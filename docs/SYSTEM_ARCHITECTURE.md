# SYSTEM ARCHITECTURE — Verified Source of Truth

**Account:** DUP447680 (IBKR paper trading) | **~$942k NAV** | **Port 4002 (IB Gateway paper API)**
**Last verified:** 2026-07-08 | **Python:** py -3.14 | **Working dir:** `C:\QuantTrading\TrendFollowing\`

---

## How to Use This Document

This is the single verified source of truth for how the trading system **actually works today** — not
how it was designed. Every factual claim is traced to a specific file and function. Where design intent
and actual live behavior differ, both are stated explicitly.

**Update this document with every architectural change.** The Phase B consistency check enforces that
it stays accurate. If a claim here conflicts with the code, the code wins; fix the doc and file a gap.

---

## 1. System Overview

### Intended layered architecture (the design)

```
[Signal Layer]         signal_engine.py / mean_reversion_strategy.py / vrp_strategy.py
       ↓
[Allocation Layer]     portfolio_risk.py (ERC weights + vol scalar)   ← INERT TODAY
       ↓
[Governance Layer]     governance_gates.py (VIX gate + 2-day confirmation)
       ↓
[Execution Layer]      order_engine.py → pending_orders.json → premarket_submit.bat
       ↓
[Monitoring Layer]     monitor.py / multi_strategy_monitor.py → dashboard_data.json
```

### Actual live architecture (what runs)

The allocation layer (ERC) has never been active. Governance feeds execution correctly.
The meta-allocator (propose → govern → attribute) exists but is dashboard-only and does
not affect orders. See Section 4 for the full design-vs-actual breakdown.

---

## 2. The Daily Routine — Step by Step

### Split pipeline timing (Task Scheduler)

| Time | Script | Role |
|------|--------|------|
| 4:15 PM ET Mon–Fri | `daily_routine_v2.bat` | Signal generation, governance, order staging |
| 7:00 AM ET next day | `premarket_submit.bat` | Submit staged orders to IBKR |
| 7:15 AM ET next day | `health_check.bat` | Pipeline health check + alert email |

### 4:15 PM pipeline (`daily_routine_v2.bat`)

**Step 0 — `preflight_check.py`**
Pings IB Gateway at port 4002. If connection fails, logs `[CRITICAL]` and `goto :end`,
halting the entire routine. No subsequent steps run. Routine depends on IB Gateway being
live before 4:15 PM.

**Step 1 — `data_feed.py`**
Fetches price data from IBKR API. Writes `data/prices.csv`. Marked `[WARN]` on error but
does NOT halt (downstream scripts fall back to the prior CSV). Status: functional when IB
Gateway is connected.

**Step 2 — `signal_engine.py`** ← cosmetic only; see note
Calls `generate_today_signal()` (`signal_engine.py:96`), which reads `data/prices.csv`,
computes Trend signals, and prints a human-readable summary to stdout (captured in
`routine.log`). **Writes no files.** The Trend signal used for live orders is NOT produced
here — `order_engine.py` calls `generate_today_signal()` independently at Step 7.
Step 2 exists solely for human-readable logging. Removing it would not affect orders.

**Step 2b — `trend_following_strategy.py`** ← additive, crash-safe (Phase C-3)
Runs `TrendFollowingStrategy.__main__`. Delegates to the same `generate_today_signal()`
as Step 2 and Step 7 — byte-identical signals. Writes:
- `logs/trend_state.jsonl` — daily sleeve state record (pnl from prior positions × prices.csv return)
- `logs/sleeve_forecasts.jsonl` — six-field forecast object (via `emit_forecast()`)
CARDINAL RULE respected: no `if errorlevel 1 goto :end` guard — a failure here logs a
warning and never halts the routine. The order path (Step 7) is unaffected.

**Step 3 — `mean_reversion_strategy.py`** (no flags)
Runs `MeanReversionStrategy.__main__`. Calls `calculate_signals()` (downloads 8mo prices
for 22 tickers via yfinance, computes 50-day z-scores, applies weekly rebalance on Fridays,
momentum filter on shorts). Writes:
- `logs/mean_reversion_positions.json` — {longs: [...], shorts: [...], date: ...}
- `logs/meanreversion_state.jsonl` — daily sleeve state record (pnl, positions, extra)
- `logs/sleeve_forecasts.jsonl` — six-field forecast object (via `emit_forecast()`)

**Step 4 — `vrp_strategy.py --signal`**
Runs `VRPStrategy.__main__`. Calls `calculate_signals()` (downloads VIX/VIX3M/SVXY from
yfinance, computes roll yield and entry condition). Writes:
- `logs/vrp_state.jsonl` — daily sleeve state record
- `logs/sleeve_forecasts.jsonl` — six-field forecast object (via `emit_forecast()`)

**Step 5 — `governance_gates.py`** ← critical path; halts on failure
Instantiates `GovernanceGates`, calls `evaluate()`. Fetches VIX + VIX3M from yfinance,
evaluates three gate conditions, applies two-day deactivation confirmation. Computes
per-sleeve actions from `SLEEVE_GATE_RESPONSES` table. Writes `logs/gate_state.jsonl`.
If `evaluate()` raises, the bat file exits (halt condition protects order path).

**Step 6 — `portfolio_risk.py`** ← OBSERVATION MODE (Phase C-1)
Runs `PortfolioRiskManager.__main__`. Loads sleeve return streams from
`meanreversion_state.jsonl` and `vrp_state.jsonl`, reads gate state, computes
true ERC weights via Riskfolio-Lib's risk-parity optimizer (MV, equal risk
budgets) — replacing the prior inverse-volatility approximation as of
2026-07-13, following a peer-review finding of up to 11.75pp divergence
from true ERC. **Computes and logs — does NOT size orders.**
`ERC_LIVE_SIZING = False` constant guards the observation/live boundary.
Writes `logs/portfolio_state.jsonl` — fields: `timestamp`, `portfolio_vol_ex_ante`,
`sleeve_weights`, `risk_contributions`, `insufficient_history`, `erc_live_sizing`.
ERC earns live sizing authority after observation logs prove stable/sane (Phase E).
See Section 4 for the design-vs-actual gap.

**Step 7 — `order_engine.py --signals-only`**
The core order-staging step. Does NOT submit to IBKR. Instead:
1. Calls `generate_today_signal()` directly (imported: `order_engine.py:12`) — re-runs the
   same Trend signal computation as Step 2, independently.
2. Calls `size_today_positions()` (`position_sizer.py:6`) — vol-target sizing for Trend.
3. Connects to IBKR (port 4002) to read live NAV and current positions.
4. Calls `compute_mr_order_list()` — reads `logs/mean_reversion_positions.json` +
   `logs/gate_state.jsonl`, computes MR share counts.
5. Calls `compute_vrp_order_list()` (Phase C-2) — reads `logs/gate_state.jsonl` (suspend
   check) + `logs/vrp_state.jsonl` (weight), fetches SVXY price via yfinance, computes
   delta vs current SVXY holding. Gate-first: suspend → no order; reduce_50pct → halved
   capital. Uses same `MIN_TRADE_USD = $100` threshold as Trend.
6. Writes `logs/pending_orders.json` — all staged orders for Trend, MR, and VRP sleeves.
   VRP orders tagged `"sleeve": "VRP"`.
`portfolio_state.jsonl` is NOT read by order_engine.py (ERC in observation mode).

**Step 8 — `monitor.py`**
Reads live NAV and positions from IBKR. Writes position/NAV data to log files read by
Step 9.

**Step 9 — `multi_strategy_monitor.py`**
Reads `logs/{sleeve}_state.jsonl` (Trend, MR, VRP), `logs/gate_state.jsonl`, and
`logs/portfolio_state.jsonl` (does not exist — silently omitted). Merges into
`C:\QuantTrading\quant-portfolio\data\dashboard_data.json`.

**Step 10 — `git push`**
Commits and pushes `dashboard_data.json`, `last_positions.json`, `live_performance.csv`
to GitHub, updating the live dashboard at `isaacnicas.github.io/quant-portfolio`.

### 7:00 AM pipeline (`premarket_submit.bat`)

Calls `submit_orders_premarket.py`, which reads `logs/pending_orders.json` and submits
orders to IBKR via ib_insync. Checks for `pipeline_alert.txt` and logs any rejections.
Order type: `MKT DAY` (executes at market open). This is where IBKR actually receives orders.

### 7:15 AM health check (`health_check.bat`)

Calls `pipeline_health_check.py`. Reads `routine.log` (checks for "Routine complete"),
`pending_orders.json` (checks signal_date freshness), `gate_state.jsonl`. Sends alert
email via `C:\QuantTrading\config\email_config.json` if anomalies detected.

---

## 3. Per-Sleeve Status Table

| | **Trend** | **MeanReversion** | **VRP** |
|---|---|---|---|
| **Invoked daily?** | YES — signal_engine.py (Step 2, cosmetic) + trend_following_strategy.py (Step 2b, state log) + order_engine.py (Step 7, live) | YES — mean_reversion_strategy.py (Step 3) | YES — vrp_strategy.py --signal (Step 4) |
| **Persists state?** | YES — trend_state.jsonl written by Step 2b (Phase C-3). pnl from prior positions × prices.csv return | YES — meanreversion_state.jsonl (pnl from prior positions × today return), mean_reversion_positions.json | YES — vrp_state.jsonl (pnl from prior signal × SVXY return on day 2+) |
| **Sized by?** | `size_today_positions()` in position_sizer.py: `weight = signal × (target_vol=15% / asset_ewm_vol)`, clipped by leverage_scalar, dead-band thresholds (equity 2%, lev_etfs 4%, macro 1%) | `MR_SLEEVE_FRACTION = 0.10` hardcoded in order_engine.py. `mr_capital = nav × 0.10`, split 50/50 long/short, equal-dollar per name. ERC weight of 30% never applied | `VRP_SLEEVE_FRACTION = 0.10` in `compute_vrp_order_list()`. Delta ordering vs current SVXY holding. Gate-first: suspend → no order; reduce_50pct → capital halved |
| **Has order path?** | YES — order_engine.py imports generate_today_signal() directly; staged in pending_orders.json as "trend" sleeve | YES — compute_mr_order_list() reads mean_reversion_positions.json; staged as "MeanReversion" sleeve | YES (Phase C-2) — compute_vrp_order_list() reads vrp_state.jsonl + gate_state.jsonl; SVXY delta staged as "VRP" sleeve |
| **Emits forecast interface?** | YES (Phase C-3) — TrendFollowingStrategy.__main__ runs as Step 2b; writes trend_state.jsonl + sleeve_forecasts.jsonl | YES — emit_forecast() called in Step 3 __main__; writes sleeve_forecasts.jsonl. NOT read by order_engine | YES — emit_forecast() called in Step 4 __main__; writes sleeve_forecasts.jsonl. NOT read by order_engine |
| **Live weight vs ERC design** | Varies by signal/vol (vol-target adaptive). No hardcoded fraction. ERC design: 60% | **10% actual / 30% ERC design** — intentional conservative prove-out (see Section 9) | **10% allocation, gated** — signal and order path live; orders staged when ungated |

---

## 4. Sizing & Allocation — Design vs Actual

### Designed behavior

`portfolio_risk.PortfolioRiskManager` was intended to run in Step 6 and:
1. Compute ERC weights: `weight_sleeve = target_sleeve_vol / realized_vol`, then normalize
   (VRP≈10%, MR≈30%, Trend≈60% at typical realized vols)
2. Compute a portfolio vol scalar: `min(target_portfolio_vol=11% / portfolio_vol, 2.0)`
3. Feed these weights + scalar to `order_engine.py` for final sizing
4. Write `logs/portfolio_state.jsonl` for monitoring

### Actual behavior

`portfolio_risk.py` has **no `__main__` block** (`portfolio_risk.py:396` is end of file;
no block follows `print_risk_report()`). Step 6 executes `py -3.14 portfolio_risk.py`,
which loads the module and exits. Nothing is computed. Nothing is written.

`order_engine.py` has no `import portfolio_risk` statement (verified: only imports at
lines 1–12 are asyncio, json, date, Path, pd, ib_insync, position_sizer, signal_engine).
It reads no ERC weight from any file.

**The ERC allocation layer has never been active in the live order path.**

### Actual per-sleeve sizing (the real code)

| Sleeve | Sizing mechanism | Key line |
|--------|-----------------|----------|
| Trend | `position_sizer.size_today_positions()`: vol-target per asset, leverage capped | `position_sizer.py:32` |
| MR | `mr_capital = nav * 0.10` — hardcoded fraction | `order_engine.py:173, 310` |
| VRP | `vrp_capital = nav * 0.10`; delta vs current SVXY; gate-first; reduce_50pct halves capital | `order_engine.py:compute_vrp_order_list` |

### The gap

This is Gap #1. The ERC layer was designed as the authoritative capital-allocation
mechanism. Currently, Trend is sized by a reasonable (though different) vol-target method,
MR is sized by a hardcoded fraction 3× smaller than ERC design, and VRP has no order path.
The fix — adding a `__main__` block to `portfolio_risk.py`, wiring its output to
`order_engine.py`, and replacing the hardcoded fractions — is a Phase A/B item. Per Section
9, ERC earns live sizing authority only after observation-mode validation.

---

## 5. Governance Layer

**Script:** `governance_gates.py` | **Step 5** | **Output:** `logs/gate_state.jsonl`

### Three VIX gate conditions (verified: `GovernanceGates.evaluate()`, lines 159–163)

| Gate | Condition | Trigger |
|------|-----------|---------|
| G1 Backwardation | `F1 / F2 ≥ 0.95` | VIX term structure approaching parity (contango collapsing) |
| G2 Level | `spot_VIX > vix_200dma` | VIX regime elevated above its own 200-day mean |
| G3 Shock | `VIX +25% in 3 trading days` | Acute volatility spike |

F1 proxy = `^VIX` (CBOE 30-day index); F2 proxy = `^VIX3M` (CBOE 3-month index).
Note from code: "When IBKR provides VX futures, replace with actual front two contracts."
Current proxies are cash VIX indices, not futures — term structure approximation only.

### Two-day deactivation confirmation (verified: `governance_gates.py:169–176`)

Gates **activate immediately** on any trigger. Gates **deactivate only after two consecutive
clear evaluations** (the `in_confirmation` flag holds the effective gate for one additional
day after raw conditions clear). This prevents whipsawing on brief VIX retreats.

### Per-sleeve responses (verified: `SLEEVE_GATE_RESPONSES`, `governance_gates.py:36–57`)

| Sleeve | G1 Backwardation | G2 Level | G3 Shock |
|--------|-----------------|----------|----------|
| VRP | suspend | suspend | suspend |
| MeanReversion | none | reduce_50pct | reduce_50pct |
| FactorTiming | none | none | reduce_25pct |
| EquityCarry | none | reduce_25pct | reduce_50pct |

Note: FactorTiming and EquityCarry appear in `SLEEVE_GATE_RESPONSES` but have no
corresponding strategy files — they are placeholders for future sleeves.

### What governance actually does vs. not

The gate action (`suspend`, `reduce_50pct`, `active`) is read by `order_engine.py` from
`gate_state.jsonl` for **MeanReversion** (lines 159–171, 298–314) and **VRP**
(`compute_vrp_order_list`, Phase C-2). For VRP, gate is checked first — `suspend` returns
immediately with no order; `reduce_50pct` halves `vrp_capital` before share computation.
Trend is unaffected by the gate in the order path (no Trend gate read in order_engine.py).

**Regime classifier** (`_classify_macro()`, `governance_gates.py:238`): Computes
`expansion` / `contraction` / `unknown` from ISM PMI, HY credit spread, yield curve (all
optional; passed as CLI args in the bat file or omitted → "unknown"). This field is stored
in `gate_state.jsonl` as `macro_regime` but is NOT used to size orders. Regime is
observational only; it has been shelved from sizing after two Gate-2 validation failures.

---

## 6. The Meta-Allocator (built, dashboard-only, not live)

### Components (all in working dir)

| File | Role | Writes |
|------|------|--------|
| `meta_allocator_v0.py` | `WeightProposer` — proposes sleeve tilts against ERC baseline | `logs/proposed_weights.jsonl` |
| `governance_gate_wiring.py` | `ProposalGate` — applies three-stage governance veto to proposals | `logs/gated_decisions.jsonl` |
| `attribution_logger.py` | `AttributionLogger` — per-sleeve attribution records + daily summary | `logs/attribution.jsonl` |
| `backtest_allocator_v0.py` | Causal allocator backtest vs ERC baseline | `logs/backtest_allocator_v0.jsonl` |

### Propose → govern → attribute loop

```
sleeve_forecasts.jsonl  →  WeightProposer.propose()     → proposed_weights.jsonl
                        →  ProposalGate.gate()           → gated_decisions.jsonl
                        →  AttributionLogger.log()       → attribution.jsonl
```

The proposer reads `logs/sleeve_forecasts.jsonl` (written by MR and VRP in Steps 3–4;
Trend only when `trend_following_strategy.py` is run manually). It tilts around an ERC
baseline (VRP=10%, MR=30%, Trend=60%), subject to:
- MAX_TILT = 0.25 (25% relative tilt cap per sleeve)
- DEADBAND = 0.02 (2pp inertia threshold — no tilt if within 2pp of baseline)

Governance stages (non-reorderable):
1. VIX gate → suspend → park at ERC baseline (no redistribution to active sleeves)
2. Vol-target clip → VOL_TARGET=11%; scale = min(1.0, 11%/book_vol)
3. Per-sleeve bounds → floor=0%, cap=70%

**None of these logs are read by `order_engine.py`.** Live orders are byte-identical
regardless of what the meta-allocator proposes.

### Dependency note

The meta-allocator tilts around an ERC baseline that does not yet run live. Until the ERC
layer (Section 4 gap) is active, the meta-allocator operates relative to a theoretical
baseline — its proposals cannot be executed even if the live-authority gate were cleared.
**ERC activation is a prerequisite for the allocator going live.**

### Backtest status

`backtest_allocator_v0.py` ran on 2026-06-29 with synthetic MR peer (no real MR/VRP state
logs existed). Result: INDICATIVE only (n < 30 trading days of real data). Gate formally
clears only when Series C (dynamic net-of-costs) Sharpe > Series A (ERC) Sharpe on real,
non-synthetic data with n ≥ 63 records.

---

## 7. Gap Register

| # | Component | Status |
|---|-----------|--------|
| 1 | **ERC layer** (`portfolio_risk.py`) | **OBSERVATION MODE** (Phase C-1): `__main__` added; Step 6 writes `portfolio_state.jsonl`. `ERC_LIVE_SIZING = False` — weights computed and logged, not used for sizing. Earns live authority in Phase E |
| 2 | **VRP order path** | **RESOLVED (Phase C-2)**: `compute_vrp_order_list()` + `submit_vrp_orders()` in `order_engine.py`. SVXY delta staged as "VRP" sleeve. Gate-first: suspend -> no order; reduce_50pct -> halved capital |
| 3 | **Trend forecast interface** | **RESOLVED (Phase C-3)**: Step 2b in `daily_routine_v2.bat` runs `trend_following_strategy.py` daily. Writes `trend_state.jsonl` + `sleeve_forecasts.jsonl`. Signal byte-identical to Step 7 |
| 4 | **`portfolio_state.jsonl`** | **PARTIALLY RESOLVED (Phase C-1)**: file written by Step 6. Fields: `timestamp`, `portfolio_vol_ex_ante`, `sleeve_weights`, `risk_contributions`, `insufficient_history`, `erc_live_sizing`. Not read by `order_engine.py` (observation mode) |
| 5 | **MR sleeve fraction in wrong layer** | **OPEN**: MR sizing (10%) hardcoded in `order_engine.py`. Resolves when ERC earns live authority (Phase E) |
| 6 | **PIT date-guard in `_load_recent_state()`** | **RESOLVED (Phase C-4)**: `date < today` filter added structurally to `_load_recent_state()` and cross-sleeve reads in `_compute_correlation_to_portfolio()`. Correct regardless of call order |
| 7 | **FactorTiming / EquityCarry placeholders** | **OPEN**: Listed in `SLEEVE_GATE_RESPONSES` but no strategy files. Future phases |
| 8 | **VIX futures proxies** | **OPEN**: Gate uses cash VIX indices (^VIX, ^VIX3M). Replace with VX futures when IBKR access available |
| 9 | **Step 2 signal redundancy** | **OPEN**: `signal_engine.py` (Step 2) writes no output; Step 7 re-computes identical signal. Cosmetic only; low priority |

---

## 8. Autonomy Governance Framework

The system is NOT autonomous today. This section defines the evidence-based conditions
that must be met before each stage of autonomy is granted. Conditions are defined now,
before the evidence exists, so they cannot be back-filled to fit outcomes.

### Stage 0 — Current state (Architecture Unverified)
Architecture documented and verified (this document). Key components are inert or missing
(Gaps 1–6 above). All orders reviewed manually. The system stages orders and a human
submits them.

**Exit condition to consider Stage 1:** All gaps in Section 7 fixed and documented here.
Phase B consistency check running clean (no gap between doc and code). No silent failures
in routine.log for ≥ 10 consecutive trading days.

### Stage 1 — Verified & Instrumented (No Autonomy Yet)
All designed components are wired and producing output:
- ERC running in **observation mode** (computes and logs weights; does NOT yet size orders)
- VRP order path built and tested
- Trend state log running (trend_state.jsonl populated daily)
- Meta-allocator proposer running against real sleeve forecasts (not synthetic)
- Consistency check (Phase B) running and passing daily
- MR sleeve running at 10% (prove-out allocation), ERC logging what it would allocate

**Exit condition to consider Stage 2:** ≥ 10 weeks Stage-1 clean (Phase B green, zero
silent gaps) AND meta-allocator real-data backtest (n ≥ 63) passes: Series C Sharpe >
Series A Sharpe. ERC observation logs show ≥ 63 records of computed weights.

### Stage 2 — Supervised Autonomy
System rebalances and executes autonomously. Human reviews daily dashboard. Intervention
is possible and expected. ERC earns live sizing authority: `order_engine.py` reads ERC
weights from `portfolio_risk.py` output (Trend and MR sized by ERC, not hardcoded fractions).

**Exit condition to consider Stage 3:** ≥ [N weeks to fill in once Stage 1 accumulation
rate is known] Stage-2 with no human intervention required AND live P&L tracking within
[±1 Sharpe unit] of meta-allocator backtest projection.

### Stage 3 — Full Autonomy
System runs autonomously with weekly human review. Emergency halt mechanism available.
Incident response procedures defined before entering this stage.

**ERC earns live authority the same way:** observation mode → criteria met → live.
No component goes live-and-sizing without passing a defined evidence bar first.

---

## 9. Key Decisions Locked

These decisions have been made. They are documented here for reference, not for
re-litigation. Future changes must clear a higher bar than re-litigating these.

| Decision | What was decided | Why |
|----------|-----------------|-----|
| **MR at 10%** | MR runs at 10% of NAV (hardcoded), not 30% ERC design | Intentional conservative prove-out. OOS Sharpe is ~0.24 — not yet earned full ERC weight. Revisit after N weeks of live track record at actual ERC weight | 
| **ERC = observation first** | ERC runs in observation mode before earning live sizing authority | Cannot trust a sizing mechanism whose output has never been validated against live execution. Earns authority against defined criteria (Stage 1 → 2 exit conditions above) |
| **Backtest fidelity = match live weights** | Backtests run at actual live weights (10% for MR), not design weights | Apples-to-apples comparison. Running a 30%-MR backtest and comparing to 10%-MR live is not informative. Adjust backtest weights when live weights change |
| **Regime engine = observational only** | Regime classifier (macro + VIX regime) logged but NOT used to size orders | Two Gate-2 validation failures. Regime data stored in gate_state.jsonl as `macro_regime` field. Available for future re-validation if conditions change |
| **Meta-allocator = performance-conditioned** | Meta-allocator is dashboard-only; does not affect orders until validated | Requires real sleeve P&L data (n ≥ 63 records) and ERC active before it can meaningfully propose. Backtest with n < 30 and synthetic MR peer is INDICATIVE only |
| **VRP order path = Phase C** | VRP SVXY orders to be built in Phase C | VRP has been continuously gated since at least 2026-06-24. Build the order path when gate begins to clear and there is something to execute |

---

## Appendix: Key File Map

| File | Purpose | Reads | Writes |
|------|---------|-------|--------|
| `signal_engine.py` | Trend signal computation | `data/prices.csv` | stdout (cosmetic) |
| `position_sizer.py` | Trend position sizing | signal_engine output (in-memory) | — |
| `mean_reversion_strategy.py` | MR signals + state log | yfinance, `mean_reversion_positions.json` | `mean_reversion_positions.json`, `meanreversion_state.jsonl`, `sleeve_forecasts.jsonl` |
| `vrp_strategy.py` | VRP signals + state log | yfinance | `vrp_state.jsonl`, `sleeve_forecasts.jsonl` |
| `trend_following_strategy.py` | Trend class wrapper (NOT in routine) | `data/prices.csv` (via signal_engine) | `trend_state.jsonl` (when run manually), `sleeve_forecasts.jsonl` |
| `governance_gates.py` | VIX gate evaluation | yfinance (^VIX, ^VIX3M) | `gate_state.jsonl` |
| `portfolio_risk.py` | ERC weights + vol scalar (INERT — no `__main__`) | — | — (nothing written) |
| `order_engine.py` | Order staging + (live mode) submission | `signal_engine` (import), `mean_reversion_positions.json`, `gate_state.jsonl` | `pending_orders.json`, `pipeline_alert.txt` |
| `strategy_base.py` | Base class: `log_daily_state()` method | — | `{sleeve}_state.jsonl` (when called) |
| `sleeve_forecast_mixin.py` | 6-field forecast interface + `emit_forecast()` | `{sleeve}_state.jsonl` | `sleeve_forecasts.jsonl` |
| `meta_allocator_v0.py` | Weight proposer (dashboard-only) | `sleeve_forecasts.jsonl`, `gate_state.jsonl` | `proposed_weights.jsonl` |
| `governance_gate_wiring.py` | Proposal gate (dashboard-only) | `proposed_weights.jsonl`, `gate_state.jsonl` | `gated_decisions.jsonl` |
| `attribution_logger.py` | Position attribution (dashboard-only) | gated_decisions, proposals, forecasts | `attribution.jsonl` |
| `monitor.py` | NAV + position tracking | IBKR API | position/NAV logs |
| `multi_strategy_monitor.py` | Dashboard aggregator | `{sleeve}_state.jsonl`, `gate_state.jsonl`, `portfolio_state.jsonl` (absent) | `dashboard_data.json` |
| `pipeline_health_check.py` | Daily health check + email alert | `routine.log`, `pending_orders.json`, `gate_state.jsonl` | alert email |
| `data_feed.py` | Price data fetch | IBKR API | `data/prices.csv` |
| `preflight_check.py` | IB Gateway connection check | port 4002 | — |

---

*Document created 2026-07-05. Update with every architectural change. The code is authoritative; this document is the human-readable verified trace.*
