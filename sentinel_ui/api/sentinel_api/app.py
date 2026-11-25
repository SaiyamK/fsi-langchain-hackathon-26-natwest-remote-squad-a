"""HTTP API + server-sent events for the analyst workspace (design.md U3).

Run from the repo root:  uv run uvicorn sentinel_api.app:app --app-dir sentinel_ui/api --port 8000

Environment (all optional):
- SENTINEL_UI_MODE      live | record | replay | offline. Default: replay if a recording exists, else live if a
                        model key is configured, else offline.
- SENTINEL_LIVE_TX      comma-separated transaction IDs that run live even in replay (DEC-003: Sophie's case)
- SENTINEL_REPLAY_SPEED how much faster than recorded a replay plays (default 3)
- SENTINEL_SPEED        transactions released per second (default 8)
"""

import asyncio
import json
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from sentinel_api import UI_ROOT
from sentinel_api.detail import account_detail, case_detail
from sentinel_api.models import AccountDetail, CaseDetail, DecisionIn, FastForwardIn, Snapshot, SpeedIn
from sentinel_api.results import load_results
from sentinel_api.session import Config, Session
from sentinel_api.world import World


#
# Events: worker threads publish, every SSE client gets its own queue
#
class EventBus:
    def __init__(self):
        self.loop: asyncio.AbstractEventLoop | None = None
        self.queues: set[asyncio.Queue] = set()

    def publish(self, kind: str, data: dict):
        if self.loop is not None:
            self.loop.call_soon_threadsafe(self._fanout, {"type": kind, "data": data})

    def _fanout(self, event: dict):
        for q in list(self.queues):
            if q.qsize() < 5000:
                q.put_nowait(event)


#
# Building a session for the configured mode
#
def _agents_available(model: str) -> bool:
    provider = model.split(":", 1)[0]
    key = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}.get(provider)
    return bool(os.environ.get(key)) if key else True


def build_session(bus: EventBus) -> Session:
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.store.memory import InMemoryStore
    from tools.precedents import load_seed_precedents
    from utils.models import model  # loads the repo-root .env
    from utils.state import MyAgentContext

    from sentinel_api import recording
    from sentinel_api.investigators import LiveInvestigator, OfflineInvestigator
    from sentinel_api.models import ReplayInfo

    ctx = MyAgentContext()
    available = _agents_available(model)
    saved = recording.load()
    mode = os.environ.get("SENTINEL_UI_MODE") or ("replay" if saved else "live" if available else "offline")
    live_tx = tuple(t.strip() for t in os.environ.get("SENTINEL_LIVE_TX", "").split(",") if t.strip())
    if mode in ("live", "record") and not available:
        mode = "offline"
    if mode == "replay" and not saved:
        mode = "live" if available else "offline"

    store = InMemoryStore()
    load_seed_precedents(store)
    offline = OfflineInvestigator(store, ctx)
    live = None
    if available and (mode in ("live", "record") or live_tx):
        from agents import build_agent

        live = LiveInvestigator(build_agent(checkpointer=InMemorySaver(), store=store), ctx)

    replay_info = None
    if mode == "live":
        investigator = live
    elif mode == "record":
        investigator = recording.RecordingInvestigator(live, model)
    elif mode == "replay":
        player = recording.ReplayInvestigator(saved, store, ctx, fallback=live or offline,
                                              speed=float(os.environ.get("SENTINEL_REPLAY_SPEED", "3")))
        investigator = _LiveOverride(player, live, set(live_tx)) if live and live_tx else player
        replay_info = ReplayInfo(recorded_at=saved["recorded_at"], model=saved.get("model"),
                                 investigations=len(saved["investigations"]))
    else:
        investigator = offline

    config = Config(mode=mode, speed=float(os.environ.get("SENTINEL_SPEED", "8")), model=model,
                    replay=replay_info, live_transactions=live_tx, agents_available=available)
    return Session(World.load(), store, investigator, config, bus.publish, ctx)


class _LiveOverride:
    """Replay everything except the listed transactions, which run live (DEC-003)."""

    def __init__(self, player, live, live_tx: set[str]):
        self.player, self.live, self.live_tx = player, live, live_tx

    def run(self, tx, *args):
        return (self.live if tx["transaction_id"] in self.live_tx else self.player).run(tx, *args)


#
# App
#
class Holder:
    def __init__(self):
        self.bus = EventBus()
        self.session: Session | None = None
        self.lock = threading.Lock()

    def reset(self) -> Session:
        with self.lock:
            if self.session is not None:
                self.session.close()
            self.session = build_session(self.bus)
            return self.session


holder = Holder()


@asynccontextmanager
async def lifespan(_: FastAPI):
    holder.bus.loop = asyncio.get_running_loop()
    await asyncio.to_thread(holder.reset)
    yield
    if holder.session:
        holder.session.close()


app = FastAPI(title="Sentinel analyst workspace API", lifespan=lifespan)


def session() -> Session:
    if holder.session is None:
        raise HTTPException(503, "Session is starting")
    return holder.session


@app.get("/api/state", response_model=Snapshot)
def get_state():
    return session().snapshot()


@app.get("/api/events")
async def events():
    queue: asyncio.Queue = asyncio.Queue()
    holder.bus.queues.add(queue)

    async def stream():
        try:
            # Send something at once: headers and onopen otherwise wait for the first real event
            yield {"event": "ready", "data": "{}"}
            while True:
                event = await queue.get()
                yield {"event": event["type"], "data": json.dumps(event["data"], default=str)}
        finally:
            holder.bus.queues.discard(queue)

    return EventSourceResponse(stream(), ping=15)


@app.post("/api/stream/start")
def start():
    session().start()
    return session().info()


@app.post("/api/stream/pause")
def pause():
    session().pause()
    return session().info()


@app.post("/api/stream/resume")
def resume():
    session().start()
    return session().info()


@app.post("/api/stream/reset")
async def reset():
    s = await asyncio.to_thread(holder.reset)
    holder.bus.publish("reset", s.info().model_dump(mode="json"))
    return s.info()


@app.post("/api/stream/fast-forward")
def fast_forward(body: FastForwardIn):
    session().fast_forward(body.days)
    return session().info()


@app.post("/api/stream/speed")
def speed(body: SpeedIn):
    session().set_speed(body.tx_per_second)
    return session().info()


@app.get("/api/cases/{case_id}", response_model=CaseDetail)
def get_case(case_id: str):
    detail = case_detail(session(), case_id)
    if detail is None:
        raise HTTPException(404, f"No case {case_id}")
    return detail


@app.get("/api/accounts/{account_id}", response_model=AccountDetail)
def get_account(account_id: str, days: int = 30):
    return account_detail(session(), account_id, days)


@app.post("/api/transactions/{transaction_id}/decision")
def decide(transaction_id: str, body: DecisionIn):
    if not body.note.strip():
        raise HTTPException(422, "A note is required")
    if not session().decide(transaction_id, body.decision, body.note):
        raise HTTPException(404, f"No transaction {transaction_id} in the stream")
    return {"ok": True}


@app.get("/api/sars/{sar_id}")
def get_sar(sar_id: str):
    s = session()
    tx_id = sar_id.removeprefix("SAR-")
    row = s.rows.get(tx_id)
    item = s.store.get(("sars", row.user_id), sar_id) if row else None
    if item is None:
        raise HTTPException(404, f"No SAR draft {sar_id}")
    return item.value


@app.get("/api/results")
def results():
    return load_results()


@app.get("/api/trace/{run_id}")
def trace(run_id: str):
    """Redirect to a run in LangSmith. The URL needs the workspace, so it's looked up rather than guessed."""
    try:
        from langsmith import Client

        client = Client()
        return RedirectResponse(client.get_run_url(run=client.read_run(run_id)))
    except Exception as exc:  # noqa: BLE001 - LangSmith unreachable or run not found
        raise HTTPException(404, f"Trace not available: {type(exc).__name__}") from exc


# Serve the built web app (sentinel_ui/web/dist) when it exists, so one process runs the demo
DIST = UI_ROOT / "web" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        file = DIST / path
        return FileResponse(file if path and file.is_file() and Path(file).resolve().is_relative_to(DIST) else DIST / "index.html")
