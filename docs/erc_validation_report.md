# ERC Validation Report
Date: 2026-07-13
Validated by: Riskfolio-Lib 7.3.0

## What Was Tested

`portfolio_risk.py`'s `compute_erc_weights()` implements **inverse-volatility (IV) weighting, not true ERC**, despite the module and method being named "ERC" throughout. The relevant code (`portfolio_risk.py:117-128`):

```python
vol = self._realized_vol(sleeve_returns[sleeve])
# Inverse-vol weight: higher vol → smaller weight
raw_weights[sleeve] = self.target_sleeve_vol / vol
...
total = sum(raw_weights.values())
normalized = {s: w / total for s, w in raw_weights.items()}
```

Each sleeve's weight is a function of that sleeve's own realized volatility only (annualized std over the last 21 observations, via `_realized_vol`). No covariance matrix is constructed and no cross-sleeve correlation term enters this calculation. (`compute_cross_sleeve_correlations()` exists elsewhere in the same file and is computed for redundancy-flagging/logging purposes, but its output is never passed into `compute_erc_weights()`.) True ERC requires solving for the weight vector such that each sleeve's *risk contribution* — not its standalone volatility — is equal, which is a function of the full covariance matrix.

## Data

Three sleeve return series were built and inner-joined:

- **Trend**: `trend_v4_daily_returns.csv`, `strategy_net` column (pre-computed, canonical backtest output; used as-is per instruction, not reconstructed from `signal_engine.py`). Native range 2008-01-03 → 2026-06-17.
- **MeanReversion**: `MeanReversionStrategy.backtest(start='2019-01-01', end='2026-06-17')`, `daily_pnl` converted to a return series by dividing by NAV ($1,000,000). Native range 2019-07-08 → 2026-06-16.
- **VRP**: `VRPStrategy.backtest(start='2015-01-01', end='2026-06-17')`, `strategy_return` column (already a daily % return). Native range 2015-01-02 → 2026-06-16.

All three were truncated at the right edge to 2026-06-17 (the last date available in the Trend series) before the inner join, so the aligned matrix isn't distorted by MR/VRP extending past where Trend has no data.

**Aligned matrix: 2019-07-08 → 2026-06-16, 1,746 observations.** Left edge is bounded by MeanReversion's earliest available date. No gaps greater than 5 calendar days were found in the aligned index. Saved to `docs/erc_validation_sleeve_returns.csv`.

## Results

Custom weights were produced by calling `PortfolioRiskManager.compute_erc_weights()` directly and unmodified, with the same constructor parameters used in `portfolio_risk.py`'s own production `__main__` block (`target_portfolio_vol=0.11, target_sleeve_vol=0.10, lookback_days=21`).

Individual sleeve volatilities (annualized, last 21 observations, via `_realized_vol`): Trend 49.59%, MeanReversion 10.46%, VRP 25.74%.

`compute_erc_weights()` builds no covariance matrix, so for the Riskfolio-Lib comparison and the marginal-risk-contribution calculation below, a covariance matrix was reconstructed using the same window and method `portfolio_risk.py` uses elsewhere for correlations (`compute_cross_sleeve_correlations`: last-21-observation Pearson correlation), combined with the same `_realized_vol` annualized vols:

| | Trend | MeanReversion | VRP |
|---|---:|---:|---:|
| **Trend** | 0.245925 | -0.034871 | 0.097972 |
| **MeanReversion** | -0.034871 | 0.010945 | -0.016658 |
| **VRP** | 0.097972 | -0.016658 | 0.066229 |

This same covariance matrix was fed into Riskfolio-Lib's `Portfolio.rp_optimization(model='Classic', rm='MV', b=[1/3, 1/3, 1/3])` and `HCPortfolio.optimization(model='HRP', codependence='pearson', rm='MV', linkage='single')`.

| Sleeve | Custom (IV) | Riskfolio RP | Riskfolio HRP | Delta (Custom vs RP) |
|---|---:|---:|---:|---:|
| Trend | 0.1304 | 0.0963 | 0.1292 | +0.0341 |
| MeanReversion | 0.6182 | 0.7357 | 0.7940 | -0.1175 |
| VRP | 0.2513 | 0.1680 | 0.0768 | +0.0833 |

Max |Delta| (Custom vs Riskfolio RP): **0.1175** (11.75 percentage points, on MeanReversion).

**Tolerance verdict: DIVERGED** (threshold for DIVERGED is any |Delta| ≥ 0.02; all three sleeves exceed it).

## Marginal Risk Contributions

Two related quantities were computed against the covariance matrix above: raw Marginal Risk Contribution (MRC = ∂portfolio_vol/∂w_i) and Risk Contribution (RC = w_i × MRC_i, which sums to portfolio vol and is the quantity true risk-parity/ERC equalizes across assets — not raw MRC, which is not expected to be equal across assets once weights differ).

| Sleeve | MRC (custom) | RC (custom) | MRC (Riskfolio RP) | RC (Riskfolio RP) |
|---|---:|---:|---:|---:|
| Trend | 38.87% | 5.07% | 22.39% | 2.156% |
| MeanReversion | -2.18% | -1.35% | 2.93% | 2.156% |
| VRP | 21.15% | 5.32% | 12.84% | 2.156% |
| Portfolio vol | — | 9.04% | — | 6.47% |

Under **Riskfolio RP weights, Risk Contributions are equal across all three sleeves** (2.156% each, matching to 4 decimal places) — the expected signature of true ERC.

Under the **custom (IV) weights, Risk Contributions are not equal** (5.07%, -1.35%, 5.32%) — confirming the custom method is not true ERC. Notably, MeanReversion's risk contribution under custom weights is *negative*: despite receiving the largest weight (61.82%), MeanReversion is negatively correlated with both Trend and VRP, so on a full-covariance basis it is diversifying (reducing) portfolio risk rather than adding to it. Inverse-volatility weighting has no way to see this, since it only ever looks at each sleeve's own volatility in isolation.

## Interpretation

`portfolio_risk.py`'s `compute_erc_weights()` produces inverse-volatility weights, not true equal-risk-contribution weights, and the divergence from Riskfolio-Lib's RP optimizer (up to 11.75 percentage points on MeanReversion) is fully explained by this: the custom method has no mechanism to account for the negative correlation between MeanReversion and the other two sleeves, so it cannot detect that MeanReversion is a risk-reducing diversifier rather than treating it purely as a low-volatility sleeve deserving more capital. This is not evidence of an implementation bug relative to what the code is actually written to do — the code correctly computes inverse-volatility weights as written — but it is evidence that the "ERC" naming throughout `portfolio_risk.py` (module docstring, method name, code comments) does not match what the method computes, which is directly relevant to any Phase-E decision that assumes `ERC_LIVE_SIZING` weights are true risk-parity weights.

## Post-Fix Re-Validation (2026-07-13)

Method updated to: Riskfolio-Lib RP (MV, equal budgets)

`compute_erc_weights()` was replaced to delegate directly to Riskfolio-Lib's `rp_optimization(model='Classic', rm='MV', rf=0, b=None, hist=True)`, using full-sample historical covariance (`assets_stats(method_cov='hist')` over the entire aligned matrix) rather than the last-21-day window used for the pre-fix IV comparison above. `b=None` yields equal risk budgets by Riskfolio-Lib's own default (`rb = ones(N,1)/N`). Falls back to equal weights when joint history is below the 21-day minimum (this is the expected/correct behavior during C8 immaturity, not a defect).

Re-run using the exact same input as the original study — `docs/erc_validation_sleeve_returns.csv`, unchanged, not rebuilt (2019-07-08 → 2026-06-16, 1,746 observations) — with an independent re-derivation of Riskfolio RP against the same full-sample covariance basis the fixed method now uses internally.

**Result: CONVERGED** (all three |Delta| = 0.0000)

| Sleeve | Custom (post-fix) | Riskfolio RP | Riskfolio HRP | Delta (Custom vs RP) |
|---|---:|---:|---:|---:|
| Trend | 0.2286 | 0.2286 | 0.1292 | 0.0000 |
| MeanReversion | 0.5816 | 0.5816 | 0.7940 | 0.0000 |
| VRP | 0.1898 | 0.1898 | 0.0768 | 0.0000 |

Max |Delta| (Custom vs Riskfolio RP): **0.0000**. (HRP is a different clustering-based method entirely and is not expected to match RP — shown for reference only, unchanged from the original study.)

MRC equality confirmed under new weights: **Risk Contributions are equal across all three sleeves under the post-fix custom weights** (3.7247%, 3.7246%, 3.7245% — matching to 4 decimal places, portfolio vol 11.17% annualized), identical to Riskfolio RP's own risk contributions computed against the same weights and covariance matrix — the defining signature of true ERC, and a direct contrast to the pre-fix IV weights' unequal (and for MeanReversion, negative) risk contributions above.

## Files
docs/erc_validation_sleeve_returns.csv — sleeve return matrix used
