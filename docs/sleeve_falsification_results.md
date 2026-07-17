# Sleeve Falsification Test — Results (Test A only)

Methodology fixed in `docs/sleeve_falsification_prereg.md` before any number below was computed. Test B (bootstrap vs. live drawdown) was dropped before Step 1 — the PEAD long-leg bootstrap it would have reused was never actually built. No claim is made here about whether today's live drawdown is ordinary variance or an outlier.

## Trend

- Data: `TrendFollowing/trend_v4_daily_returns.csv`, `strategy_net`, full history 2008-01-03 to 2026-06-17, T=4,644.
- Observed annualized Sharpe: **0.8619** (skew -0.425, kurtosis 6.457).
- DSR (n_trials=21, floor — one trial per named `CFG` constant): **0.0000** (sr0 = 1.9221)
- DSR (n_trials=200, higher estimate): **0.0000** (sr0 = 2.7655)

## MeanReversion

- Data: `quant-portfolio/docs/erc_validation_sleeve_returns.csv`, `mr_return`, native range 2019-07-08 to 2026-06-16, T=1,746 (matches the strategy's own documented IS/OOS split).
- Observed annualized Sharpe (full period): **0.3453** (skew 0.289, kurtosis 24.204 — unusually fat-tailed, flagged below).
- IS (≤2022-12-31) Sharpe: 0.4305 (n=880) — matches the strategy docstring's claimed "~+0.45."
- OOS (≥2023-01-01) Sharpe: 0.2294 (n=866) — matches the docstring's claimed "~+0.24."
- DSR (n_trials=10, floor — one trial per named class constant): **0.0006** (sr0 = 1.5746)
- DSR (n_trials=100, higher estimate): **0.0000** (sr0 = 2.5306)

## PBO (context, not a gate — disclosed substitution)

3-sleeve selection matrix (`trend_return`, `mr_return`, `vrp_return`, aligned, T=1,746), CSCV n_splits=16, 12,870 combinations: **PBO = 0.1139**. This tests whether picking the best-looking sleeve in-sample would have generalized out-of-sample across the 3 live sleeves — not within-sleeve parameter-search PBO, which no surviving data supports for either sleeve. 0.11 is well below the 0.5 "no better than chance" line, i.e. this specific cross-sleeve selection question shows no overfitting signal. This does not offset the DSR result below — it answers a different question (sleeve-selection robustness, not single-sleeve edge significance).

## Mechanical verdict (Step 0 rule applied exactly, no adjustment after seeing the numbers)

**Trend: FAIL-A.** DSR = 0.0000 at the floor n_trials estimate (21) — fails immediately per the rule ("if the floor estimate alone fails, that is reported as an unambiguous FAIL"). Test B not run (dropped).

**MeanReversion: FAIL-A.** DSR = 0.0006 at the floor n_trials estimate (10) — same outcome. Test B not run (dropped).

## What this implies — one paragraph per sleeve

**Trend**: under the pre-registered convention (mean=0, std=1 annualized-Sharpe null across trials — the standard textbook default, used because TrendFollowing has no experiment-tracking database to draw a real trial population from), Trend's observed 0.86 Sharpe over 4,644 daily observations does not come close to clearing the expected-max-Sharpe bar even at the most generous plausible trial count (sr0=1.92 at n=21 vs. observed 0.86) — the gap is large enough that this result is not sensitive to the n_trials uncertainty (21 vs. 200 barely moves DSR, both ≈0). It is sensitive to the null-distribution convention itself: std=1 in annualized-Sharpe units is a wide null, arguably calibrated for quant_lab's own use case (screening large numbers of essentially-random technical signal candidates), not for a strategy built from ~21 deliberately-chosen, individually-motivated parameters rather than a random sweep. This test does not distinguish "Trend's edge isn't real" from "the borrowed null convention is too aggressive for a hand-designed strategy" — that is a real, disclosed limitation of reusing this specific machinery as-is for this specific object, not a hidden one. Per the Step 0 rule as written, this is reported as FAIL-A and, mechanically, warrants reconsidering size/continuation — but the caveat above should weigh into how hard that conclusion is leaned on before acting on it alone.

**MeanReversion**: same structural picture — 0.35 Sharpe over 1,746 observations doesn't approach sr0 even at the floor n_trials (10), and the IS/OOS split (0.43 → 0.23) that the strategy's own docs treat as a validated decay-but-still-positive pattern reads very differently once run through this null: neither sub-period would come close to clearing DSR either. One additional, separate flag: MR's daily P&L kurtosis (24.2) is unusually fat-tailed for a Sharpe-based framework — worth checking as a data-quality question on its own (a small number of extreme days disproportionately shaping the series), independent of the DSR verdict. Same caveat as Trend applies to the null convention. Per the rule: FAIL-A, mechanically warranting the same reconsideration.

## Bottom line

Both sleeves fail Test A as pre-registered. This is reported plainly per the mechanical rule. It is **not** the same as "proven fake" — the single largest driver of both FAILs is a borrowed null-distribution assumption (std=1 in annualized Sharpe units) that was disclosed as a placeholder before any number was seen, not selected after the fact to produce this result, but whose fitness for a hand-engineered (not randomly-swept) strategy is itself an open question this test cannot resolve. Test B, which would have given an independent read on whether current live pain is ordinary variance, was never run. Recommended next step: before resizing or killing either sleeve on this result alone, either (a) source a defensible empirical trial-Sharpe population specific to how Trend/MeanReversion were actually built (would require reconstructing what doesn't currently exist), or (b) treat this result as one input — alongside the already-diagnosed execution gaps (concentration, no stop-losses, shadow-mode fixes not live) — rather than a standalone kill signal.
