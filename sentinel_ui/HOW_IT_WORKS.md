# How the Sentinel workspace works

What happens when you press **Start**, where every number on screen comes from, and where to look behind it.
For setup and deployment, see [README.md](README.md).

> Draft for analyst review, not legal, compliance or regulatory advice. Synthetic data only.

---

## 1. The data is fixed, not generated live

All transactions were generated **once, ahead of time**, by `sentinel_aml_agent/data/generate.py` (fixed seed),
and saved as JSON Lines files:

| File | What it holds |
|---|---|
| `data/transactions.jsonl` | 1,131 synthetic transactions, 1 Oct 2026 → 25 Aug 2027 |
| `data/customer_profiles.jsonl` | KYC profile per customer (occupation, risk rating, PEP, expected monthly credits and cash, account opened) |
| `data/analyst_labels.jsonl` | The "right answer" per transaction. **Never shown to the agents**; the UI uses it for one tile only (false positives avoided) |
| `data/reviewer_answers.jsonl` | Scripted analyst answers (e.g. Sophie's "Annual bonus — employer verified via payslip") |
| `data/seed_precedents.jsonl` | Analyst decisions from before the stream starts (e.g. Liam's old "flatmates" clearance) |

**Start** replays `transactions.jsonl` in time order. Every run sees the same transactions; new data only appears if
someone reruns the generator and redeploys.

## 2. What happens to each transaction

```
transactions.jsonl ──(Start, 8 per second)──►  1. RULES  (plain Python, instant, no AI)
                                                ├─ score < 30  → "Cleared by rules"           (~97%)
                                                └─ score ≥ 30  → "Under review" ↓              (~3%)
                                               2. AGENTS (Deep Agents supervisor + specialists)
                                                ├─ confident, escalate → "Flagged"
                                                ├─ confident, clear    → "Cleared"
                                                └─ unsure / hard flag  → "Needs analyst" ↓
                                               3. ANALYST (you): Clear / Escalate + note
                                                └─ the note is saved as a precedent (memory), valid 12 months
```

**Step 1, rules** (`sentinel_aml_agent/rules/scorer.py`). Each transaction gets points for: cash just under £10,000,
structuring (3+ such deposits in 72 h), cash velocity, a credit or debit ≥ 3× the customer's expected monthly
credits, a first payment to a new counterparty, pass-through (≥ 90% of the last 24 h's money sent on), round trips,
and fan-in into a new account. Scores for high-risk or PEP customers are ×1.3. Accounts in a confirmed mule ring
score at least 60.

**Step 2, agents** (`sentinel_aml_agent/agents.py`). A supervisor reads the transaction and sends it to specialists
running in parallel:
- **pattern analyst**: this customer's last 30 days (structuring, spikes, round trips);
- **KYC & precedent**: profile, sanctions and PEP screening, earlier analyst decisions;
- **fund-flow**: the one tool allowed to look across customers, to find mule rings. Every use is logged.

The supervisor then records a verdict with `record_decision`. Code, not the AI, applies the safeguards:
- a **hard red flag** (sanctions, PEP, confirmed ring) overrides any precedent;
- a precedent only counts for the **same customer, counterparty and pattern**, and only until it **expires**;
- confidence **below 0.7**, a grey-zone score, or a hard flag on a "clear" → **pause for the analyst**.

If the final verdict is escalate, a **SAR writer** drafts a Suspicious Activity Report from the evidence.

**Step 3, analyst.** The pause becomes a "Needs your decision" alert. Your answer resumes the agents, and your note is
saved as a precedent that the agents can cite next time ("Sentinel remembers…").

Up to **4 investigations run at once** (one customer at a time each). An investigation waiting for an analyst holds
one of the 4 slots, so unanswered alerts slow the queue down.

## 3. Modes: what "live" means

Set by `SENTINEL_UI_MODE` (on the VPS: `/opt/sentinel-aml-ui/sentinel_ui/.env`). Only step 2 changes.

| Mode | Step 2 (agents) | AI cost | Banner |
|---|---|---|---|
| `offline` | Skipped: every flagged transaction goes straight to the analyst | none | yellow "Agents offline" |
| `live` | Real model calls (`gpt-6-sol` via the LangSmith gateway), ~20 s and ~12 calls each | yes | "Live" |
| `record` | Same as live, **and** each investigation is saved to the recording file | yes | "Live, recording for replay" |
| `replay` | Recorded agent steps played back at 3× their real pace | none | purple "REPLAY: recorded at …" |

In **replay**, the analyst step is still real: pauses still wait for you, and your note still becomes a precedent.
Only the agents' steps and verdicts come from the recording. Transactions listed in `SENTINEL_LIVE_TX` run live
even in replay.

## 4. Where to see what happened

| What | Where |
|---|---|
| The recording | VPS: `/opt/sentinel-aml-ui/sentinel_ui/recordings/world0.json`. One entry per investigation: every step with its time offset, the decision record, the SAR draft, model calls, tokens and the LangSmith run ID |
| Every model call | LangSmith → project `fsi-hackathon-<ATTENDEE_NAME>` (e.g. `fsi-hackathon-sanjeev`). In the UI, "LangSmith trace" on an investigation opens it (sign in to LangSmith first) |
| One investigation's steps | Live Stream → **Agent activity** panel, or Flagged → case → **Investigation steps** |
| Uses of the cross-customer tool | Case → **Audit** → "Cross-customer graph tool" |
| Analyst actions | Case → **Audit** → "Case history" |
| Server log | `ssh root@srv1475135.hstgr.cloud 'docker logs -f sentinel-aml-ui'` |

---

## 5. The summary bar, tile by tile

Every tile is computed by the server from the current session (`sentinel_ui/api/sentinel_api/session.py`,
`Session.counters`). Nothing is a fixed demo number. Hover a tile with an ⓘ to see its basis.

### Left: what the stream is doing

| Tile | Formula | Notes |
|---|---|---|
| **Received** | transactions released so far / 1,131 | Fast-forward releases the next 10 months at once |
| **Cleared by rules** | rows cleared by rules ÷ received | Rule score below 30; no AI involved |
| **Under review** | rows waiting for or inside an agent investigation | Includes ones queued behind the 4 slots |
| **Flagged** | rows whose verdict is **escalate**, by the agents or by an analyst | |
| **Needs analyst** | rows waiting for an analyst decision right now | Also shows a row whose investigation errored |
| **Agent model calls** | model calls summed over **finished** investigations | Counts the supervisor and every specialist call. Tooltip: investigations and tokens. A running investigation is added when it finishes. In replay, these are the recorded counts |

Agent-cleared rows ("Cleared", green) are counted too but have no tile of their own: they're the difference between
Under review and the other agent outcomes.

### Right: the value ticker (click it to open Results)

| Tile | Formula | What it means |
|---|---|---|
| **Alerts: rules-only → Sentinel** | left: rows with rule score ≥ 30. Right: rows that are **Flagged**, **Needs analyst**, or were decided by an analyst | How many alerts a rules-only system would raise vs how many an analyst actually had to look at with Sentinel. Both use the same rules, so the comparison is fair |
| **False positives avoided** | rows where rules-only would escalate **and** the synthetic label says *clear* **and** Sentinel cleared it **without** an analyst | The only place the labels are used |
| **Analyst hours saved** | (rules-only alerts − Sentinel alerts − still under review) × 20 min ÷ 60 | 20 minutes per alert is an **assumption** (shown in the tooltip). Transactions still under review aren't counted as saved |
| **Tokens: Sentinel vs all-to-agents** | tokens used so far vs (average tokens per finished investigation × 1,131) | The right number is an **estimate** of sending every transaction to the agents. Tokens, not money: there's no published price for the gateway model (DEC-005) |

In **offline** mode the two alert numbers are equal and the savings are 0, because every flagged transaction goes to
the analyst.

---

## 6. Other numbers

### Flagged queue (each case card)

A **case** groups flagged transactions: all accounts in one confirmed mule ring become one network case
(`CASE-RING-<collector>`); otherwise it's one case per customer and pattern (`CASE-<customer>-<pattern>`).

| On the card | How it's computed |
|---|---|
| Accounts | Our bank's accounts on the case graph |
| Flagged · transfers | Flagged / analyst-decided transactions in the case · money movements on the graph |
| £ total | Sum of all transfers on the graph |
| Dates | First transfer → latest flagged transaction |
| Verdict | **escalate** if any member's agent or final decision is escalate |
| Confidence | The **lowest** confidence among members |
| Severity | Highest risk score, +15 if any hard red flag, +10 for a network case, capped at 100 |
| Order | Needs analyst first, then highest severity, then newest |

### Case view

**Graph.** Nodes are accounts. Arrows are money movements, and line width grows with the amount. For a mule ring
(columns, left to right): **source** (outside senders) → **mule** (pass-through accounts) → **hub** (collector) →
**sink** (where money leaves). For one customer, the customer sits in the middle with counterparties around it,
covering the 72 hours before each flagged transaction. A red dashed ring marks a **hard red flag**; a small red flag
marks a fired red flag. A dashed outline means another bank.

**Title.** A plain-words finding built from the graph, e.g. *"5 accounts funnelled £8,418 into Northgate Trading Ltd
within 65 hours; £8,250 then left for Kestrel Exports FZE"*.

**Metrics** (`sentinel_ui/api/sentinel_api/cases.py → metrics`):

| Mule ring | How |
|---|---|
| Mule accounts / distinct senders | Count of mule / source nodes |
| Hops | Always 3: source → mule → hub → cash-out |
| Total into hub | Sum of transfers into the hub |
| Passed on by each mule | Each forward ÷ what that mule received in the previous 24 h |
| Typical holding time | Median hours between a mule's last incoming payment and its forward |
| Time to cash-out | Hours from the last transfer into the hub to its first payment out |
| Countries | Distinct countries on the case's transfers |

| One customer | How |
|---|---|
| Money in / out | Credits into / payments out of the customer in the window |
| Just below £10,000 | Credits of £9,000–£9,999, and at how many branches |
| Expected a month | From the KYC profile |

**Red flags.** Each is **Fired**, **Not fired**, or **No data**, with the evidence underneath. Flags that don't
usually apply to the pattern are greyed out.

| Red flag | Fires when |
|---|---|
| Newly opened account with a sudden jump in volume | A case account was under 90 days old when the case began, and received ≥ 5× its own inflow of the previous 30 days |
| Shared device / IP | Always **No data**: device and IP aren't in the data |
| Pass-through | Someone sent on ≥ 90% of what they received in the previous 24 h |
| Many transfers just below a threshold | 3+ credits of £9,000–£9,999 into the hub or customer |
| Consolidation then cash-out | The hub sent out ≥ 50% of what it collected |
| Large deposit then split | A credit ≥ 3× expected monthly, then 5+ recipients within 24 h |
| No payroll / vendor relationship | ≥ 80% of payment recipients had never been paid before |
| Several banks, currencies or countries | More than one country or currency on the case |

Thresholds are listed under **Thresholds** on the panel; they match the rules tier.

**Timeline and replay.** Transfers in time order. **Replay** draws them one by one; key moments (first money in, the
hub's peak, the cash-out, when Sentinel flagged it) pause briefly with a caption.

**Net flow strips.** The data has no balance column, so each mule's or hub's line is **money in minus money out since
the case window opened**. A mule shows a rise and then a fall back to near zero (pass-through).

**Agent explanation.** Per transaction: verdict, confidence, who decided (agent or human), the agent's reason, why it
went to an analyst, hard flags, precedents cited or overridden, the analyst's note, and the investigation steps.

### Memory cards (purple)

| Card | Shown when |
|---|---|
| **Sentinel remembers** | The agents relied on a valid precedent (same customer + counterparty + pattern, not expired) |
| **OVERRIDDEN** | A precedent existed but a hard red flag beat it (e.g. Liam's old clearance once the ring is confirmed) |
| **Saved to memory** | An analyst decided with a note; it applies to that customer + counterparty + pattern for 12 months |

### Results view

Read from `sentinel_aml_agent/results/eval_summary.json`, written by the eval team's LangSmith experiments; the UI
never runs evals. It shows the **held-out test split**, rules-only vs Sentinel. The headline is computed from those
numbers: false-positive cut = (rules-only rate − Sentinel rate) ÷ rules-only rate, and "no loss of recall" only if
Sentinel's recall on planted cases is at least the rules-only recall. The definitions of the eval metrics are the eval
team's (`sentinel_aml_agent/evals/`, `DECISIONS.md`). The "This session so far" box repeats the live tiles above,
which come from the stream, not from the eval.
