# Empirical Check: Does the Meta-Allocator's Tilt Already Handle Endogenous Risk?
Date: 2026-07-15

## Scope

Measurement only. No governance logic was added, no gate was built, nothing was wired into the live order path. This replays the real, imported `WeightProposer._compute_tilt_scores()` / `._compute_deltas()` from `meta_allocator_v0.py` (TrendFollowing) against each sleeve's 5 worst historical drawdown episodes, to test whether the allocator's existing continuous tilt already dampens a sleeve's weight during its own vol/correlation dislocations — the gap identified in `endogenous_risk_gap_investigation.md` (2026-07-14).

## Method (see also `functional-conjuring-dream.md` plan for full detail)

- Source data: `docs/erc_validation_sleeve_returns.csv` (1746 rows, 2019-07-08 to 2026-06-16), reused as-is.
- Episodes: for each sleeve, the 5 worst peak-to-trough drawdowns over a max 63-trading-day window, ≥21 trading days apart.
- `forecast_vol` and `correlation_to_portfolio` reconstructed using the exact formulas confirmed by reading `sleeve_forecast_mixin.py` directly (not a rolling-stdev proxy): `forecast_vol` = EWMA(span=21) of rolling-21d annualized realized vol; `correlation_to_portfolio` = rolling 63d correlation of the sleeve's return series to the sum of the other two sleeves' returns. Both computed point-in-time (data strictly before the evaluation date), matching the mixin's own PIT guard.
- `expected_edge` reconstructed as trailing 63d Sharpe of daily return (`mean/std × √252`), matching `_compute_expected_edge` exactly under the assumption that per-day capital allocation is roughly constant within a 63-day window (Sharpe is scale-invariant to a constant multiplier; not exact under live time-varying sizing).
- **Reconstruction limitation, disclosed per the task's own instruction rather than silently substituted:** `confidence` is sleeve-specific and strategy-internal (e.g. VRP's `roll_yield / 0.15`) and is not reconstructable from a plain-returns CSV. This replay fixes `confidence = 1.0` for every sleeve at every point — an explicit **best-case, maximally-responsive** assumption. Real confidence is generally ≤1.0, so the real allocator's dampening in these same episodes would be **weaker**, not stronger, than what's reported below. This biases the whole exercise *toward* Verdict A (allocator already handles it); the findings below hold despite that bias, not because of it.
- No portfolio-level ERC risk contribution was computed (that's `portfolio_risk.py`, out of scope). This stays scoped to per-sleeve tilted weight from `meta_allocator_v0.py` alone.

## Results — All 15 Episodes

Sign convention: **positive Relative Reduction = the allocator reduced the sleeve's weight** (intended risk-off behavior). **Negative = the allocator increased the sleeve's weight** during that sleeve's own worst historical drawdown (the opposite of intended).

| Sleeve | Episode (trough) | Drawdown | Vol Elevated? | Corr Elevated? | ERC Baseline | Tilted Weight | Reduction (pp) | Relative Reduction | Persistence |
|---|---|---|---|---|---|---|---|---|---|
| Trend | 2020-03-20 | -18.9% | Yes | Yes | 60.0% | 70.4% | -10.4pp | **-17.4%** | persisted |
| Trend | 2026-03-30 | -18.1% | Yes | No | 60.0% | 75.0% | -15.0pp | **-25.0% (cap)** | persisted |
| Trend | 2024-08-05 | -17.0% | Yes | No | 60.0% | 75.0% | -15.0pp | **-25.0% (cap)** | persisted |
| Trend | 2022-01-27 | -16.5% | Yes | Yes | 60.0% | 55.0% | +5.0pp | +8.3% | persisted |
| Trend | 2022-03-14 | -16.3% | No | No | 60.0% | 53.2% | +6.8pp | +11.4% | persisted |
| MeanReversion | 2020-03-23 | -18.9% | Yes | No | 30.0% | 22.5% | +7.5pp | +25.0% (cap) | persisted |
| MeanReversion | 2022-06-16 | -8.4% | Yes | Yes | 30.0% | 37.5% | -7.5pp | **-25.0% (cap)** | persisted |
| MeanReversion | 2026-03-27 | -8.2% | Yes | Yes | 30.0% | 22.5% | +7.5pp | +25.0% (cap) | persisted |
| MeanReversion | 2020-04-22 | -7.9% | Yes | Yes | 30.0% | 30.4% | -0.4pp | **-1.5%** | reverted quickly |
| MeanReversion | 2025-07-29 | -7.2% | No | No | 30.0% | 22.5% | +7.5pp | +25.0% (cap) | persisted |
| VRP | 2022-06-13 | -29.6% | Yes | No | 10.0% | 12.5% | -2.5pp | **-25.0% (cap)** | persisted |
| VRP | 2022-07-14 | -28.0% | No | No | 10.0% | 10.9% | -0.9pp | **-9.4%** | persisted |
| VRP | 2022-02-28 | -27.4% | Yes | No | 10.0% | 7.5% | +2.5pp | +25.0% (cap) | persisted |
| VRP | 2022-05-05 | -26.3% | Yes | No | 10.0% | 10.4% | -0.4pp | **-4.1%** | persisted |
| VRP | 2024-10-07 | -24.5% | Yes | No | 10.0% | 7.5% | +2.5pp | +25.0% (cap) | persisted |

**8 of 15 episodes (bolded, negative) show the allocator increasing the sleeve's weight during that sleeve's own worst historical drawdown — the opposite of the intended risk-off response.** 4 of those 8 hit the ±25% cap in the wrong direction (Trend ×2, MeanReversion ×1, VRP ×1).

## Step 3 — Direct Answers

**1. Median and worst-case relative weight reduction: close to the cap, or well below it?**
Neither, in a way that matters more than magnitude alone: the **median relative reduction across all 15 episodes is -1.5%** — a net *increase* in exposure, not a reduction. The cap (±25%) is hit often (9 of 15 episodes), but almost as often in the wrong direction (4 times) as the right one (5 times). The allocator isn't "too weak" in a simple sense — it's frequently at full strength, but the sign is unreliable.

**2. Any episodes where vol/correlation stayed unremarkable even during a real drawdown?**
Yes, 3 of 15: Trend 2022-03-14 (-16.3% dd, neither vol nor correlation elevated), MeanReversion 2025-07-29 (-7.2% dd, neither elevated), VRP 2022-07-14 (-28.0% dd, neither elevated despite being VRP's second-worst drawdown on record). Correlation elevation is rare generally — only 4 of 15 episodes show it, meaning `correlation_to_portfolio` alone would be a weak trigger for most of these drawdowns even if it were wired in.

**3. Forecast Error Gap (realized `vol_21d` − `forecast_vol`): median and peak?**
Median gap ≈ 0.0 (-0.03pp), meaning on average, by the time a trough is reached, the EWMA-smoothed forecast has mostly caught up to realized vol. But the **peak gap is +19.2 percentage points (annualized)**, in MeanReversion's COVID trough (2020-03-23) — realized vol was dramatically ahead of what the smoothed forecast signal reflected at the worst moment. The EWMA is a lagging filter by construction; it works fine in typical episodes but under-reports the single fastest, sharpest dislocation in this dataset by a wide margin.

**4. Verdict: A or B?**
**B — the allocator's existing tilt does not meaningfully or reliably handle a sleeve's own endogenous risk dislocations, and a separate mechanism is justified.** Confidence: **high**, not merely medium, for one structural reason confirmed in Step 0 and now validated empirically in Step 2: the tilt score is `z_edge × confidence`, a **cross-sectional relative-Sharpe ranking**, with no path for `forecast_vol` or `correlation_to_portfolio` to influence it at all. It doesn't fail to react to a sleeve's own dislocation because the reaction is too small or too slow — it fails because it isn't measuring that dislocation in the first place. It happens to move the right direction when a sleeve's relative 63-day Sharpe is also its worst-ranked among the three sleeves, and the wrong direction otherwise — a coincidence, not a design property, and coincidence explains the 8-of-15 wrong-direction rate cleanly. This holds despite the `confidence = 1.0` best-case assumption biasing the whole replay toward finding the allocator *more* protective than it really is — the real, confidence-scaled allocator would show fewer, not more, protective episodes.

## Recommendation

Build a lightweight, **multiplicative, sleeve-own-state risk scalar** applied on top of (not replacing) the existing ERC-tilt output — not a redesign of the tilt logic itself, and not a discrete on/off gate. The existing tilt answers "which sleeve currently has better relative edge," a real and useful question the data shows it answers reasonably (median forecast-error gap near zero, cap-saturation shows it's not underpowered). The missing question is "is this specific sleeve's own risk state currently elevated, independent of how its edge ranks against the other two" — and nothing today asks that question with `forecast_vol` or `correlation_to_portfolio`, even though both are already computed and logged daily and sit unused. The cleanest fix, closely mirroring `pysystemtrade`'s `risk_overlay.py` (already reviewed this session): compute a per-sleeve scalar in [downward-only, ≤1.0] as something like `min(1, vol_target / forecast_vol)`, applied multiplicatively to the sleeve's final tilted weight, independent of the cross-sectional z-score machinery. This directly targets the 8-of-15 wrong-direction failure mode found here (a sleeve whose own vol has spiked gets scaled down regardless of how its relative edge ranks) without touching or destabilizing the tilt mechanism that's already working as intended for its own narrower purpose.
