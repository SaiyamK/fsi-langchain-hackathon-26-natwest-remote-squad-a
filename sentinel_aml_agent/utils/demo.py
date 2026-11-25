"""Helpers for the demo notebook (`modules/01_sentinel_demo.ipynb`). Display only: every verdict comes from the
same rules, agents, safeguards and memory as everywhere else (DEC-004).

Interrupts on transactions that aren't on stage are answered from `data/reviewer_answers.jsonl` and labelled
"scripted analyst" (design.md D3). The analyst panel (ipywidgets) is used for the live review.
"""

import json
import os
from collections import Counter

from IPython.display import Markdown, display
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from agents import build_agent
from tools.precedents import load_seed_precedents
from utils import PROJECT_ROOT, db, replay
from utils.graph import fan_in_summary
from utils.schemas import DISCLAIMER
from utils.state import MyAgentContext
from utils.stream import Investigation, global_stream, process_stream, rule_score_for

SUMMARY = PROJECT_ROOT / "results" / "eval_summary.json"
ANNOTATIONS = PROJECT_ROOT / "results" / "annotation_summary.json"


def md(text: str):
    display(Markdown(text))


class Demo:
    """One demo session: one agent, one memory store, shared by every cell."""

    def __init__(self):
        self.store = InMemoryStore()
        self.seeded = load_seed_precedents(self.store)
        self.agent = build_agent(checkpointer=InMemorySaver(), store=self.store)
        self.ctx = MyAgentContext()
        self.answers = {a["transaction_id"]: a for a in db.table("reviewer_answers")}
        self.totals = Counter()
        self.investigations: dict[str, dict] = {}
        self.records: dict[str, dict] = {}
        self.run_ids: list[str] = []
        self._trace_base = self._langsmith_base()

    # ---------- links ----------
    @staticmethod
    def _langsmith_base() -> str | None:
        try:
            from langsmith import Client

            project = Client().read_project(project_name=os.environ["LANGSMITH_PROJECT"])
            return str(project.url)
        except Exception:
            return None

    def trace_link(self, run_id: str | None) -> str:
        if not run_id:
            return ""
        return f"[trace]({self._trace_base}/r/{run_id})" if self._trace_base else f"trace `{run_id}`"

    # ---------- interrupts ----------
    def scripted_answer(self, question: dict) -> dict:
        row = self.answers.get(question["transaction_id"])
        if row:
            answer = {"decision": row["decision"], "note": row["note"], "analyst": "scripted"}
            md(f"🧑‍⚖️ **Asked a human** about `{question['transaction_id']}` because: "
               f"{'; '.join(question['why_review'])}. *Scripted analyst* (reviewer_answers.jsonl): "
               f"**{row['decision']}**, \"{row['note']}\"")
        else:
            answer = {"decision": question["agent_decision"], "note": ""}
            md(f"🧑‍⚖️ **Review requested** for `{question['transaction_id']}` ({'; '.join(question['why_review'])}). "
               f"This background case has no analyst in the demo, so the agents' decision "
               f"(**{question['agent_decision']}**) stands, as in the starter. In production it would wait in the queue.")
        return answer

    # ---------- running ----------
    def _remember(self, run: dict):
        for d in run["decisions"]:
            self.records[d["transaction_id"]] = d
            self.totals["transactions"] += 1
            self.totals["rules"] += d["decided_by"] == "rules"
            self.totals[d["final_decision"]] += 1
        for i in run["investigations"]:
            self.investigations[i["transaction_id"]] = i
            self.run_ids.append(i["trace_run_id"])
        self.totals["model_calls"] += run["counters"]["model_calls"]
        replay.note_recorded_runs(self.run_ids)

    def stream(self, start: str, end: str, title: str):
        """Run every transaction in [start, end) through the tiers, with a live counter."""
        txs = global_stream(start, end)
        handle = display(Markdown(f"**{title}**: starting…"), display_id=True)
        live = Counter()

        def on_event(e):
            live["n"] += 1
            live["rules"] += e["tier"] == "rules"
            live["agents"] += e["tier"] == "agents"
            if handle is not None:  # None outside Jupyter
                handle.update(Markdown(f"**{title}**: {live['n']}/{len(txs)} transactions · "
                                   f"{live['rules']} cleared by rules (no LLM) · {live['agents']} investigated by agents"))

        run = process_stream(self.agent, self.ctx, txs, on_interrupt=self.scripted_answer, on_event=on_event,
                             parallel_customers=True, extra_tags=["demo"])
        self._remember(run)
        c = run["counters"]
        md(f"**{len(txs)} transactions**: {run['rules_cleared']} cleared by rules "
           f"({run['rules_cleared'] / max(len(txs), 1):.1%}) with no LLM call; {c['investigations']} investigated "
           f"({c['model_calls']} model calls).")
        for i in run["investigations"]:
            self.show(i["transaction_id"], brief=True)
        return run

    def case(self, transaction_ids: list[str]):
        """Run specific transactions (and show each investigation)."""
        txs = [db.get("transactions", transaction_id=t) for t in transaction_ids]
        run = process_stream(self.agent, self.ctx, txs, on_interrupt=self.scripted_answer, parallel_customers=True,
                             extra_tags=["demo"])
        self._remember(run)
        for t in transaction_ids:
            self.show(t)
        return run

    # ---------- live human review ----------
    def start_review(self, transaction_id: str) -> Investigation:
        tx = db.get("transactions", transaction_id=transaction_id)
        score, reasons = rule_score_for(tx, self.ctx)
        inv = Investigation(self.agent, self.ctx, tx, score, reasons, extra_tags=["demo", "live-review"])
        q = inv.start()
        inv.done = q is None
        if inv.done:
            self._finish(inv)
        return inv

    def panel(self, inv: Investigation):
        """The analyst panel: evidence, why the agents are unsure, a note box and Clear / Escalate buttons."""
        if inv.done:
            md("The agents decided without needing a human.")
            return
        import ipywidgets as w

        q = inv.question
        md(f"### 🧑‍⚖️ Analyst review needed: `{q['transaction_id']}`\n"
           f"- **Agents' view:** {q['agent_decision']} · risk {q['risk_score']} · confidence {q['model_confidence']}"
           f" (after checks {q['confidence']})\n"
           f"- **Why you're being asked:** {'; '.join(q['why_review'])}\n"
           f"- **Evidence:** {q['reason']}\n"
           f"- **Rules flagged:** {'; '.join(q['rule_reasons'])}\n"
           f"- **Precedents:** valid {q['precedents']['valid'] or 'none'} · expired {q['precedents']['expired'] or 'none'}")
        note = w.Text(placeholder="Your note (saved as a precedent)", layout=w.Layout(width="70%"))
        out = w.Output()
        buttons = [w.Button(description="Clear", button_style="success"),
                   w.Button(description="Escalate", button_style="danger")]

        def click(b):
            if inv.done:
                return
            with out:
                self.answer(inv, {"decision": b.description.lower(), "note": note.value, "analyst": "presenter"})

        for b in buttons:
            b.on_click(click)
        display(w.VBox([note, w.HBox(buttons), out]))

    def answer(self, inv: Investigation, answer: dict):
        if inv.done:
            return
        q = inv.resume(answer)
        while q is not None:
            q = inv.resume(self.scripted_answer(q))
        inv.done = True
        self._finish(inv)

    def ensure_answered(self, inv: Investigation, transaction_id: str):
        """For a non-interactive run of the notebook: if nobody clicked, use the scripted answer (labelled)."""
        if not inv.done:
            md("*No click recorded in this run of the notebook, so the scripted analyst answers.*")
            self.answer(inv, self.scripted_answer(inv.question))

    def _finish(self, inv: Investigation):
        record, summary = inv.finish()
        self._remember({"decisions": [record], "investigations": [summary], "counters": {"model_calls": summary["model_calls"]}})
        self.show(record["transaction_id"])

    # ---------- showing ----------
    def show(self, transaction_id: str, brief: bool = False):
        d = self.records[transaction_id]
        i = self.investigations.get(transaction_id, {})
        tx = db.get("transactions", transaction_id=transaction_id)
        who = db.get("customer_profiles", user_id=tx["user_id"])["name"]
        icon = "🚨" if d["final_decision"] == "escalate" else "✅"
        head = (f"{icon} **{transaction_id}** {who} · £{tx['amount']:,.0f} {tx['txn_type'].replace('_', ' ')} · "
                f"**{d['final_decision'].upper()}** by {d['decided_by']}")
        if brief:
            md(f"{head} · {d.get('reason', '')[:220]}")
            return
        lines = [head, f"- Rules: score {d.get('rule_score')} · {'; '.join(d.get('rule_reasons') or [])}"]
        if i:
            subs = [c["subagent"] for c in i["tool_calls"] if c["subagent"]]
            lines.append(f"- Supervisor delegated to: {', '.join(dict.fromkeys(subs)) or 'none'} · "
                         f"{i['model_calls']} model calls · {i['seconds']}s · {self.trace_link(i['trace_run_id'])}")
        lines.append(f"- Verdict: {d.get('pattern')} · risk {d.get('risk_score')} · confidence {d.get('confidence')}")
        if d.get("hard_flags"):
            lines.append(f"- **Hard flags:** {'; '.join(d['hard_flags'])}")
        for p in d.get("precedents_relied_on") or []:
            prec = self.store.get(("precedents", tx["user_id"]), p)
            v = prec.value if prec else {}
            lines.append(f"- **Precedent relied on:** {v.get('created_at')} \"{v.get('note')}\", valid until "
                         f"{v.get('expires_at')}. Hard red flags: none.")
        for p in d.get("precedents_overridden") or []:
            lines.append(f"- **Precedent found → OVERRIDDEN:** \"{p['note']}\" ({p['key']}). Reason: {p['reason']}")
        for p in d.get("precedents_dropped") or []:
            lines.append(f"- Precedent not applied: {p['key']} ({p['reason']})")
        if d.get("analyst_note"):
            lines.append(f"- Analyst note → saved as a precedent: \"{d['analyst_note']}\"")
        lines.append(f"- Reason: {d.get('reason')}")
        md("\n".join(lines))

    def network_graph(self, account_id: str, as_of: str):
        """Draw the fan-in network around an account, as the fund-flow tool sees it at `as_of`."""
        import matplotlib.pyplot as plt
        import networkx as nx

        s = fan_in_summary(account_id, as_of)
        collector = s["collector_account"]
        g = nx.DiGraph()
        names = {p["account_id"]: p["name"].split()[0] for p in db.table("customer_profiles")}
        for f in s["forwards"]:
            g.add_edge(f["from"], collector, amount=f["amount"])
        for t in db.table("transactions"):
            if t["timestamp"] <= as_of and t["account_id"] in set(s["feeder_accounts"]) and t["direction"] == "in" \
                    and t["txn_type"] == "faster_payment" and t["timestamp"] >= min(f["timestamp"] for f in s["forwards"])[:10]:
                g.add_edge(t["counterparty_id"], t["account_id"], amount=t["amount"])
            if t["timestamp"] <= as_of and t["account_id"] == collector and t["direction"] == "out":
                g.add_edge(collector, t["counterparty_id"], amount=t["amount"])
        layers = {}
        for n in g.nodes:
            layers[n] = 2 if n == collector else 1 if n in s["feeder_accounts"] else 3 if g.in_degree(n) else 0
        nx.set_node_attributes(g, layers, "layer")
        pos = nx.multipartite_layout(g, subset_key="layer")
        colours = ["#d62728" if n == collector else "#ff7f0e" if n in s["feeder_accounts"] else "#bbbbbb" for n in g]
        plt.figure(figsize=(11, 5))
        nx.draw_networkx(g, pos, node_color=colours, node_size=[1400 if n == collector else 700 if n in
                         s["feeder_accounts"] else 160 for n in g], labels={n: names.get(n, "") for n in g},
                         font_size=8, arrowsize=10, edge_color="#999999")
        plt.title(f"Fan-in network seen by the fund-flow tool at {as_of} · ring confirmed: {s['ring_confirmed']} · "
                  f"pass-through {s['pass_through_ratio']:.0%}")
        plt.axis("off")
        plt.show()

    def sar(self, transaction_id: str):
        tx = db.get("transactions", transaction_id=transaction_id)
        item = self.store.get(("sars", tx["user_id"]), f"SAR-{transaction_id}")
        if not item:
            md("No SAR draft for this transaction.")
            return
        s = item.value
        md(f"### SAR draft · {s['subject']} · {s['pattern']}\n> **{DISCLAIMER}**\n\n"
           f"**Timeline**\n" + "\n".join(f"- {x}" for x in s["timeline"]) +
           "\n\n**Evidence**\n" + "\n".join(f"- {x}" for x in s["evidence"]) +
           f"\n\n**Narrative.** {s['narrative']}\n\n**Precedents.** " + "; ".join(s["precedents_cited_or_overridden"]) +
           f"\n\n*{s['disclaimer']}*")


#
# Eval results (loaded, never run live: DEC-003, R9.4)
#
CATEGORIES = [
    ("1. Detection quality", "benchmark", ["false_positives", "false_positive_rate", "alert_precision", "recall_planted"]),
    ("2. Risk calibration", "benchmark", ["score_alignment_eval"]),
    ("3. Human-in-the-loop routing", "benchmark", ["review_routing_eval", "human_review_rate", "reviews_month1", "reviews_month2"]),
    ("4. Memory safeguards", "scenarios", ["precedent_used_when_valid", "no_reliance_on_invalid_precedent",
                                           "hard_flag_overrides_precedent"]),
    ("5. Agent behaviour", "scenarios", ["kyc_called_every_time", "record_decision_once", "specialists_match_rule_reasons"]),
    ("6. SAR quality", "scenarios", ["sar_grounded", "sar_written_for_escalations"]),
    ("7. Efficiency", "benchmark", ["llm_share", "model_calls_per_investigation", "tokens_per_investigation",
                                   "p50_seconds_per_investigation"]),
    ("8. Privacy and scope", "scenarios", ["network_calls_audited", "network_returns_account_ids_only"]),
]


COUNTS = {"false_positives", "reviews_month1", "reviews_month2", "tokens_per_investigation",
          "model_calls_per_investigation", "p50_seconds_per_investigation", "investigations"}


def _fmt(v, key: str = ""):
    if v is None:
        return "–"
    if key in COUNTS:
        return f"{v:,.0f}" if float(v).is_integer() else f"{v:,.1f}"
    return f"{v:.1%}"


def eval_tables():
    s = json.loads(SUMMARY.read_text())
    runs = s["runs"]
    bench_r, bench_s = runs["benchmark:test:rules-only"]["scores"], runs["benchmark:test:sentinel"]["scores"]
    sc_r, sc_s = runs["scenarios:all:rules-only"]["scores"], runs["scenarios:all:sentinel"]["scores"]
    md(f"**Loaded from `results/eval_summary.json`** (updated {s['updated_at']}, model `{s['model']}`). {s['note']}")
    fp_r, fp_s = bench_r["false_positives"], bench_s["false_positives"]
    md("### Headline: held-out test world (950 transactions, 15 planted alerts)\n"
       "| | Rules only | Sentinel |\n|---|---|---|\n"
       f"| False positives | {fp_r:.0f} | **{fp_s:.0f}** ({(fp_s - fp_r) / fp_r:+.0%}) |\n"
       f"| Alert precision | {bench_r['alert_precision']:.0%} | **{bench_s['alert_precision']:.0%}** |\n"
       f"| Recall on planted alerts | {bench_r['recall_planted']:.0%} | **{bench_s['recall_planted']:.0%}** |\n"
       f"| Decision accuracy · score alignment · review routing (starter evaluators) | "
       f"{bench_r['decision_accuracy_eval']:.3f} · {bench_r['score_alignment_eval']:.3f} · {bench_r['review_routing_eval']:.3f} | "
       f"{bench_s['decision_accuracy_eval']:.3f} · {bench_s['score_alignment_eval']:.3f} · {bench_s['review_routing_eval']:.3f} |\n"
       f"| Human reviews, month 1 → month 2 (repeat cases planted in the data) | – | "
       f"{bench_s['reviews_month1']:.0f} → {bench_s['reviews_month2']:.0f} |\n"
       f"| Transactions reaching an LLM | 0% | {bench_s['llm_share']:.1%} |\n"
       f"| Per investigation: model calls · tokens · median seconds | – | {bench_s['model_calls_per_investigation']:.1f} · "
       f"{bench_s['tokens_per_investigation']:,.0f} · {bench_s['p50_seconds_per_investigation']:.0f}s |")
    rows = ["| Category | Dataset | Evaluators | Rules only | Sentinel |", "|---|---|---|---|---|"]
    for name, ds, keys in CATEGORIES:
        r, sn = (bench_r, bench_s) if ds == "benchmark" else (sc_r, sc_s)
        rows.append(f"| {name} | {ds} | {', '.join(f'`{k}`' for k in keys)} | "
                    f"{' · '.join(_fmt(r.get(k), k) for k in keys)} | {' · '.join(_fmt(sn.get(k), k) for k in keys)} |")
    rows.append("| 6b. SAR completeness (LLM judge) | online | `sar_complete` | – | see monitoring below |")
    md("### Coverage: 8 evaluation categories\n" + "\n".join(rows) +
       "\n\n**Not covered yet:** real or public AML data, adversarial inputs (e.g. prompt injection through payment "
       "references), fairness across customer groups, production load, analyst usability.")
    md("**LangSmith experiments:** " + " · ".join(f"`{v['experiment']}`" for v in runs.values()))


def monitoring():
    """Online evaluator scores on SAR drafts and the annotation queue summary (PLAN.md 7.1)."""
    try:
        from langsmith import Client

        client = Client()
        runs = list(client.list_runs(project_name=os.environ["LANGSMITH_PROJECT"], filter='eq(name, "sar-writer")', limit=50))
        scores = [f.score for f in client.list_feedback(run_ids=[r.id for r in runs], feedback_key=["sar_complete"])
                  if f.score is not None] if runs else []
    except Exception as e:  # monitoring is best-effort in the notebook
        runs, scores = [], []
        md(f"(Couldn't read LangSmith: {e})")
    if scores:
        md(f"**Online evaluator `sar_complete`:** {len(scores)} SAR drafts scored automatically in the tracing "
           f"project · mean {sum(scores) / len(scores):.2f} · lowest {min(scores):.2f}.")
    else:
        md(f"**Online evaluator `sar_complete`:** not scoring yet ({len(runs)} `sar-writer` runs in the project). "
           "Set it up with `evals/online_evaluators.md`.")
    if ANNOTATIONS.exists():
        a = json.loads(ANNOTATIONS.read_text())
        tag = " **(SIMULATED reviews)**" if a.get("simulated") else ""
        md(f"**Annotation queue `{a['queue']}`:** {a['reviewed']}/{a['queued']} reviewed{tag} · agent-analyst "
           f"agreement {_fmt(a['agreement_rate'])} · evidence sufficient {_fmt(a['evidence_sufficient_rate'])} · "
           f"{len(a['disagreements'])} disagreements (become new test cases).")
    else:
        md("**Annotation queue:** created; no reviews collected yet (`scripts/annotation_queue.py --collect`).")
