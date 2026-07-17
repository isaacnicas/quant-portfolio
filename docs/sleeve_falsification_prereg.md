# Sleeve Falsification Test — Pre-Registration (Trend, MeanReversion)

**Status at time of writing this file: no DSR/PBO numbers have been computed yet.** This is written before any result is seen, per the decision rule below being fixed in advance.

## Scope change from original request

The original task specified two tests: (A) DSR/PBO survival, (B) live drawdown vs. a stationary block bootstrap of each sleeve's own backtest history, reusing "the stationary block bootstrap already built and validated for the PEAD long-leg work."

That bootstrap does not exist. Checked directly: `quant_lab/docs/pead_longleg_bootstrap_ci.md` (commit `b52f980`, 2026-07-15) states explicitly that the PEAD long-leg bootstrap was **never run** — the exercise stopped before Step 2 (the bootstrap) because the reconstructed return series didn't reproduce the reported Sharpe. No bootstrap function exists anywhere in `quant_lab` or `C:\QuantTrading` (grepped, zero matches). Per user direction, **Test B is dropped from this run.** This document and the resulting verdict cover **Test A only**. No claim is made about live-drawdown-vs-variance for either sleeve.

## Data sources (confirmed on disk, not rebuilt)

- **Trend**: `TrendFollowing/trend_v4_daily_returns.csv`, column `strategy_net` — full history 2008-01-03 to present (4,644 daily observations).
- **MeanReversion**: `quant-portfolio/docs/erc_validation_sleeve_returns.csv`, column `mr_return` — confirmed by `erc_validation_report.md` line 25 to be the direct, unmodified output of `MeanReversionStrategy.backtest(start='2019-01-01', end='2026-06-17')`, `daily_pnl / $1,000,000` NAV. Native range 2019-07-08 to 2026-06-16 (1,747 observations), spanning the strategy's own documented IS (2019-2022) / OOS (2023-2026) split.

## Test A methodology (fixed now)

Using `quant_lab/validation/robustness.py`'s `deflated_sharpe_ratio()` and `probability_of_backtest_overfitting()`, imported and called exactly as written, unmodified.

**DSR inputs:**
- `observed_sharpe`: annualized Sharpe computed directly from each sleeve's full return series above (`mean/std * sqrt(252)`, ddof=0, matching the codebase's existing convention).
- `returns`: the daily series itself (T and skew/kurtosis computed internally by the function).
- `mean_sharpe_trials=0.0`, `std_sharpe_trials=1.0`: the standard null-hypothesis convention (skill-less trials centered at zero, unit Sharpe variance) — used because, unlike `quant_lab`'s `store.duckdb`, **TrendFollowing has no experiment-tracking database and no empirical population of historical trial Sharpes to draw real mean/std from.** This is disclosed as the textbook default, not a measured population statistic.
- `n_trials`: **honestly bounded, not a single flattering number.** TrendFollowing is confirmed **not a git repository** (`git status` → "fatal: not a git repository") — there is no commit history to mine for distinct parameter variations tested. No design doc quantifies a trial count either; `mean_reversion_strategy.py`'s docstring states parameters are "FROZEN from the validated IS/OOS backtest" but does not say how many configurations were tried to get there. In the absence of real evidence, n_trials is bounded by **counting named tunable constants in each sleeve's own code** as a floor (one trial per parameter, the most conservative-toward-PASS assumption — an actual build plausibly revisits parameters multiple times, which would only push the true count higher and DSR lower):
  - Trend (`signal_engine.py` `CFG` dict): 21 named tunable constants → **floor n_trials = 21**. A higher, still-conservative-relative-to-typical-practice estimate of **200** is also run to show sensitivity.
  - MeanReversion (`mean_reversion_strategy.py` class constants): 10 named tunable constants → **floor n_trials = 10**. Higher estimate: **100**.
  - Both bounds are reported for both sleeves. This is an acknowledged weakness of this test given the data available — it is disclosed rather than papered over, exactly as the PEAD write-up modeled.

**PBO methodology — disclosed substitution:** True within-sleeve parameter-grid PBO would require the actual set of historically-tested parameterizations (returns per candidate configuration), which do not survive anywhere for either sleeve (same gap as n_trials above). As a fair, on-disk, undisclosed-nothing substitute, PBO is run using `probability_of_backtest_overfitting()` unmodified on the 3-column returns matrix already validated for the ERC study (`erc_validation_sleeve_returns.csv`: `trend_return`, `mr_return`, `vrp_return`, 2019-07-08 to 2026-06-16, aligned, 1,746 obs after alignment). This tests whether *selecting among the live sleeves* based on in-sample performance would have generalized out-of-sample (CSCV, n_splits=16) — a real and relevant overfitting question for this portfolio, but **not equivalent to** a single sleeve's own internal parameter-search PBO. Reported as a single PBO value shared by both sleeves' verdicts, labeled as this substitution, not as sleeve-specific parameter PBO.

## Decision rule (fixed now, Test A only)

For each sleeve independently:
- **PASS**: DSR > 0.95 at **both** the floor and higher n_trials estimate. Edge survives honest correction even under the more conservative (higher-trial-count) assumption.
- **FAIL**: DSR <= 0.95 at either n_trials estimate. If the floor estimate alone fails, that is reported as an unambiguous FAIL — the floor is the most generous assumption possible given the missing evidence.

PBO is reported alongside for context (shared substitution across both sleeves, per above) but is not, by itself, a pass/fail gate for this run given the substitution — it is interpretive context, disclosed as such.

Applied mechanically after computation. No threshold or n_trials value will be adjusted after seeing the DSR output.
