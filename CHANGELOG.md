# Changelog

All notable changes to this project are documented here.
Newest entries first. Dates in ISO format (YYYY-MM-DD).

This project began as a single trend-following ETF strategy (see [README.md](README.md))
and is evolving into a multi-strategy systematic book. This file tracks that evolution.

---

## [2026-06-26] — Research documentation + VRP gate validation

### Added
- `RESEARCH.md` — full methodology, backtest process, results, and rationale
  for each strategy addition, with honest markers where figures are not yet
  measured.
- `OPERATIONS.md`, `CHANGELOG.md`, and a reframed `README.md` introduction
  linking the four-document set (narrative / operations / research / history).
- VRP gate-validation backtest (2015-01-01 → 2026-06-26) run and saved to
  `vrp_backtest_results.txt`. Both required gate-fires confirmed (Feb 2018,
  Mar 2020 = True). Sleeve standalone: CAGR 7.5%, Sharpe 0.39, max drawdown
  −65.4% (≈ −6.5% at a 10% portfolio cap).

### Findings
- VRP gate is a regime *detector*, not a gap-loss preventer: on 2018-02-05 the
  exit fired on the close after SVXY had already gapped ~80% at the open. The
  sleeve's survivability rests on the 10–15% position cap, not the gate.
  Documented in `RESEARCH.md`.
- Confirmed VRP futures-curve proxy is the CBOE `^VIX/^VIX3M` indices (not
  VIXY/VIXM); the reverse-split issue does not apply.
- Mean-reversion diversification case confirmed: anchor + MR blended under ERC
  weighting (≈67% MR / 33% anchor) gives max drawdown −17.73%, **9.23pp
  shallower** than the anchor's −26.96%, with blended Sharpe 0.95 vs anchor 1.07.
  Worst residual drawdown narrows to the COVID window (2020-02-19 → 2020-03-23).
  Saved to `blended_backtest_results.txt`.
- PEAD lookahead-bias check came back clean after fixing a quarter-matching flaw
  in the verification script: the earlier DIVERGED (17% on MKC) was a
  different-quarter artifact, not a data revision. Matched-quarter comparison
  shows 0.00% divergence — yfinance serves point-in-time estimates. Verdict rests
  on one stock so far; to be re-confirmed as the earnings DB fills through Q2.
  Saved to `pit_verification_results.txt`.
- PEAD aggregate stats measured (2025-06-02 → 2026-06-01, cohort-ranking version):
  24 trades, 62.5% hit rate, +1.23% avg/trade, Sharpe 0.59, max drawdown −16.3%.
  Sample is small (~4 quarters) — indicative, not validated; re-run after Q2 2026.
  The file's 28.8% CAGR is a sequential-compounding artifact and is not quoted.
  Earlier seasonal-SUE version not reproducible (replaced in place, no history).
  Saved to `pead_aggregate_stats.txt`.

### Deployment / sample-growth items (not open research)
- PEAD: re-verify PIT and re-run stats after Q2 2026 earnings adds ~5–6 events.
- VRP: portfolio-level position-cap enforcement required before any allocation.

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
