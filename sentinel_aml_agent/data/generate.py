"""Seeded, labelled synthetic AML data for Sentinel (tasks 1.3 and 1.4). All people and firms are fictional.

    uv run python data/generate.py              # world 0 (demo), 1 (dev) and 2 (test)
    uv run python data/generate.py --world 0    # one world only

World 0 is the demo cast from DEMO_SCRIPT.md (design.md D4) plus background customers; it's written to `data/`.
Worlds 1 and 2 are the eval benchmark (DEC-006): background customers plus the same scenario types with random
names, amounts and dates; they're written to `data/worlds/world_<N>/`. The same scenario functions build both, so
nothing downstream can tell a demo customer from an eval one (DEC-004).

Same seed and world → byte-identical files.

How labels work. Each transaction gets an analyst label saying whether an ALERT should fire on that transaction:
- `decision`: "escalate" if an alert should fire here, else "clear".
- `pattern`: the typology the transaction is part of. Earlier steps of a pattern (Daniel's first three deposits, the
  money arriving in a mule account) keep the pattern name but are labelled "clear", because the alert is expected on
  the transaction that completes the pattern. Recall counts labels with decision "escalate" and pattern != "none".
- `ambiguous`: an analyst would want to be asked (mixed evidence). Mule forwards before the ring can be confirmed
  are `ambiguous: true, decision: escalate` (agreed in PLAN.md section 1).
- `expect_override`, `expect_precedent_use`, `expect_human`: scenario expectations for the safeguard evals (DEC-010).
- `month`: 1 for October 2026, 2 for November 2026, and so on.
"""

import argparse
import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
STREAM_START = date(2026, 10, 1)
STREAM_END = date(2026, 11, 30)

FIRST_NAMES = [
    "Olivia", "Noah", "Ava", "Leo", "Isla", "Oscar", "Freya", "Arthur", "Mia", "Harry", "Ella", "Jack", "Lily",
    "George", "Ruby", "Theo", "Evie", "Henry", "Poppy", "Alfie", "Zara", "Ethan", "Hannah", "Samuel", "Maya",
    "Adam", "Nadia", "Kai", "Erin", "Rohan", "Leah", "Owen", "Imogen", "Felix", "Anya", "Callum", "Esme", "Ravi",
]
LAST_NAMES = [
    "Morgan", "Bennett", "Carter", "Doyle", "Ellis", "Foster", "Grant", "Hayes", "Iqbal", "Jennings", "Kaur", "Lowe",
    "Mason", "Nolan", "Osei", "Parry", "Quinn", "Rahman", "Shaw", "Turner", "Usman", "Vaughan", "Ward", "Young",
    "Akhtar", "Brooks", "Chen", "Dixon", "Evans-Lee", "Fraser", "Gill", "Holt", "Ibrahim", "Jarvis", "Kemp", "Lynch",
]
BRANCHES = ["Leeds Briggate", "Manchester Market St", "Birmingham New St", "Bristol Broadmead", "Sheffield Fargate",
            "Wakefield Westgate", "Bradford Broadway", "York Parliament St", "Nottingham Clumber St"]
MERCHANTS = [("FreshMart", 8, 90), ("City Transit", 2, 15), ("Corner Cafe", 3, 12), ("StreamBox", 6, 15),
             ("Petrol Plus", 30, 80), ("BookNook", 5, 30), ("PharmaCare", 4, 25), ("HomeHub", 15, 140)]


class World:
    """Collects the rows for one world and hands out IDs."""

    def __init__(self, number: int, seed: int):
        self.number = number
        self.rng = random.Random(seed * 1000 + number)
        self.profiles: list[dict] = []
        self.txs: list[dict] = []          # each has a "_label" until written out
        self.answers: list[dict] = []      # scripted analyst answers, keyed by transaction later
        self.precedents: list[dict] = []
        self.pep_entries: list[dict] = []
        self._ext = 1000

    # ---------- people ----------
    def customer(self, num: int, name: str, *, customer_type="individual", occupation="employee", risk="low",
                 pep=False, monthly_credits=2500, monthly_cash=0, opened="2020-01-15", dob="1990-01-01") -> dict:
        profile = {
            "user_id": f"CUS-{num:04d}", "name": name, "account_id": f"ACC-{num:04d}",
            "customer_type": customer_type, "occupation": occupation, "risk_rating": risk, "pep": pep,
            "home_country": "GB", "currency": "GBP", "date_of_birth": dob,
            "expected_monthly_credits": monthly_credits, "expected_monthly_cash": monthly_cash,
            "account_opened": opened,
        }
        self.profiles.append(profile)
        return profile

    def ext(self, prefix: str = "EXT") -> str:
        self._ext += 1
        return f"{prefix}-{self.number}{self._ext:04d}"

    def random_name(self, taken: set[str]) -> str:
        while True:
            name = f"{self.rng.choice(FIRST_NAMES)} {self.rng.choice(LAST_NAMES)}"
            if name not in taken:
                taken.add(name)
                return name

    # ---------- transactions ----------
    def tx(self, who: dict, when: datetime, direction: str, txn_type: str, amount: float, *, counterparty_id=None,
           counterparty_name=None, branch=None, country="GB", reference="", channel="online", label=None) -> dict:
        row = {
            "transaction_id": None, "user_id": who["user_id"], "account_id": who["account_id"],
            "timestamp": when.strftime("%Y-%m-%dT%H:%M"), "direction": direction, "txn_type": txn_type,
            "amount": round(float(amount), 2), "currency": "GBP", "counterparty_id": counterparty_id,
            "counterparty_name": counterparty_name, "branch": branch, "country": country, "reference": reference,
            "channel": channel,
            "_label": label or clear_label(),
        }
        self.txs.append(row)
        return row

    def transfer(self, sender: dict, receiver: dict, when: datetime, amount: float, reference: str,
                 out_label=None, in_label=None) -> tuple[dict, dict]:
        """An internal transfer between two of our customers: an out leg for the sender, an in leg for the receiver."""
        out_leg = self.tx(sender, when, "out", "internal_transfer", amount, counterparty_id=receiver["account_id"],
                          counterparty_name=receiver["name"], reference=reference, label=out_label)
        in_leg = self.tx(receiver, when + timedelta(minutes=1), "in", "internal_transfer", amount,
                         counterparty_id=sender["account_id"], counterparty_name=sender["name"], reference=reference,
                         label=in_label)
        return out_leg, in_leg

    def answer(self, row: dict, decision: str, note: str):
        self.answers.append({"_tx": row, "decision": decision, "note": note})


def clear_label(pattern="none", **flags) -> dict:
    return {"decision": "clear", "risk_score": 5 if pattern == "none" else 25, "ambiguous": False, "pattern": pattern,
            **_flags(flags)}


def alert_label(pattern: str, risk_score=85, ambiguous=False, **flags) -> dict:
    return {"decision": "escalate", "risk_score": risk_score, "ambiguous": ambiguous, "pattern": pattern,
            **_flags(flags)}


def _flags(flags: dict) -> dict:
    return {"expect_override": flags.get("expect_override", False),
            "expect_precedent_use": flags.get("expect_precedent_use", False),
            "expect_human": flags.get("expect_human", False)}


def at(day: date, hh: int, mm: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hh, mm)


def days(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


#
# Background traffic: ordinary customers, including benign activity that rules flag
#
def background_customer(w: World, num: int, name: str, kind: str, start=STREAM_START, end=STREAM_END,
                        quiet: tuple[date, date] | None = None) -> dict:
    """An ordinary customer. `quiet` is a date range with no cash deposits (keeps a scenario's window clean)."""
    rng = w.rng
    if kind == "cash_business":
        cash = rng.choice([4000, 6000, 8000, 12000])
        p = w.customer(num, name, customer_type="individual", occupation=rng.choice(["cafe owner", "market trader",
                       "barber", "takeaway owner"]), monthly_credits=cash + 1500, monthly_cash=cash,
                       opened=f"{rng.randint(2012, 2022)}-0{rng.randint(1, 9)}-1{rng.randint(0, 9)}",
                       dob=f"19{rng.randint(65, 95)}-0{rng.randint(1, 9)}-2{rng.randint(0, 8)}")
        home = rng.choice(BRANCHES)
        for d in days(start, end):
            in_quiet = quiet and quiet[0] <= d <= quiet[1]
            if d.weekday() in (1, 4) and not in_quiet:
                w.tx(p, at(d, rng.randint(9, 16), rng.randint(0, 59)), "in", "cash_deposit",
                     cash / 8.7 * rng.uniform(0.6, 1.3), branch=home, channel="branch", reference="Takings")
            if d.day == 3:
                w.tx(p, at(d, 10), "out", "faster_payment", cash * 0.35, counterparty_id=f"EXT-SUP-{num:04d}",
                     counterparty_name="Wholesale supplier", reference="Stock")
    elif kind == "student":
        p = w.customer(num, name, occupation="student", monthly_credits=900, opened=f"202{rng.randint(3, 5)}-09-0{rng.randint(1, 9)}",
                       dob=f"200{rng.randint(3, 7)}-0{rng.randint(1, 9)}-1{rng.randint(0, 9)}")
        w.tx(p, at(date(2026, 10, 6), 6), "in", "bacs", 3100, counterparty_id="EXT-SLC", counterparty_name="Student loan",
             reference="Maintenance loan")
        for d in days(start, end):
            if d.day == 28:
                w.tx(p, at(d, 7), "in", "bacs", rng.uniform(450, 700), counterparty_id=f"EXT-PT-{num:04d}",
                     counterparty_name="Part-time employer", reference="Wages")
    elif kind == "retired":
        pension = rng.choice([1400, 1800, 2400])
        p = w.customer(num, name, occupation="retired", monthly_credits=pension, opened=f"19{rng.randint(88, 99)}-05-12",
                       dob=f"195{rng.randint(0, 9)}-0{rng.randint(1, 9)}-0{rng.randint(1, 9)}")
        for d in days(start, end):
            if d.day == 1:
                w.tx(p, at(d, 6), "in", "bacs", pension, counterparty_id="EXT-PEN", counterparty_name="Pension",
                     reference="Pension")
    else:  # salaried
        salary = rng.choice([2200, 2800, 3500, 4200, 5500])
        p = w.customer(num, name, occupation=rng.choice(["nurse", "teacher", "engineer", "accountant", "analyst",
                       "electrician"]), monthly_credits=salary, opened=f"20{rng.randint(10, 23)}-0{rng.randint(1, 9)}-0{rng.randint(1, 9)}",
                       dob=f"19{rng.randint(70, 99)}-0{rng.randint(1, 9)}-1{rng.randint(0, 9)}")
        employer = f"EXT-EMP-{num:04d}"
        for d in days(start, end):
            if d.day == 25:
                w.tx(p, at(d, 6), "in", "bacs", salary, counterparty_id=employer, counterparty_name="Employer payroll",
                     reference="Salary")
            if d.day == 1:
                w.tx(p, at(d, 9), "out", "faster_payment", salary * 0.35, counterparty_id=f"EXT-LL-{num:04d}",
                     counterparty_name="Landlord", reference="Rent")
    # card spending for everyone
    for d in days(start, end):
        if rng.random() < 0.3:
            merchant, lo, hi = rng.choice(MERCHANTS)
            w.tx(p, at(d, rng.randint(8, 21), rng.randint(0, 59)), "out", "card", rng.uniform(lo, hi),
                 counterparty_name=merchant, channel="card")
    return p


def benign_large_credit(w: World, p: dict, when: datetime, multiple: float, vague: bool, counterparty_id=None) -> dict:
    """A large one-off credit that's legitimate. Clear references are easy to clear; vague ones deserve a human."""
    rng = w.rng
    clear_refs = [("Solicitor client account", "Completion funds 14 Oak Rd"), ("HMRC", "Tax refund"),
                  ("Estate of late relative", "Inheritance distribution")]
    vague_refs = [("Private individual", "Payment"), ("Consultancy client", "Invoice settlement")]
    cp_name, ref = rng.choice(vague_refs if vague else clear_refs)
    amount = p["expected_monthly_credits"] * multiple
    label = clear_label("anomalous_credit", expect_human=vague) | {"ambiguous": vague, "risk_score": 40 if vague else 25}
    row = w.tx(p, when, "in", "faster_payment", amount, counterparty_id=counterparty_id or w.ext(),
               counterparty_name=cp_name, reference=ref, label=label)
    if vague:
        w.answer(row, "clear", f"Customer provided evidence: {ref.lower()} from {cp_name.lower()}; legitimate.")
    return row


#
# Scenarios (used for the demo cast and for planted eval cases)
#
def structuring(w: World, p: dict, first: datetime, amounts: list[float], branches: list[str], gaps_hours: list[float]):
    """Cash deposits just under £10,000 at several branches within about 72 hours.

    Labels follow the textbook typology (DEC-012): three or more near-threshold deposits in a few days is
    structuring, so the 3rd deposit and every one after it should alert. The first two alone are not suspicious.
    """
    when = first
    for i, amount in enumerate(amounts):
        last = i == len(amounts) - 1
        label = alert_label("structuring", 90) if i >= 2 else clear_label("structuring")
        w.tx(p, when, "in", "cash_deposit", amount, branch=branches[i % len(branches)], channel="branch",
             reference="Cash deposit", label=label)
        if not last:
            when += timedelta(hours=gaps_hours[i])


def anomalous_then_repeat(w: World, p: dict, counterparty_id: str, counterparty_name: str, reference: str,
                          first: datetime, first_amount: float, repeat: datetime | None, repeat_amount: float,
                          note: str):
    """A big credit from a new counterparty that an analyst clears with a note; later, the same again."""
    first_row = w.tx(p, first, "in", "faster_payment", first_amount, counterparty_id=counterparty_id,
                     counterparty_name=counterparty_name, reference=reference,
                     label=clear_label("anomalous_credit", expect_human=True) | {"ambiguous": True, "risk_score": 45})
    w.answer(first_row, "clear", note)
    if repeat:
        w.tx(p, repeat, "in", "faster_payment", repeat_amount, counterparty_id=counterparty_id,
             counterparty_name=counterparty_name, reference=reference,
             label=clear_label("anomalous_credit", expect_precedent_use=True) | {"risk_score": 20})


def round_trip(w: World, p: dict, out_when: datetime, out_amount: float, back_when: datetime, back_amount: float):
    """Money out to one company, nearly all of it back from a different one."""
    out_row = w.tx(p, out_when, "out", "faster_payment", out_amount, counterparty_id=w.ext(),
                   counterparty_name="Ardent Holdings Ltd", reference="Investment",
                   label=clear_label("round_tripping", expect_human=True) | {"ambiguous": True, "risk_score": 50})
    w.answer(out_row, "clear", "Outbound investment noted; monitoring for return flows.")
    w.tx(p, back_when, "in", "faster_payment", back_amount, counterparty_id=w.ext(),
         counterparty_name="Bellmere Capital LLP", reference="Return of funds",
         label=alert_label("round_tripping", 88))


def mule_ring(w: World, mules: list[dict], collector: dict, start: datetime, flatmate_id: str,
              offshore_id: str):
    """Several low-risk accounts receive small transfers and pass almost all of it to one new business account.

    The ring is "confirmable" under the same definition as `utils/graph.py`: 5 distinct accounts each forwarding
    at least 90% of what they received in the previous 24 hours to one collector, within 72 hours.

    Round 1: each mule receives 3 small payments and forwards ~95% to the collector, 12 hours apart. The ring is
    confirmable once the 5th mule has forwarded. Round 2: the first mule receives money from its "flatmate"
    counterparty (the one an old precedent cleared) and forwards it again; that's where the precedent must be
    overridden. The collector sends everything offshore.
    """
    rng = w.rng
    confirm_at = 5
    forwarded = 0
    for i, mule in enumerate(mules):
        base = start + timedelta(hours=12 * i)
        total = 0.0
        for k in range(3):
            amount = rng.uniform(250, 900)
            total += amount
            cp = flatmate_id if (i == 0 and k == 0) else w.ext("EXT-VIC")
            w.tx(mule, base + timedelta(minutes=20 + 50 * k), "in", "faster_payment", amount, counterparty_id=cp,
                 counterparty_name="Flatmate" if cp == flatmate_id else "Private individual",
                 reference=rng.choice(["Rent", "Thanks", "Money owed", "Payment"]), label=clear_label("mule_fan_in"))
        forwarded += 1
        confirmed = forwarded >= confirm_at
        out_label = alert_label("mule_fan_in", 85 if confirmed else 60, ambiguous=not confirmed,
                                expect_human=not confirmed)
        # The collector's inbound leg only carries a signal once the ring is confirmed (DEC-012); before that the
        # alert belongs on the mule's forward.
        in_label = alert_label("mule_fan_in", 85) if confirmed else clear_label("mule_fan_in")
        out_leg, _ = w.transfer(mule, collector, base + timedelta(hours=5), total * 0.95, "Invoice",
                                out_label, in_label)
        if not confirmed:
            w.answer(out_leg, "escalate", "Rapid pass-through to a new business account; possible mule activity.")
    round1_end = start + timedelta(hours=12 * (len(mules) - 1) + 6)
    w.tx(collector, round1_end, "out", "faster_payment", 0.0, counterparty_id=offshore_id,
         counterparty_name="Kestrel Exports FZE", country="AE", reference="Goods",
         label=alert_label("mule_fan_in", 90))
    # Round 2: the first mule again, starting with the flatmate counterparty
    first = mules[0]
    r2 = round1_end + timedelta(hours=13)
    amount = rng.uniform(700, 950)
    w.tx(first, r2, "in", "faster_payment", amount, counterparty_id=flatmate_id, counterparty_name="Flatmate",
         reference="Rent", label=alert_label("mule_fan_in", 85, expect_override=True))
    w.transfer(first, collector, r2 + timedelta(hours=3), amount * 0.96, "Invoice",
               alert_label("mule_fan_in", 85), alert_label("mule_fan_in", 85))
    w.tx(collector, r2 + timedelta(hours=8), "out", "faster_payment", 0.0, counterparty_id=offshore_id,
         counterparty_name="Kestrel Exports FZE", country="AE", reference="Goods", label=alert_label("mule_fan_in", 90))


def fix_collector_outflows(w: World, collector: dict):
    """Set each offshore payment to ~98% of what the collector received since its previous offshore payment."""
    rows = sorted((t for t in w.txs if t["user_id"] == collector["user_id"]), key=lambda t: t["timestamp"])
    pot = 0.0
    for t in rows:
        if t["direction"] == "in":
            pot += t["amount"]
        elif t["counterparty_name"] == "Kestrel Exports FZE":
            t["amount"] = round(pot * 0.98, 2)
            pot = 0.0


#
# Worlds
#
def build_world_0(w: World):
    """The demo cast (DEMO_SCRIPT.md, design.md D4), plus the safeguard customers (DEC-010) and background."""
    taken = {"Daniel Hughes", "Sophie Clarke", "Marcus Reid", "Liam Walsh", "Chloe Evans", "Ben Taylor",
             "Amira Khan", "Josh Patel", "Grace Holloway", "Tom Ashworth", "Emma Price"}

    # Daniel Hughes: structuring
    daniel = background_customer(w, 1, "Daniel Hughes", "cash_business", quiet=(date(2026, 10, 2), date(2026, 10, 10)))
    daniel.update(occupation="market trader", expected_monthly_cash=12000, expected_monthly_credits=13500,
                  date_of_birth="1981-06-14", account_opened="2017-03-02")
    structuring(w, daniel, at(date(2026, 10, 6), 9, 40), [9500, 9500, 9500, 9500],
                ["Leeds Briggate", "Wakefield Westgate", "Bradford Broadway", "Leeds Briggate"], [6.5, 19, 21.8])

    # Sophie Clarke: anomalous credit → analyst → precedent → repeat ten months later
    sophie = background_customer(w, 2, "Sophie Clarke", "salaried")
    sophie.update(occupation="product manager", expected_monthly_credits=3500, date_of_birth="1992-02-08")
    anomalous_then_repeat(w, sophie, "EXT-0102", "Halden Group Rewards", "Annual bonus",
                          at(date(2026, 10, 14), 10, 5), 18000, at(date(2027, 8, 14), 10, 0), 19200,
                          "Annual bonus — employer verified via payslip")
    w.tx(sophie, at(date(2027, 8, 25), 6), "in", "bacs", 3500, counterparty_id="EXT-EMP-0002",
         counterparty_name="Employer payroll", reference="Salary")

    # Marcus Reid: PEP-linked, round-tripping
    marcus = background_customer(w, 3, "Marcus Reid", "salaried")
    marcus.update(occupation="company director", risk_rating="high", pep=True, expected_monthly_credits=15000,
                  date_of_birth="1974-11-30")
    w.pep_entries.append({"name": "Marcus Reid", "position": "Close associate of the Minister of Trade",
                          "country": "Valdoria"})
    round_trip(w, marcus, at(date(2026, 11, 3), 11), 250000, at(date(2026, 11, 20), 15, 30), 240000)

    # Safeguard customers (DEC-010): expired precedent, out-of-scope precedent, plain control
    grace = background_customer(w, 4, "Grace Holloway", "salaried")
    grace.update(expected_monthly_credits=4000)
    w.precedents.append({"user_id": "CUS-0004", "counterparty_id": "EXT-0401", "pattern": "anomalous_credit",
                         "decision": "clear", "note": "Rental income from a let property", "analyst": "seed",
                         "created_at": "2025-06-01", "expires_at": "2026-06-01"})
    row = w.tx(grace, at(date(2026, 11, 5), 12), "in", "faster_payment", 15000, counterparty_id="EXT-0401",
               counterparty_name="Lettings agent", reference="Rent arrears settlement",
               label=clear_label("anomalous_credit", expect_human=True) | {"ambiguous": True, "risk_score": 45})
    w.answer(row, "clear", "Lettings agent confirmed arrears settlement for the let property.")

    tom = background_customer(w, 5, "Tom Ashworth", "salaried")
    tom.update(expected_monthly_credits=4200)
    w.precedents.append({"user_id": "CUS-0005", "counterparty_id": "EXT-0501", "pattern": "anomalous_credit",
                         "decision": "clear", "note": "Annual dividend from family company", "analyst": "seed",
                         "created_at": "2026-04-10", "expires_at": "2027-04-10"})
    row = w.tx(tom, at(date(2026, 11, 18), 9, 30), "in", "faster_payment", 20000, counterparty_id="EXT-0502",
               counterparty_name="Private individual", reference="Payment",
               label=clear_label("anomalous_credit", expect_human=True) | {"ambiguous": True, "risk_score": 45})
    w.answer(row, "clear", "Customer showed a sale agreement for a car; legitimate.")

    background_customer(w, 6, "Emma Price", "salaried")

    # Mule ring into Northgate Trading Ltd; Liam has an old clearance from his flatmate
    mules = []
    for num, name in [(40, "Liam Walsh"), (41, "Chloe Evans"), (42, "Ben Taylor"), (43, "Amira Khan"), (44, "Josh Patel")]:
        m = background_customer(w, num, name, "student")
        mules.append(m)
    w.precedents.append({"user_id": "CUS-0040", "counterparty_id": "EXT-FLAT-0040", "pattern": "mule_fan_in",
                         "decision": "clear", "note": "Transfers from flatmates for rent", "analyst": "seed",
                         "created_at": "2026-03-10", "expires_at": "2027-03-10"})
    w.tx(mules[0], at(date(2026, 10, 1), 18), "in", "faster_payment", 400, counterparty_id="EXT-FLAT-0040",
         counterparty_name="Flatmate", reference="Rent")
    northgate = w.customer(50, "Northgate Trading Ltd", customer_type="business", occupation="wholesale trading",
                           monthly_credits=20000, opened="2026-10-25")
    mule_ring(w, mules, northgate, at(date(2026, 11, 9), 9), "EXT-FLAT-0040", "EXT-OFF-0590")
    fix_collector_outflows(w, northgate)

    # Background customers
    for i in range(34):
        kind = w.rng.choices(["salaried", "cash_business", "student", "retired"], [60, 15, 15, 10])[0]
        p = background_customer(w, 100 + i, w.random_name(taken), kind)
        if w.rng.random() < 0.12:
            benign_large_credit(w, p, at(date(2026, 11, w.rng.randint(2, 27)), 11), w.rng.uniform(4, 8),
                                vague=w.rng.random() < 0.5)


def build_eval_world(w: World):
    """About 40 customers: background, plus one planted case of each scenario type with random values (DEC-006)."""
    rng = w.rng
    taken: set[str] = set()

    for i in range(24):
        kind = rng.choices(["salaried", "cash_business", "student", "retired"], [60, 15, 15, 10])[0]
        p = background_customer(w, 100 + i, w.random_name(taken), kind)
        if rng.random() < 0.15:
            benign_large_credit(w, p, at(date(2026, 10, rng.randint(2, 28)), 11), rng.uniform(4, 8),
                                vague=rng.random() < 0.5)

    # Structuring, twice
    for n in (1, 2):
        start = date(2026, rng.randint(10, 11), rng.randint(3, 20))
        p = background_customer(w, n, w.random_name(taken), "cash_business",
                                quiet=(start - timedelta(days=4), start + timedelta(days=4)))
        count = rng.choice([3, 4])
        structuring(w, p, at(start, rng.randint(9, 11)), [rng.uniform(9100, 9950) for _ in range(count)],
                    rng.sample(BRANCHES, 3), [rng.uniform(5, 22) for _ in range(count - 1)])

    # Anomalous credit → analyst (month 1) → repeat (month 2): drives the month 1 → month 2 metric
    for n in (3, 4, 5):
        p = background_customer(w, n, w.random_name(taken), "salaried")
        cp = w.ext()
        first = at(date(2026, 10, rng.randint(5, 20)), 10)
        anomalous_then_repeat(w, p, cp, "Consultancy client", "Quarterly retainer", first,
                              p["expected_monthly_credits"] * rng.uniform(4, 6), first + timedelta(days=31),
                              p["expected_monthly_credits"] * rng.uniform(4, 6),
                              "Customer showed the consultancy contract; quarterly retainer is legitimate.")

    # Round trip
    p = background_customer(w, 6, w.random_name(taken), "salaried")
    p.update(risk_rating="high", expected_monthly_credits=12000)
    out_day = date(2026, 10, rng.randint(5, 25))
    amount = rng.uniform(120000, 300000)
    round_trip(w, p, at(out_day, 11), amount, at(out_day + timedelta(days=rng.randint(10, 20)), 15),
               amount * rng.uniform(0.9, 0.97))

    # Mule ring: 5 mules into a new business account
    mules = [background_customer(w, 40 + k, w.random_name(taken), "student") for k in range(5)]
    flatmate = w.ext("EXT-FLAT")
    w.precedents.append({"user_id": mules[0]["user_id"], "counterparty_id": flatmate, "pattern": "mule_fan_in",
                         "decision": "clear", "note": "Transfers from flatmates for rent", "analyst": "seed",
                         "created_at": "2026-04-02", "expires_at": "2027-04-02"})
    w.tx(mules[0], at(date(2026, 10, 1), 18), "in", "faster_payment", rng.uniform(350, 500),
         counterparty_id=flatmate, counterparty_name="Flatmate", reference="Rent")
    collector = w.customer(50, f"{rng.choice(['Harbour', 'Summit', 'Crescent', 'Ironbridge'])} Supplies Ltd",
                           customer_type="business", occupation="wholesale trading", monthly_credits=20000,
                           opened="2026-10-20")
    mule_ring(w, mules, collector, at(date(2026, 11, rng.randint(3, 20)), 9), flatmate, w.ext("EXT-OFF"))
    fix_collector_outflows(w, collector)


#
# Output
#
def write_world(w: World, seed: int):
    w.txs.sort(key=lambda t: (t["timestamp"], t["user_id"], t["direction"], t["amount"]))
    for i, t in enumerate(w.txs, start=1):
        t["transaction_id"] = f"TX-{w.number}{i:05d}"

    labels, answers = [], []
    for t in w.txs:
        start = date(2026, 10, 1)
        when = datetime.fromisoformat(t["timestamp"])
        month = (when.year - start.year) * 12 + when.month - start.month + 1
        labels.append({"transaction_id": t["transaction_id"], **t.pop("_label"), "month": month})
    for a in w.answers:
        answers.append({"transaction_id": a["_tx"]["transaction_id"], "decision": a["decision"], "note": a["note"]})

    folder = DATA_DIR if w.number == 0 else DATA_DIR / "worlds" / f"world_{w.number}"
    folder.mkdir(parents=True, exist_ok=True)
    tables = {
        "customer_profiles": sorted(w.profiles, key=lambda p: p["user_id"]),
        "transactions": w.txs,
        "analyst_labels": labels,
        "reviewer_answers": sorted(answers, key=lambda a: a["transaction_id"]),
        "seed_precedents": sorted(w.precedents, key=lambda p: (p["user_id"], p["counterparty_id"])),
    }
    for name, rows in tables.items():
        with open(folder / f"{name}.jsonl", "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # PEP entries live in the shared watchlist; add ours once (idempotent)
    if w.pep_entries:
        pep_path = DATA_DIR / "pep_list.jsonl"
        existing = [json.loads(line) for line in pep_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        names = {e["name"] for e in existing}
        with open(pep_path, "a", encoding="utf-8") as f:
            for e in w.pep_entries:
                if e["name"] not in names:
                    f.write(json.dumps(e, ensure_ascii=False) + "\n")

    n_alert = sum(1 for l in labels if l["decision"] == "escalate")
    print(f"world {w.number} (seed {seed}): {len(tables['customer_profiles'])} customers, {len(w.txs)} transactions, "
          f"{n_alert} alert labels, {len(answers)} reviewer answers, {len(w.precedents)} seed precedents -> {folder}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--world", type=int, choices=[0, 1, 2], help="one world only (default: 0, 1 and 2)")
    args = parser.parse_args()
    for number in ([args.world] if args.world is not None else [0, 1, 2]):
        w = World(number, args.seed)
        (build_world_0 if number == 0 else build_eval_world)(w)
        write_world(w, args.seed)


if __name__ == "__main__":
    main()
