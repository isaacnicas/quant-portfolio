# Operations — System Architecture & Live Pipeline

Current technical state of the running system. This document reflects the
present architecture and is kept current; for the history of how it got here,
see [CHANGELOG.md](CHANGELOG.md). For the project narrative and backtest, see
[README.md](README.md). For the backtest process and rationale behind each
sleeve, see [RESEARCH.md](RESEARCH.md).

Paper account: **DUP447680** (IBKR).
Live dashboard: https://isaacnicas.github.io/quant-portfolio/live-dashboard.html

---

## Strategies

| Sleeve | Status | Signal | Notes |
|---|---|---|---|
| Trend-following (anchor) | LIVE | TSMOM + CS-Mom, regime filter, fast-exit | Monthly rebalance; ETF universe |
| Mean-reversion | LIVE | 50-day z-score, ±1.5 dead-band | Asymmetric momentum filter, 2-per-sector cap |
| VRP (VIX contango) | GATED OUT | SVXY carry, ^VIX/^VIX3M | Currently disabled by governance gate |
| PEAD | BUILT, ORDERS PAUSED | Cross-sectional cohort SUE ranking | Awaiting qualifying 5+ stock cohort (mid-July Q2 season) |
| FactorTiming | PLANNED (Phase 1B) | — | Pre-registered in governance; no strategy file yet. Dashboard shows "Planned". |
| EquityCarry | PLANNED (Phase 2) | — | Pre-registered in governance; no strategy file yet. Dashboard shows "Planned". |

---

## Architecture

- `data_feed.py` — IBKR daily bars (3yr history), port 4002
- `signal_engine.py` — trend signals (TSMOM, CS-Mom, regime filter, fast-exit)
- `mean_reversion_strategy.py` — mean-reversion sleeve
- `vrp_strategy.py` — SVXY-based VRP sleeve
- `governance_gates.py` — VIX risk governor (3-condition gate, 2-day deactivation confirm)
- `portfolio_risk.py` — ERC weighting, 11% vol target
- `order_engine.py` — order submission (MKT+OPG), port 4002
- `monitor.py` — NAV/position read + dashboard JSON, port 4002
- `multi_strategy_monitor.py` — daily blended report

---

## Execution pipeline

Two-stage split to satisfy order-type timing constraints:

- **4:15 PM ET — `daily_routine_v2.bat`:** data feed → signals (all sleeves) →
  governance → ERC risk → orders staged to `pending_orders.json` → monitor →
  dashboard push.
- **7:00 AM ET — `premarket_submit.bat`:** submits staged orders as MKT+OPG
  (open auction). Health-check email at 7:15 AM.

Automated via Windows Task Scheduler (weekday triggers, AC-power only, 30-min
limit, no concurrent instances).

---

## Interactive Brokers connection

- Runs headless on **IB Gateway**, port **4002** (paper). Live port is 4001.
- **IBC 3.24.0** (IbcAlpha) handles auto-login. Headless launch via
  `C:\IBC\StartGateway.bat`; IBC config at `C:\IBC\config.ini`
  (`TradingMode=paper`, `ReadOnlyApi=no`).
- IBC config lives **outside the repo**; credentials are gitignored and must
  never be committed.
- TWS (port 7497) retained as a manual fallback until Gateway proves stable
  over several cycles. The old port line is kept commented in each script.

---

## Environment

- Python 3.14.6 via the `py -3.14` launcher (not bare `python` / `pip`).
- `ib_insync` 0.9.86 — requires an asyncio patch at the top of every script
  for Python 3.14 compatibility.
- All scripts at `C:\QuantTrading\TrendFollowing\`.

---

## Known issues

- IBKR subscription **Error 10089** → live prices read from local `prices.csv`
  rather than requested via API for order sizing.
- **`StartGateway.bat` not yet wired into Task Scheduler** — Gateway must be
  launched and logged into paper before the 7:00 AM submit job. Until scheduled,
  the Gateway path is not fully autonomous.

---

## Roadmap

- Wire `StartGateway.bat` into Task Scheduler ahead of the 7:00 AM submit job.
- Mean-reversion universe expansion to S&P 400 MidCap (target ~Jul 10):
  avg daily volume > $5M, no earnings within 5 trading days, target 80–120 names.
- PEAD order activation pending a qualifying cohort (mid-July Q2 earnings).
- Factor-timing and equity-carry sleeves (later phases).

---

*Paper trading and research only. Not investment advice.*
