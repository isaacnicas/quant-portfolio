# Quant Portfolio — Systematic Multi-Strategy Trading System

Live paper-trading system anchored by a monthly-rebalancing trend-following
ETF strategy, extended into a multi-strategy book with shared governance and
risk infrastructure. Paper account: DUP447680 (IBKR).

Live dashboard: https://isaacnicas.github.io/quant-portfolio/live-dashboard.html

## Strategies

| Sleeve | Status | Signal | Notes |
|---|---|---|---|
| Trend-following (anchor) | LIVE | TSMOM + CS-Mom, regime filter, fast-exit | Monthly rebalance; ETF universe |
| Mean-reversion | LIVE | 50-day z-score, ±1.5 dead-band | Asymmetric momentum filter, 2-per-sector cap |
| VRP (VIX contango) | GATED OUT | SVXY carry, ^VIX/^VIX3M | Currently disabled by governance gate |
| PEAD | BUILT, ORDERS PAUSED | Cross-sectional cohort SUE ranking | Awaiting qualifying 5+ stock cohort (mid-July Q2 season) |

## Architecture

- `data_feed.py` — IBKR daily bars (3yr history), port 4002
- `signal_engine.py` / strategy modules — signal generation
- `mean_reversion_strategy.py` — MR sleeve
- `vrp_strategy.py` — SVXY-based VRP sleeve
- `governance_gates.py` — VIX risk governor (3-condition gate, 2-day deactivation confirm)
- `portfolio_risk.py` — ERC weighting, 11% vol target
- `order_engine.py` — order submission (MKT+OPG), port 4002
- `monitor.py` — NAV/position read + dashboard JSON, port 4002
- `multi_strategy_monitor.py` — daily blended report

## Execution pipeline

Two-stage split to satisfy order-type timing constraints:

- **4:15 PM ET** — `daily_routine_v2.bat`: data feed → signals (all sleeves)
  → governance → ERC risk → orders staged to `pending_orders.json` → monitor
  → dashboard push.
- **7:00 AM ET** — `premarket_submit.bat`: submits staged orders as MKT+OPG
  (open auction). Health-check email at 7:15 AM.

Automated via Windows Task Scheduler (weekday triggers, AC-power only,
30-min limit, no concurrent instances).

## Trend-Following — change log (through 2026-06-26)

- Migrated all scripts from `OneDrive\Desktop\TrendFollowing` to
  `C:\QuantTrading\TrendFollowing\` to eliminate file-lock race conditions.
- Order execution switched from `MKT/DAY` to `MKT+OPG`. MOO was rejected by
  paper gateway (Error 321: requires submission before 3:58 PM, incompatible
  with the 4:15 PM pipeline).
- Pipeline split into 4:15 PM signal generation and 7:00 AM submission.
- Fixed Task Scheduler trigger (was firing at midnight with TWS closed → all
  orders rejected nightly). Recreated `MultiStrategy_DailyRoutine` weekday
  4:15 PM.
- Python 3.14.6 via `py -3.14`; asyncio patch required at top of every script
  for ib_insync 0.9.86 compatibility.

## Operational — IB Gateway migration (2026-06-26)

- Migrated from TWS (port 7497) to IB Gateway (port 4002) for headless
  operation. IBC 3.24.0 (IbcAlpha) handles auto-login to paper account
  DUP447680.
- Port updated in `data_feed.py`, `order_engine.py`, and `monitor.py`
  (7497 → 4002; old TWS line kept commented as fallback).
- Headless launch via `C:\IBC\StartGateway.bat` (IBC config at
  `C:\IBC\config.ini`, outside the repo; credentials gitignored).
- TWS retained as manual fallback until Gateway proves stable over several
  cycles.
- Full pipeline dry-run passed end-to-end through Gateway: data feed → signals
  (trend/MR/VRP/PEAD) → governance → ERC risk (gross 134.97%) → 15 orders
  staged → monitor → dashboard push.

## Known issues

- IBKR subscription Error 10089 → live prices read from local `prices.csv`.
- `StartGateway.bat` not yet wired into Task Scheduler — Gateway must be
  launched and logged in before the 7:00 AM submit job (see roadmap).

## Roadmap

- Wire `StartGateway.bat` into Task Scheduler ahead of 7:00 AM submit.
- Mean-reversion universe expansion to S&P 400 MidCap (target Jul 10).
- PEAD order activation pending qualifying cohort (mid-July Q2 earnings).

## Disclaimer

Paper trading and research only. Not investment advice.
