# UI Spec: AML Analyst Workspace (Live Stream, Flagged Transactions, Network View)

*Functional requirements only · Sentinel (AML transaction monitoring) · 2026-11-25*
*Target: a **dedicated analyst application**, separate from the submitted notebook, using the same agent backend. These requirements are **technology-independent**: they say what the analyst and the audience must be able to see and do, not how it's built.*
*Related: [USE_CASE.md](../../../../USE_CASE.md) · [DEMO_SCRIPT.md](../../../../DEMO_SCRIPT.md)*

> Every screen shows: *"Draft for analyst review, not legal, compliance or regulatory advice. Synthetic data only."*

## 1. Purpose

Give a **bank's AML analyst** one workspace where they:
1. **Watch the live stream** of incoming transactions.
2. **See transactions flagged in that stream** as Sentinel's agents process them in the background.
3. **Open a flagged-transactions section** to review each flag, including **visual network views** of mule rings, fan-in and fan-out.

The network views let the analyst **see, understand and act on** suspicious money flows that span several accounts:

- **Money-mule ring:** money bounced through several intermediary (mule) accounts, often across banks or countries, to hide its origin.
- **Fan-in (many → one):** many accounts send money to one collecting account in a short period, usually followed by a cash-out.
- **Fan-out (one → many):** one account quickly splits a large sum into many smaller transfers to unrelated recipients.

These patterns can't be seen one transaction or one customer at a time. The UI must make the network shape, the timing and the red flags obvious at a glance, and show why the agent reached its verdict.

## 2. Users

| User | Needs from this UI |
|---|---|
| **Bank's AML analyst** (the actor) | Watch incoming transactions; notice flags as they appear; review flagged transactions; see the network behind them; check the evidence; decide `clear` / `escalate`; generate a SAR draft |
| Demo audience / judges | Follow the analyst's journey and understand each pattern within seconds |

The UI has **four main areas**, reachable from a persistent navigation bar:

| Area | What it is |
|---|---|
| **Live Stream** | The real-time feed of incoming transactions, with flags appearing as the agents finish processing |
| **Flagged Transactions** | The analyst's work queue: every flagged transaction and case, with its status |
| **Case / Network View** | One flagged case in depth: network graph, metrics, red flags, timeline, accounts, agent explanation, actions |
| **Results** | Rules-only vs Sentinel on the labelled eval set (EX-13) |

Across all areas: the summary bar with the live value ticker (EX-3), the agent activity panel (EX-1) and "needs your decision" alerts (EX-4).

## 2a. Analyst journey

1. The analyst opens the workspace and lands on **Live Stream**. Transactions scroll in as they arrive.
2. Most transactions are cleared instantly by rules and shown as cleared. A few are picked up by the agents and shown as **"Under review"** while the agents work in the background.
3. When the agents finish, the transaction's status updates in place: **cleared** (optionally citing a precedent), **flagged** (escalated by the agent), or **needs analyst** (the agent is unsure). Flagged items stand out and a counter updates.
4. The analyst opens **Flagged Transactions** (from the navigation bar, the counter, or a flagged row) and sees the queue.
5. The analyst opens one flagged item. If it belongs to a network pattern, the **Case / Network View** shows the mule ring, fan-in or fan-out visually.
6. The analyst reviews the evidence and the agent's explanation, then **clears** or **escalates** with a note, and optionally generates a SAR draft.
7. The decision is saved as a precedent; the item's status updates everywhere, including in the live stream.

## 3. Definitions

| Term | Meaning in this UI |
|---|---|
| Node | One account |
| Edge | One or more transfers from one account to another, aggregated over the selected time window |
| Hub | The central account of a fan-in (collector) or fan-out (distributor) |
| Mule | An account acting as a pass-through: money in, almost all of it out soon after |
| Hop | One step along a chain of transfers |
| Case | A flagged pattern under review, linked to one or more accounts and transactions |
| Flag | The agent's verdict that a transaction needs attention: escalated, or sent to the analyst |
| Processing status | Where a transaction is in the pipeline: `Received` → `Cleared by rules` / `Under review (agents)` → `Cleared` / `Flagged` / `Needs analyst` |
| Precedent | A past analyst decision saved in long-term memory, which the agents can cite or override |
| Rules-only baseline | What the rules tier alone would have flagged, computed alongside Sentinel for comparison |

## 3a. Priorities

| Priority | Meaning |
|---|---|
| **P1** | Must have. The demo doesn't work, or loses a judging point, without it |
| **P2** | Strong addition. Clearly lifts the demo; build once all P1 items work end to end |
| **P3** | Only if time allows. Polish; cut first if the schedule slips |

### Priority of the core requirements (sections 4.1–4.10)

| Section | Priority | Exceptions |
|---|---|---|
| 4.1 Live Stream | P1 | LS-8 filters: P2 |
| 4.2 Flagged Transactions | P1 | FQ-5 filters, FQ-6 search: P2 |
| 4.3 Case / Network View layout | P1 | CV-3 previous/next case: P2 |
| 4.4 Network graph view | P1 | FR-4.7 expand hops, FR-4.8 time window: P2; FR-4.11 node cap: P3 |
| 4.5 Pattern metrics and red flags | P1 | FR-5.3 configurable thresholds: P3 |
| 4.6 Timeline / flow replay | P1 | — |
| 4.7 Account detail panel | P1 | FR-7.5 full transaction list: P2 |
| 4.8 Agent explanation | P1 | — |
| 4.9 Analyst actions | P1 | FR-9.2 mark accounts: P2; FR-9.5 export: P3 |
| 4.10 Audit | P2 | FR-10.2 cross-customer tool log: P1 (backs a Q&A answer) |

The experience requirements in section 4.11 each carry their own priority.

## 4. Functional requirements

### 4.1 Live Stream

- **LS-1** Show incoming transactions in real time, newest at the top, in a continuously updating list.
- **LS-2** Each row shows: time, sender (account, customer name), receiver (account, customer name or business), amount, currency, payment format, and **processing status**.
- **LS-3** Processing status is shown visually and updates **in place** as the pipeline runs:

| Status | Meaning |
|---|---|
| `Cleared by rules` | Cleared instantly by the rules tier, with no agent involved |
| `Under review` | Picked up by the agents; processing in the background (shown with a progress indicator) |
| `Cleared` | Agents cleared it; shows "precedent" if a past analyst decision was cited |
| `Flagged` | Agents escalated it (high confidence) |
| `Needs analyst` | Agents are unsure; waiting for the analyst's decision |

- **LS-4** `Flagged` and `Needs analyst` rows **stand out** from the rest of the stream, show the detected pattern (e.g. `Structuring`, `Fan-in`, `Fan-out`, `Mule ring`), and briefly highlight when they first appear, so the analyst notices them.
- **LS-5** When a flagged transaction is part of a network case, its row shows a **network badge** and the case ID. Other rows in the visible stream that belong to the same case are marked as related.
- **LS-6** A summary bar above the stream shows live counters: transactions received, % cleared by rules, under review, flagged, needs analyst, and agent (LLM) calls so far.
- **LS-7** Stream controls: **Start**, **Pause**, **Resume**, and **Fast-forward** (jump ahead by a set period, e.g. 10 months, for the demo). Pausing stops new rows appearing but background processing continues.
- **LS-8** The analyst can filter the stream to show only `Flagged` / `Needs analyst` rows, or only one customer or account.
- **LS-9** Selecting any row opens a short transaction detail (all fields, status, and for flagged rows the agent's one-line reason), with a link **"Open case"** to the Case / Network View.
- **LS-10** A flag counter in the navigation bar shows the number of open flagged items and links to Flagged Transactions.

### 4.2 Flagged Transactions (work queue)

- **FQ-1** List every flagged item: transactions with status `Flagged` or `Needs analyst`, grouped into **cases** when several transactions belong to the same pattern.
- **FQ-2** Each item shows: case ID, pattern type (`Structuring` / `Fan-in` / `Fan-out` / `Mule ring` / `Anomalous credit` / `Round-tripping`), lead or hub account, number of accounts and transactions involved, total amount, time span, agent verdict, confidence, why it was flagged (one line), and status (`New` / `Awaiting analyst` / `Cleared` / `Escalated`).
- **FQ-3** Default order: `Needs analyst` first, then by severity, then newest first.
- **FQ-4** Network patterns (mule ring, fan-in, fan-out) show a **small thumbnail of the network shape** in the list, so the pattern can be recognised before the case is opened.
- **FQ-5** Filters: pattern type, status, verdict, confidence range, date range, minimum total amount. Quick filters: **"Needs my decision"**, **"Network cases"**.
- **FQ-6** Search by account ID, customer name or case ID.
- **FQ-7** New flagged items appear in the queue as soon as the agents flag them, without the analyst refreshing, and are marked as new until opened.
- **FQ-8** Selecting an item opens the **Case / Network View** (4.3 onwards). Items that aren't network patterns (e.g. structuring by one customer) open the same view, showing the customer's transaction timeline instead of a multi-account graph.
- **FQ-9** When an item is resolved, its status updates here and in the Live Stream.

### 4.3 Case / Network View (layout)

- **CV-1** Opening a case shows, on one screen: the **network graph** (4.4) as the main element; **metrics and red flags** (4.5) beside it; the **timeline** (4.6) beneath it; and the **agent explanation** (4.8) and **analyst actions** (4.9) in a side panel. The **account detail** (4.7) opens when an account is selected.
- **CV-2** A header shows the case ID, pattern type, the plain-language finding (see FR-4.6), verdict, confidence and status.
- **CV-3** The analyst can go back to Flagged Transactions or to the Live Stream, and move to the previous or next case in the queue, without losing filters.

### 4.4 Network graph view

- **FR-4.1** Show the case's accounts as nodes and the transfers between them as **directed edges**, with arrows showing which way the money moves.
- **FR-4.2** Edge thickness reflects the total amount. Edge labels show the total amount and number of transfers, and can be switched on or off.
- **FR-4.3** Node styling shows the account's role: **hub**, **mule / pass-through**, **source** (money comes from outside the case), **sink / cash-out**, or **other**. A legend explains every style.
- **FR-4.4** Nodes that trigger a red flag show a flag marker. Nodes with a **hard red flag** (sanctions hit, PEP, confirmed network membership) are visibly distinct.
- **FR-4.5** Layout follows the pattern:
  - **Fan-in:** senders arranged around one central collector, with arrows pointing inwards.
  - **Fan-out:** one central distributor, with arrows pointing outwards.
  - **Mule ring:** left to right, from source through mule layers to the hub and cash-out.
- **FR-4.6** The graph title states the finding in plain words, e.g. *"5 accounts funnelled £48,200 into Northgate Trading Ltd within 36 hours"*.
- **FR-4.7** The user can expand the network by **1 or 2 more hops** from any node, and collapse it again.
- **FR-4.8** The user can change the **time window** (e.g. 24h, 72h, 7 days, 30 days). The graph and every metric update to match.
- **FR-4.9** Pointing at or selecting a node or edge highlights it and its direct neighbours, and dims everything else.
- **FR-4.10** Selecting a node opens the account detail panel (4.7). Selecting an edge lists its underlying transfers: timestamp, amount, currency, payment format.
- **FR-4.11** Very large networks are capped at a set node limit, with a *"+N more accounts"* indicator, so the view stays readable.

### 4.5 Pattern metrics and red flags

- **FR-5.1** Show a metrics panel next to the graph with the measures that matter for the case's pattern:

| Pattern | Metrics shown |
|---|---|
| **Fan-in** | Number of distinct senders; total received; number of transfers just below the reporting/monitoring threshold; how long the money stayed before cash-out; cash-out type (large withdrawal, wire, crypto) |
| **Fan-out** | Size and time of the large incoming deposit; number of distinct recipients; total sent; time from deposit to the last outgoing transfer; share of recipients with no previous relationship |
| **Mule ring** | Number of mule accounts; number of hops; % of incoming money passed on by each mule; typical holding time; end-of-day balances; number of banks, currencies and countries involved |

- **FR-5.2** Show a **red-flag checklist**. Each flag is marked as fired or not fired, with the evidence behind it (values, transaction IDs, accounts):

| Red flag | Applies to |
|---|---|
| Newly opened account with a sudden jump in volume | Mule ring, Fan-in |
| Shared device ID or IP address across unrelated accounts | Mule ring |
| Pass-through behaviour: near-zero end-of-day balance; most incoming money leaves within hours | Mule ring |
| Many unrelated transfers just below a reporting/monitoring threshold | Fan-in |
| Consolidation followed immediately by a large withdrawal, wire or crypto purchase | Fan-in |
| A large deposit followed quickly by many smaller transfers to unrelated recipients | Fan-out |
| No payroll or vendor relationship explains the outgoing transfers | Fan-out |
| Several banks, currencies or countries crossed in a short time | Mule ring, Fan-out |

- **FR-5.3** Detection thresholds can be configured: time window, minimum number of counterparties, near-threshold band, pass-through %, and holding time. The values in use are shown in the panel.
- **FR-5.4** If the data needed for a flag isn't available (e.g. device/IP missing from a data source), the flag shows **"No data"**, never "Not fired".

### 4.6 Timeline / flow replay

- **FR-6.1** Show a timeline of the case's transfers in time order, linked to the graph: selecting a transfer on the timeline highlights its edge.
- **FR-6.2** Provide **replay** (play / pause / step), which draws the edges one by one in time order, so viewers watch money arrive and leave.
- **FR-6.3** Mark key moments on the timeline: first incoming transfer, the hub's peak balance, the cash-out, and the moment the agent flagged the case.
- **FR-6.4** For each mule and hub, show a small **balance-over-time** view that makes pass-through behaviour visible (balance rising, then quickly falling back to near zero).

### 4.7 Account detail panel

- **FR-7.1** For the selected account, show: account ID, customer name (synthetic), bank, account age, KYC risk rating, PEP / sanctions status, and expected monthly volume.
- **FR-7.2** Show money in and out for the time window, the number of counterparties, and this account's role in the case.
- **FR-7.3** Show the red flags fired for this account.
- **FR-7.4** Show **precedents** (past analyst decisions) for this account, with their dates, notes and expiry. If a precedent was **overridden** by a hard red flag, show that clearly with the reason, e.g. *"Cleared 2026-03-10: overridden, confirmed fan-in network membership"*.
- **FR-7.5** Link to the account's full transaction list.

### 4.8 Agent explanation

- **FR-8.1** Show the agent's verdict (`clear` / `escalate`), confidence, and the pattern it identified.
- **FR-8.2** Show a short, plain-language explanation of the verdict that refers to specific accounts, amounts and times.
- **FR-8.3** Show a step-by-step summary of the investigation: which sub-agents ran (pattern analyst, KYC & precedent, fund-flow, SAR writer), which tools they called, and what each found.
- **FR-8.4** List every precedent the agent **cited** or **overrode**, with the reason.
- **FR-8.5** Provide a link to the full trace in LangSmith.
- **FR-8.6** Show why a case went to an analyst (e.g. "confidence 0.55 below threshold 0.7", "hard red flag present").

### 4.9 Analyst actions

- **FR-9.1** For a case awaiting review, the analyst can choose **Clear** or **Escalate** and must add a note.
- **FR-9.2** The analyst can mark individual accounts as **confirmed mule**, **hub**, or **not involved**. Confirmed accounts carry a hard red flag in all future cases.
- **FR-9.3** Submitting a decision resumes the paused agent and saves the decision as a precedent, with an expiry date, in long-term memory.
- **FR-9.4** For escalated cases, the analyst can **generate a SAR draft**. The draft includes the network summary, timeline, red flags with evidence, the accounts involved, the precedents cited or overridden, and a narrative. It carries the "not regulatory advice" stamp.
- **FR-9.5** The analyst can export the case (graph snapshot, metrics, timeline, decision) for the audit file.

### 4.10 Audit

- **FR-10.1** Every analyst action is recorded with the user, time, decision and note.
- **FR-10.2** Every use of the **cross-customer graph tool** by the fund-flow agent is recorded and visible from the case.
- **FR-10.3** The case history shows all status changes in order.

### 4.11 Experience and demo requirements

These make the agents' background work, their memory and the value they deliver **visible**, since those are what judges score.

#### P1: Must have

**EX-1 Agent activity panel (P1)**
- **EX-1.1** While a transaction is `Under review`, show its investigation live as a row of steps: **Supervisor → Pattern analyst → KYC & precedent → Fund-flow → Verdict**. Only the sub-agents that actually run are shown.
- **EX-1.2** Each step shows its state (`waiting` / `working` / `done`) and, when done, a one-line finding, e.g. *"Recalled 3 prior deposits, £28,500 in 48h"*.
- **EX-1.3** The panel is visible from the Live Stream (for the transaction currently being investigated) and from the Case View (as the full investigation record, replacing a plain-text list for FR-8.3).
- **EX-1.4** When several transactions are under review at once, the panel shows the most recent and gives a count of the others; the analyst can switch between them.
- **EX-1.5** The final step shows the verdict, confidence, and where the case went (`auto-cleared` / `escalated` / `sent to analyst`) with the reason (FR-8.6).

**EX-2 Memory moments (P1)**
- **EX-2.1** When the agents **cite a precedent**, show a distinct memory card: *"Sentinel remembers: cleared [n] months ago by [analyst] — '[note]'. Valid until [date]."*
- **EX-2.2** When the agents **override a precedent**, show the same card with a clear **OVERRIDDEN** marker and the reason, e.g. *"Confirmed fan-in network membership (hard red flag)"*.
- **EX-2.3** When an analyst decision is **saved as a precedent** (FR-9.3), show a confirmation card: *"Saved to memory: applies to [customer + counterparty + pattern] until [date]."*
- **EX-2.4** Memory cards appear in the Live Stream row (as a compact badge that expands), the agent activity panel, and the Case View's agent explanation.
- **EX-2.5** Memory cards use one consistent visual identity (see EX-9), so the audience learns to recognise "memory" at a glance.

**EX-3 Live value ticker (P1)**
- **EX-3.1** The summary bar (LS-6) adds a value comparison, updated live:
  - alerts **rules-only would have raised** vs alerts **Sentinel raised**
  - false positives avoided (where labels are available)
  - estimated **analyst hours saved** (alerts avoided × an assumed minutes-per-alert, configurable, with the assumption visible on request)
  - **LLM cost so far** vs the estimated cost if every transaction went to the LLM
- **EX-3.2** Every figure can show what it's based on, on request, and shows only computed values, never fixed demo numbers.
- **EX-3.3** Selecting the ticker opens the **Results view** (EX-13).

**EX-4 "Needs your decision" alert (P1)**
- **EX-4.1** When the agents pause for the analyst (`Needs analyst`), an alert slides in on whatever screen the analyst is on.
- **EX-4.2** The alert shows the customer, amount, pattern, the agent's question, its leaning (e.g. *"leaning clear, confidence 0.55"*) and the main reason it's unsure.
- **EX-4.3** Actions on the alert: **Open case**, **Clear**, **Escalate**. Clear and Escalate from the alert still require a note (FR-9.1), entered inline.
- **EX-4.4** Alerts stay until acted on or dismissed; dismissed alerts remain in Flagged Transactions. Several alerts stack, newest on top.
- **EX-4.5** Acting on the alert resumes the paused agent (FR-9.3) and the result appears in the stream within the same view.

**EX-5 Animated money flow (P1)**
- **EX-5.1** During replay (FR-6.2), money visibly travels along each edge in time order, with the amount shown as it moves.
- **EX-5.2** Node size or a fill level reflects the account's **current balance** during replay: mules visibly fill and then drain to near zero; the hub visibly grows until the cash-out.
- **EX-5.3** Key moments (FR-6.3) pause the replay briefly with a caption, e.g. *"Northgate receives £48,200 in 36 hours"* → *"£47,500 wired out 2 hours later"*.
- **EX-5.4** Replay speed is adjustable (e.g. 1×, 2×, 4×) and the replay can be scrubbed using the timeline.
- **EX-5.5** Opening a network case **auto-plays** the replay once (can be turned off), so the shape and the story land without a click.

**EX-16 Motion that explains (P1, new)**
- **EX-16.1** Every status change happens **in place with a visible transition** (e.g. `Under review` → `Flagged`), so the viewer sees *what* changed and *where*. Rows and cards never jump or reorder without the change being traceable.
- **EX-16.2** Opening a case from a stream row, queue item or alert **visibly continues from where it was selected** (the item expands into the case), so the audience doesn't lose their place.
- **EX-16.3** When the agents flag a network case, the involved rows in the Live Stream are **briefly linked together** (e.g. highlighted as a group) before the case appears in the queue, showing the pattern forming in the stream itself.
- **EX-16.4** Motion can be reduced or turned off by the user; every piece of information conveyed by motion is also available without it.

**EX-13 Results view (P1, new)**
- **EX-13.1** A dedicated screen comparing **rules-only vs Sentinel** on the held-out labelled set: false-positive rate, recall on planted cases, decision accuracy, review routing, analyst reviews month 1 → month 2, correct precedent overrides, % of transactions reaching an LLM, and cost per 1,000 transactions.
- **EX-13.2** Results are loaded from the stored LangSmith experiments. The view shows the experiment names, date and dataset size, and links to the experiments in LangSmith.
- **EX-13.3** The headline improvement is stated in one plain sentence at the top, e.g. *"Sentinel cut false positives by [X]% with no loss of recall"*, using only real results.
- **EX-13.4** Reachable from the navigation bar and from the value ticker (EX-3.3).

#### P2: Strong additions

**EX-6 SAR draft with linked citations (P2)**
- **EX-6.1** The SAR draft (FR-9.4) shows as a readable document with sections: subject, summary, pattern, timeline, evidence, accounts involved, precedents cited or overridden, narrative.
- **EX-6.2** Every factual statement in the narrative is linked to its source: a transaction, an edge, an account or a red flag.
- **EX-6.3** Pointing at or selecting a statement highlights its source in the graph and timeline, shown side by side with the draft.
- **EX-6.4** Any statement without a source is visibly marked as **unsupported**, so it can't be passed off as evidence.
- **EX-6.5** The analyst can edit the draft and export it as a shareable document with the "not regulatory advice" stamp.

**EX-7 Benign look-alike comparison (P2)**
- **EX-7.1** From a network case, the analyst can open a **side-by-side comparison** with a cleared case that has the same shape (e.g. a mule fan-out next to a payroll fan-out).
- **EX-7.2** Both graphs use the same layout and scale. Below them, the red flags are listed for both, showing which fired on one and not the other, and why.
- **EX-7.3** The comparison states the deciding difference in one line, e.g. *"Same shape; the payroll recipients are long-standing employees with matching monthly amounts."*

**EX-8 Presenter mode (P2)**
- **EX-8.1** A presenter mode, toggled by a keyboard shortcut, enlarges text, hides non-essential panels, and keeps the summary bar and value ticker visible.
- **EX-8.2** **Scenario shortcuts** inject each demo scenario into the stream on demand (structuring, ambiguous credit, precedent payoff, mule ring, fan-out, benign look-alike), so scenes happen on cue.
- **EX-8.3** **Scene shortcuts** jump straight to a prepared state (e.g. "mule ring case open, replay ready") to recover instantly from a stall.
- **EX-8.4** Stream speed control (e.g. 1×, 5×, 20×) and a **reset** that returns the whole demo to its starting state.
- **EX-8.5** A small presenter-only overlay lists the shortcuts and the current scene; it can be hidden.
- **EX-8.6** A **replay mode** serves cached agent results from a previous run, so the demo works without the network or the LLM.

**EX-9 Consistent colour meanings (P2)**
- **EX-9.1** One set of meanings is used everywhere (stream, queue, graph, cards, timeline): **green** = cleared, **amber** = under review / needs analyst, **red** = flagged / escalated, **purple** = memory (precedent cited, saved or overridden), **grey** = cleared by rules.
- **EX-9.2** Colour is never the only signal: every status also has an icon and a text label.
- **EX-9.3** A legend is available from every screen.

**EX-14 Case story mode (P2, new)**
- **EX-14.1** A **"Tell the story"** action on a case plays a guided walkthrough: the replay (EX-5) runs; red flags tick on one by one as their evidence appears; the agent activity steps (EX-1) light up in order; memory cards (EX-2) appear at the moment they were used; and the verdict is revealed last.
- **EX-14.2** Each step has a short caption, and the presenter can step forward and back.
- **EX-14.3** Total length for a typical case is configurable, with a default of about 30 seconds.

**EX-17 Command centre view (P2, new)**
- **EX-17.1** A single overview screen, suitable as the **opening shot** of the demo, combines: the Live Stream (compact), the agent activity panel, the value ticker, the "needs your decision" alerts, and a live mini network of the most recently flagged case.
- **EX-17.2** The mini network updates when a new network case is flagged; selecting it opens the full Case View.
- **EX-17.3** The command centre is the default landing screen in presenter mode.

**EX-15 Shareable deep links (P2, new)**
- **EX-15.1** Every case, account and SAR draft has its own direct link that opens directly in that state, including the selected node and time window.
- **EX-15.2** Opening a direct link in a new window works without first visiting the Live Stream.

#### P3: Only if time allows

**EX-10 "Ask Sentinel" on a case (P3)**
- **EX-10.1** A question box in the Case View accepts plain-language questions about the case, e.g. *"Why did you flag Northgate?"*, *"Which mule moved the most money?"*
- **EX-10.2** Answers use only the case's evidence, cite their sources the same way as EX-6.2, and say so when the evidence doesn't answer the question.
- **EX-10.3** Suggested questions are shown as one-click prompts.
- **EX-10.4** In presenter mode, answers to suggested questions can be served from cache (EX-8.6).

**EX-11 Pattern heat strip (P3)**
- **EX-11.1** Above the Flagged Transactions queue, show today's flags by pattern type (structuring, fan-in, fan-out, mule ring, anomalous credit, round-tripping) as a compact bar.
- **EX-11.2** Selecting a pattern filters the queue to that pattern.

**EX-12 Keyboard shortcuts (P3)**
- **EX-12.1** Analyst shortcuts: `C` clear, `E` escalate (both open the note field), `J` / `K` next / previous case, `R` replay, `S` generate SAR draft, `/` search, `?` show all shortcuts.
- **EX-12.2** Shortcuts never complete a decision without the required note.

## 5. Scenario acceptance criteria (demo)

| # | Scenario | The UI must show |
|---|---|---|
| 0 | **Analyst journey end to end** | The Live Stream runs; most rows go `Cleared by rules`; a few go `Under review` then `Flagged` / `Needs analyst` in place; the flag counter goes up; the analyst opens Flagged Transactions, opens a network case, sees the graph, decides, and the new status appears in both the queue and the stream |
| A | **Mule ring → fan-in** (seeded: Liam Walsh, Chloe Evans, Ben Taylor, Amira Khan, Josh Patel → Northgate Trading Ltd) | Many senders → 5 mules → Northgate as the hub, then a cash-out; pass-through flags on all 5 mules; their balance views falling to near zero; Northgate as a new account with a sudden jump in volume; Liam's earlier clearance shown as **overridden**; verdict `escalate` |
| B | **Fan-out** (IBM HI-Small sample, e.g. account `800737690`, or a seeded equivalent) | One distributor → 7+ recipients across banks and currencies within a day; the large-deposit-then-split flag; the replay showing the outgoing transfers one after another |
| C | **Fan-in with near-threshold transfers** (seeded) | Dozens of unrelated transfers just below the threshold into one hub, followed by a large wire or crypto purchase; the near-threshold count and the time to cash-out in the metrics |
| D | **Benign look-alike** (seeded: e.g. a payroll fan-out or a marketplace seller's fan-in) | The same graph shape, but red flags not fired because a payroll or vendor relationship explains it; verdict `clear`. This shows the agent isn't just matching shapes. With EX-7, shown side by side with scenario B |
| E | **Human-in-the-loop → precedent payoff** (seeded: Sophie Clarke) | The "needs your decision" alert (EX-4) for the £18,000 credit; the analyst clears with a note; the "saved to memory" card (EX-2.3); after Fast-forward, the similar credit is auto-cleared with a "Sentinel remembers" card (EX-2.1) |
| F | **Value and results** | The value ticker (EX-3) shows rules-only vs Sentinel alert counts climbing apart during the stream; the Results view (EX-13) shows the eval comparison with links to LangSmith |

## 6. Data the UI depends on

| Field | Needed for | Source |
|---|---|---|
| Sender / receiver account, bank, amount, currency, timestamp, payment format | Graph, metrics, timeline | Synthetic generator; IBM HI-Small sample |
| Account open date | "Newly opened account" flag | Synthetic generator |
| End-of-day balance (or computed running balance) | Pass-through flag, balance views | Computed from transactions |
| Device ID / IP | "Shared device/IP" flag | Synthetic generator (not in the IBM data → "No data") |
| KYC profile, PEP / sanctions | Account panel, hard flags | Synthetic KYC + `01_kyc_agent` lists |
| Precedents, decisions | Account panel, agent explanation | Agent long-term memory |
| Ground-truth labels | Not shown in the UI; eval only, plus "false positives avoided" in EX-3 | Generator / IBM `Is Laundering` |
| Live agent progress events (sub-agent started / finished, finding, verdict) | Agent activity panel (EX-1), memory cards (EX-2), alerts (EX-4) | Streamed from the agent backend |
| Rules-only verdict for every transaction | Value ticker (EX-3) | Rule scorer run alongside Sentinel |
| LLM call count and cost per call | Summary bar, value ticker | Agent backend / LangSmith |
| Assumed analyst minutes per alert | Analyst hours saved (EX-3) | Configuration value |
| Eval experiment results | Results view (EX-13) | Stored LangSmith experiments |
| Source links for each SAR statement | Linked citations (EX-6) | SAR writer structured output |
| Cached agent results | Replay mode (EX-8.6), cached answers (EX-10.4) | Recorded from a previous run |

## 7. Out of scope

- Non-functional requirements (performance, security, accessibility, technology choice): to be specified separately
- Visual design beyond the colour meanings in EX-9
- Real customer data
- Case assignment and multi-user workflow
- Notifications outside the app (email, SMS, mobile push); in-app alerts (EX-4) are in scope
- Editing transactions or KYC data from the UI
