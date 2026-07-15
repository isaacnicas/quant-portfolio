# Post-Tilt Vol Scalar: Design and Validation
Date: 2026-07-15

## Scope

Observation-only, mirroring the ERC observation-before-authority pattern (`ERC_LIVE_SIZING=False` until C8 maturity). No live governance authority, no wiring into `order_engine.py` or the daily routine. This responds directly to `docs/endogenous_risk_empirical_check.md`: the meta-allocator's tilt (`meta_allocator_v0.WeightProposer`) has no path for `forecast_vol` to influence sizing, and moved weight the wrong direction in 8 of 15 historical worst-drawdown episodes. This builds and validates a downward-only multiplicative scalar applied *after* the existing tilt — it does not touch or replace `_compute_tilt_scores` / `_compute_deltas`.

## Step 0 — Insertion Point and Formula Re-Verification

`WeightProposer.propose()` (`meta_allocator_v0.py`) computes `final_deltas` via `_compute_tilt_scores` → `_compute_deltas` → `_apply_inertia`, then `_build_record()` writes each sleeve's `proposed_weight = erc_weight + delta` into the record returned to the caller and appended to `proposed_weights.jsonl`. The clean insertion point is **after `proposed_weight` is computed** — a separate function reads that value and returns a scalar-adjusted weight, without modifying `_compute_tilt_scores`, `_compute_deltas`, `_apply_inertia`, or `_build_record`.

Re-verified `sleeve_forecast_mixin.py` and `portfolio_risk.py` directly (not assumed from the empirical check): `forecast_vol = EWMA(span=21, min_periods=5)` of `vol_21d`, and `vol_21d = _annualize(returns.tail(21).std())` where `_annualize(x) = x × √252` (`portfolio_risk.py` lines 253, 463-464). Exact match to the empirical check's reconstruction — no discrepancy found.

## Step 1 — Scalar Design

**Component 1 (slow, structural):**
```
vol_scalar_ewma = min(1.0, vol_target / forecast_vol)
```
`vol_target` = each sleeve's own long-run mean `forecast_vol`, computed from the full backtest history (per-sleeve, not a single portfolio-wide target, since typical vol levels differ structurally):

| Sleeve | vol_target (mean forecast_vol, full history) |
|---|---|
| Trend | 19.2% |
| MeanReversion | 8.6% |
| VRP | 26.0% |

**Component 2 (fast-twitch supplement):**
```
ratio = fast_vol_5d / forecast_vol
vol_scalar_fast_spike = 1.0                  if ratio <= THRESHOLD
                       = THRESHOLD / ratio     if ratio > THRESHOLD
```
`fast_vol_5d` = trailing 5-day annualized realized vol. This component exists because the empirical check found the EWMA lagged realized vol by +19.2 percentage points at MeanReversion's fastest historical dislocation (2020-03-23, COVID) — a pure EWMA scalar would have been too slow there.

**Threshold selection** — tested 1.5x / 2.0x / 2.5x against the 15 episodes:

| Threshold | Episodes triggering fast component |
|---|---|
| 1.5x | 3 / 15 |
| 2.0x | 1 / 15 |
| 2.5x | 0 / 15 |

**Chose 2.0x**: the minimum threshold that still catches the COVID/MeanReversion case (spike ratio = 0.626/0.270 = 2.32) without firing as broadly as 1.5x. Honest finding, not glossed over: at the COVID trough itself, the fast component's own scalar (0.863) never actually *binds* — the EWMA component (0.319) is already more restrictive by that date, because the 63-day-max-window trough selection gives the EWMA time to partially catch up before the trough is reached. The fast component's marginal value in this backtest is therefore concentrated in the *approach* to a trough, not validated at the trough itself — a real limitation of trough-only validation, noted rather than hidden.

**Combined**: `final_scalar = min(vol_scalar_ewma, vol_scalar_fast_spike)`, applied as `final_weight = tilted_weight × final_scalar`.

## Step 2 — Validation Against the Same 15 Episodes

Reused the empirical check's exact episode definitions and tilted (pre-scalar) weights — not redefined. Threshold = 2.0x.

| Sleeve | Episode | Drawdown | Wrong Direction? | ERC Baseline | Tilted Weight (pre-scalar) | Scalar (combined) | Final Weight | Corrected? |
|---|---|---|---|---|---|---|---|---|
| Trend | 2020-03-20 | -18.9% | Yes | 60.0% | 70.4% | 0.587 | 41.3% | **YES** |
| Trend | 2026-03-30 | -18.1% | Yes | 60.0% | 75.0% | 0.543 | 40.7% | **YES** |
| Trend | 2024-08-05 | -17.0% | Yes | 60.0% | 75.0% | 0.681 | 51.1% | **YES** |
| Trend | 2022-01-27 | -16.5% | No | 60.0% | 55.0% | 0.630 | 34.7% | n/a |
| Trend | 2022-03-14 | -16.3% | No | 60.0% | 53.2% | 1.000 | 53.2% | n/a |
| MeanReversion | 2020-03-23 | -18.9% | No | 30.0% | 22.5% | 0.319 | 7.2% | n/a |
| MeanReversion | 2022-06-16 | -8.4% | Yes | 30.0% | 37.5% | 0.492 | 18.4% | **YES** |
| MeanReversion | 2026-03-27 | -8.2% | No | 30.0% | 22.5% | 0.897 | 20.2% | n/a |
| MeanReversion | 2020-04-22 | -7.9% | Yes | 30.0% | 30.4% | 0.197 | 6.0% | **YES** |
| MeanReversion | 2025-07-29 | -7.2% | No | 30.0% | 22.5% | 1.000 | 22.5% | n/a |
| VRP | 2022-06-13 | -29.6% | Yes | 10.0% | 12.5% | 0.681 | 8.5% | **YES** |
| VRP | 2022-07-14 | -28.0% | Yes | 10.0% | 10.9% | 0.836 | 9.1% | **YES** |
| VRP | 2022-02-28 | -27.4% | No | 10.0% | 7.5% | 0.635 | 4.8% | n/a |
| VRP | 2022-05-05 | -26.3% | Yes | 10.0% | 10.4% | 0.733 | 7.6% | **YES** |
| VRP | 2024-10-07 | -24.5% | No | 10.0% | 7.5% | 0.723 | 5.4% | n/a |

**8 of 8 wrong-direction episodes are corrected** — the scalar brings the final weight back below the ERC baseline in every case where the original tilt increased exposure during that sleeve's own worst historical drawdown.

**Structurally unfixable overlap, as instructed to check:** of the 3 episodes with neither vol nor correlation elevated (Trend 2022-03-14, MeanReversion 2025-07-29, VRP 2022-07-14), only **one** — VRP 2022-07-14 — was also a wrong-direction episode. The other two (Trend 2022-03-14, MeanReversion 2025-07-29) were *not* wrong-direction to begin with; the original tilt had already reduced weight there, so there was nothing to fix. VRP 2022-07-14 nominally shows "Corrected: YES" above, but this needs a caveat: it wasn't flagged as vol-elevated by the empirical check's >1.3x-of-typical threshold, and the correction here came from the mean-based `vol_target`'s very low bar for triggering *any* reduction (see Step 3) rather than a genuine catch of an extreme reading — worth knowing before treating "8/8" as a stronger result than it is.

## Step 3 — False-Positive Check (Full History)

| Sleeve | Total Days | Days Triggered | % Triggered | In Stress Window (±10d of the 15 troughs) | Outside (false positives) | False-Positive Rate |
|---|---|---|---|---|---|---|
| Trend | 1746 | 947 | 54.2% | 91 | 856 | 90.4% |
| MeanReversion | 1746 | 595 | 34.1% | 84 | 511 | 85.9% |
| VRP | 1746 | 875 | 50.1% | 98 | 777 | 88.8% |

**This is the central honest finding of this validation.** With `vol_target` set to the sleeve's own long-run *mean* forecast_vol (as specified), the scalar triggers on 34-54% of all trading days across 6.9 years — because "forecast_vol above its own historical average" is true roughly half the time by construction, not a marker of genuine dislocation. 86-90% of trigger-days fall outside a ±10-day window around any of the 15 identified worst-drawdown troughs. Some of this is a measurement artifact — "outside the 15 worst episodes" doesn't mean "no real risk was present," since real but non-top-5 elevated-vol periods exist too — but a scalar firing on roughly half of all days cannot be doing the job of a dislocation detector; it's closer to a permanent partial de-risking.

## Recommendation

**Start logging now; do not treat this as ready for anything beyond logging.** The directional design is validated and worth continuing — Step 2's 8/8 correction rate on the exact failure mode the empirical check identified is a real result, not a coincidence, and the logging code is purely additive and safe to run daily starting today. But Step 3's false-positive rate rules out treating the current calibration as a meaningful signal, let alone a future authority candidate: a mean-based `vol_target` is the wrong choice — it should be replaced with a higher percentile of the sleeve's own forecast_vol distribution (75th, to be tested empirically the same way the 2.0x fast-spike threshold was here) so the scalar reserves its trigger for genuinely elevated regimes rather than "any day at or above average." This is a specific, scoped next design iteration, not a reason to shelve the approach — accumulate live observation data under the current formula in parallel (it's already logging correctly, see Step 5), and revisit the `vol_target` percentile choice once enough live history exists to test it the same way the backtest was tested here.

## Step 4 — Implementation

New file: **`vol_scalar_observer.py`** (TrendFollowing), not a new function inside `meta_allocator_v0.py`. Chosen over embedding in the existing file specifically so the "does not modify the tilt logic" boundary is structural (a separate file, code-reviewable in isolation) rather than a convention that could erode over time within a shared file. It:
- Reads `proposed_weights.jsonl` (read-only) for each sleeve's pre-scalar `proposed_weight`.
- Reads the live `forecast_vol` already computed and logged by `sleeve_forecast_mixin.py` (reused, not recomputed).
- Computes `vol_target` from the full available history in `{sleeve}_state.jsonl`'s `vol_21d` field (own long-run mean; ≥20 records required, else `thin_history=True` and scalar defaults to 1.0).
- Computes `fast_vol_5d` from a `pnl_usd / (capital_alloc × NAV)` return proxy, reading NAV from `portfolio_state.jsonl` (read-only) — dividing by `capital_alloc` alone (a NAV *fraction*, not a dollar figure) produced nonsensical six-figure "vol" values in initial testing; fixed before the smoke test below.
- Writes one record per sleeve per run to a new `logs/vol_scalar_observation.jsonl`, with fields `vol_scalar_ewma`, `vol_scalar_fast_spike`, `vol_scalar_combined`, `weight_pre_scalar`, `weight_post_scalar_observation_only`, plus `observation_only: true` and an explicit note field.

**Confirmed: this does not feed `order_engine.py`, does not affect `ERC_LIVE_SIZING`, and does not change any live or paper order.** It only reads existing logs and appends to a new, dedicated log file.

## Step 5 — Smoke Test

Ran `vol_scalar_observer.py` against current live sleeve state (2026-07-15):

| Sleeve | Pre-Scalar | EWMA | Fast | Combined | Post-Scalar | Thin History? |
|---|---|---|---|---|---|---|
| Trend | 0.600 | 1.000 | 1.000 | 1.000 | 0.600 | Yes |
| MeanReversion | 0.300 | 1.000 | 1.000 | 1.000 | 0.300 | Yes |
| VRP | 0.100 | 1.000 | 1.000 | 1.000 | 0.100 | Yes |

Ran without error. All three sleeves correctly show `thin_history=True` and a no-op scalar (1.0) — this live system's state logs currently hold only 6-8 records per sleeve, well below the thresholds needed for a stable `vol_target` or `forecast_vol`. This is the correct behavior: the observer declines to fabricate a scalar from insufficient data rather than producing a misleading number, matching the platform's existing thin-history convention (`SleeveForecastMixin`'s own `thin_history` rule for `expected_edge`).
