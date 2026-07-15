# Factor Timing / Equity Carry Schedule Review
Date: 2026-07-15
Scope: read-only fact-finding. No recommendation on whether to keep, move, or cancel either date — that decision is for a separate conversation.

## Correction to the task's premise: the reminders were not created around 2026-07-05

The task assumed these Task Scheduler reminders were "set up around 2026-07-05 (the session that produced the six-counsel roadmap...)". Checked directly against the filesystem, not assumed: every reminder task's XML file in `C:\Windows\System32\Tasks\` — including `Reminder_Factor_Timing` and `Reminder_Equity_Carry` — has **CreationTime = LastWriteTime = 2026-06-25 00:12:0x**, ten days before the date the task described. All reminder tasks (Factor Timing, Equity Carry, VRP Review, Phase1 Review, PEAD Build/Review, ML Meta Design, Cross-Asset Research, Earnings Revisions, Universe Expansion, IB Gateway) were created in the same single batch, that same second-level timestamp, and **none have been modified since** (CreationTime exactly equals LastWriteTime for all of them). Whatever session actually produced these had to be on or before 2026-06-25, not 2026-07-05. No document search below found a surviving "six-counsel roadmap" file by that name; see the next section for what was actually found.

## Step 1 — Original stated rationale

**No surviving document contains the literal phrase "PHASE 1B — After VRP stabilizes (60-90 days)"** or anything matching it word-for-word. This was searched for directly, not assumed absent: `git log --all -S"60-90"`, `-S"Phase 1B"`, `-S"stabilizes"`, `-S"August 18"`, `-S"October 6"` across the full history of `quant-portfolio`; equivalent text search across all `.md`/`.txt` files currently on disk in `TrendFollowing` (which has no git history at all); and a check of `C:\QuantTrading\reminders\` (only contains the generic `show_reminder.ps1` popup script, no per-task planning notes). The task's own framing of the original rationale could not be verified against any surviving primary source. This is reported plainly rather than treating the task's paraphrase as confirmed fact.

**What does survive, and is the most authoritative evidence available**, is each reminder task's own embedded action message (extracted directly from the Task Scheduler XML, not the tracker's summary of it):

> **Reminder_Factor_Timing** (trigger: 2026-08-18T09:00:00-04:00):
> "ACTION: Build factor timing sleeve. FRED API for ISM PMI. Rotate between MTUM/VLUE (expansion) and QUAL/USMV (contraction). Monthly rebalance. Always-invested long-only. If OOS Sharpe below 0.15 incremental, size at minimum 10% risk budget only."

> **Reminder_Equity_Carry** (trigger: 2026-10-06T09:00:00-04:00):
> "ACTION (conditional on Phase 1 review pass): Build equity dividend carry sleeve. Instruments: DVY, VYM vs broad index. Monthly rebalance. Low turnover. Target 5-10% risk budget. Income and smoothing sleeve for flat, low-trend environments."

Two related reminders, same batch, give context for the sequencing:

> **Reminder_Phase1_Review** (2026-09-08): "REVIEW: Full Phase 1 review. 10 weeks of live data. Check: sleeve correlations, blended drawdown vs trend anchor alone, any sleeve below success metric thresholds. Make sizing decisions based on live behavior. Prepare Phase 2 go/no-go decision."

> **Reminder_VRP_Review** (2026-09-15): "REVIEW: VRP active trading checkpoint. Count active (non-gated) trading days. If fewer than 15 active days, extend review by 2 weeks. Check gate behavior log at ...\\gate_state.jsonl"

**Reconstructed logic (inferred from the evidence above, not a confirmed quote):**
- **Equity Carry (Oct 6) is explicitly conditional** — its own message says "conditional on Phase 1 review pass" — and its date sits 28 days after the Phase 1 Review checkpoint (Sept 8) and 21 days after the VRP Review checkpoint (Sept 15). This reads as a deliberate buffer after both review gates, not an arbitrary date.
- **Factor Timing (Aug 18) is NOT conditional** — its message has no "pending review" language, and its date (54 days after the 2026-06-25 batch-creation date) falls *before* both the Phase 1 Review (Sept 8) and VRP Review (Sept 15). It is not gated on VRP's live performance at all; it reads as an independently-scheduled build/research task, most plausibly timed around the infrastructure work it names (FRED API integration), not around VRP's stabilization.
- One numerical alignment worth flagging as an observation, not a confirmed fact: VRP's governance gate cleared and its sleeve action became continuously "active" starting **2026-07-08** (see Step 3). **2026-10-06 is exactly 90 days after 2026-07-08.** This is consistent with a "90 days after VRP becomes active" rule, but no source document confirms this was the actual intended derivation — it may equally be coincidental, since the reminder was created on 2026-06-25, before VRP's gate had cleared at all.

## Step 2 — Current Task Scheduler state

Both tasks confirmed live via `Get-ScheduledTask`:

| Task | State | Trigger | Modified since creation? |
|---|---|---|---|
| Reminder_Factor_Timing | Ready (Enabled=True) | 2026-08-18 09:00 | No — CreationTime = LastWriteTime |
| Reminder_Equity_Carry | Ready (Enabled=True) | 2026-10-06 09:00 | No — CreationTime = LastWriteTime |

Neither has been removed, disabled, or edited since creation on 2026-06-25. Both are still scheduled to fire as originally set.

## Step 3 — Has the underlying dependency actually cleared?

**Equity Carry's dependency is explicitly time/review-based ("conditional on Phase 1 review pass") — not yet cleared, and cannot be, since the review itself hasn't happened.** Today is 2026-07-15; the Phase 1 Review (Sept 8) and VRP Review (Sept 15) that Equity Carry is conditioned on are both still in the future. There is nothing to evaluate yet.

**On the closest thing to a time-based check available — how long VRP has actually been running "stabilized"** — checked directly against `logs/gate_state.jsonl` and `logs/vrp_state.jsonl`:
- VRP's governance gate was **actively suspending it** (`"VRP": "suspend"`) continuously from at least 2026-06-24 through 2026-07-07 — i.e., VRP was gated near-zero at exactly the time these reminders were created (2026-06-25), confirming the task's hint was accurate for that period.
- The gate cleared and VRP's sleeve action became `"active"` starting **2026-07-08**, and has remained active on every subsequent recorded day through 2026-07-15 (the latest record).
- `vrp_state.jsonl` shows VRP has only **9 total daily records**, starting 2026-07-06, with real trading activity (`capital_alloc=0.1`, live P&L) only from 2026-07-08 onward — **8 trading days of continuously active, non-gated live history as of today.**
- By the "count active (non-gated) trading days" test the reminders' own VRP Review task specifies (≥15 active days before proceeding, else extend 2 weeks), VRP is **currently at roughly half that threshold**, with the review checkpoint itself still 8+ weeks away (Sept 15). Whether or not the specific "60-90 days" framing the task described was ever the literal original rule, VRP has nowhere near that much live history under any interpretation — 8 active days, not 60-90.

**Factor Timing's dependency is infrastructure-based (FRED API for ISM PMI) — checked directly, and it is NOT resolved.** `governance_gates.py` already contains a `_classify_macro()` function that computes an expansion/contraction/unknown regime from `ism_pmi`, `credit_spread`, and `yield_curve` — but these are plain optional function parameters (`= None` defaults) with **no FRED API call, and no other live data source, anywhere in the codebase.** The CLI entry point (`--ism`, `--credit`, `--yc`) requires these to be supplied manually; the live daily routine (`daily_routine_v2.bat` line 66) invokes `governance_gates.py` with **no arguments at all** — only a comment on line 64 ("Example with macro data: --ism 52.1 --credit 320 --yc 0.45") showing the option exists, never exercised. Confirmed empirically: every single record in `gate_state.jsonl`, from 2026-06-24 through the most recent (2026-07-15), shows `"ism_pmi": null, "credit_spread": null, "yield_curve": null, "macro_regime": "unknown"`. `docs/SYSTEM_ARCHITECTURE.md` independently confirms this is a deliberate, known state: "Regime is observational only; it has been shelved from sizing after two Gate-2 validation failures." **The FRED API integration the Factor Timing reminder names as its first action item does not exist in any form — not broken, not partial, simply never built.**

## Summary

| | Original rationale (as found) | Current TS state | Dependency status |
|---|---|---|---|
| Factor Timing (Aug 18) | Unconditional build task; names FRED API/ISM PMI as first step. No "conditional on X" language, unlike Equity Carry. Predates both Phase 1 and VRP review checkpoints. | Enabled, unmodified since 2026-06-25 | Infrastructure dependency (FRED API for ISM PMI) confirmed **not resolved** — no live data source exists anywhere in the codebase; the relevant classifier has never received real input in production. |
| Equity Carry (Oct 6) | Explicitly "conditional on Phase 1 review pass"; dated ~3-4 weeks after the Phase 1 (Sept 8) and VRP (Sept 15) review checkpoints. | Enabled, unmodified since 2026-06-25 | Review-based dependency **not yet evaluable** — the gating review itself is still in the future. On the closest measurable proxy (VRP's own active-trading tenure), VRP has 8 active days as of today, far short of any 60-90-day framing, whether or not that specific framing was ever the documented rule. |

No document survives that states the original date-derivation logic in its own words for either reminder. The evidence above is a reconstruction from the reminders' own embedded messages, their creation timestamp, and current system state — reported as such, not as a confirmed original rationale.
