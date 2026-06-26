# Changelog

All notable changes to this project are documented here.
Newest entries first. Dates in ISO format (YYYY-MM-DD).

This project began as a single trend-following ETF strategy (see [README.md](README.md))
and is evolving into a multi-strategy systematic book. This file tracks that evolution.

---

## [2026-06-26] — IB Gateway migration

### Changed
- Migrated execution from TWS (port 7497) to IB Gateway (port 4002) for
  headless, unattended operation. IBC 3.24.0 (IbcAlpha) handles auto-login
  to paper account DUP447680.
- Updated the connection port in `data_feed.py`, `order_engine.py`, and
  `monitor.py` (old TWS line kept commented as a fallback).

### Added
- Headless launch via `C:\IBC\StartGateway.bat`. IBC config kept outside the
  repo, with credentials gitignored.
- Full pipeline dry-run passed end-to-end through Gateway: data feed → signals
  (trend / mean-reversion / VRP / PEAD) → governance → ERC risk
  (gross exposure 134.97%) → 15 orders staged → monitor → dashboard push.

### Known gaps
- `StartGateway.bat` not yet wired into Task Scheduler ahead of the 7:00 AM
  submit job. Until scheduled, Gateway must be launched manually before market
  open.

---

## [2026-06-24] — Multi-strategy split architecture

### Added
- **Mean-reversion sleeve** went live: 50-day z-score, ±1.5 dead-band,
  asymmetric momentum filter (excludes top-quartile momentum names from the
  short book), 2-position-per-sector cap.
- **VRP sleeve** built (SVXY-based volatility-premium carry via ^VIX/^VIX3M) —
  currently gated out by governance.
- **PEAD sleeve** built (post-earnings-announcement drift, cross-sectional
  cohort SUE ranking) — orders paused pending a qualifying 5+ stock cohort.
- Shared **governance gate** (three-condition VIX risk governor with two-day
  deactivation confirmation) and **ERC portfolio risk** layer (equal risk
  contribution weighting, 11% vol target).

### Changed
- Split the pipeline into two stages to satisfy order-type timing constraints:
  4:15 PM signal generation (`daily_routine_v2.bat`) and 7:00 AM submission
  (`premarket_submit.bat`).
- Order type changed from MKT/DAY to MKT+OPG (open auction). MOO was rejected
  by the paper gateway (Error 321: requires submission before 3:58 PM,
  incompatible with the 4:15 PM pipeline).
- Migrated all scripts from `OneDrive\Desktop\TrendFollowing` to
  `C:\QuantTrading\TrendFollowing\` to eliminate file-lock race conditions.

---

## [2026-06-18] — Paper trading live

### Added
- Trend-following anchor strategy entered its first positions on IBKR paper
  account DUP447680 (IWM, EEM, SMH, XLK, QQQ, SPY, EWJ).
- Daily monitoring and monthly rebalancing automated via Windows Task Scheduler.
- Live dashboard deployed to GitHub Pages
  (`isaacnicas.github.io/quant-portfolio/live-dashboard.html`), fed by a daily
  JSON push.

---

## [earlier] — Backtest and research

### Added
- Eighteen-year backtest (2008–2026) of the trend-following ETF strategy across
  US/international equities, government bonds, gold, and currencies, with
  realistic trading costs.
- TSMOM + CS-Mom signal blend, regime filter, and fast-exit logic.

### Fixed
- **Over-layered safeguards** bug: three independent risk overlays multiplied
  together, leaving the strategy ~30% invested on ordinary days and returning
  ~2%/yr. Simplified to one clear rule → over 13%/yr without materially more
  risk.
- **Fast-exit calendar lock**: the circuit breaker stayed defensive until the
  next monthly check-in, missing short-selloff recoveries. Reworked to listen
  for recovery daily so it can re-engage as soon as the data supports it.
