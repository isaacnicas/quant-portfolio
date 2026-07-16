# Tech3 Cluster Penalty — Results
Date: 2026-07-15
Pre-registration: `docs/tech_cluster_penalty_prereg.md` (committed `72b0955`, before any candidate below was evaluated).

## Step 0 — Confirmed against actual source

- **Insertion point**: `position_sizer.py`, between `raw = raw * regime_scalar` and the `divers_gross_cap` block — before any downstream constraint, on the same raw-weight basis as the rest of the sizing pipeline.
- **UNIVERSE structure**: flat module-level dict in `signal_engine.py`; no existing cluster concept, so `TECH3 = ['QQQ', 'XLK', 'SMH']` was added as a new fixed constant.
- **No existing duplicate logic**: confirmed by reading both files in full — nothing resembling a risk-contribution or effective-N adjustment existed anywhere before this project.

## Full 6-Combination Comparison Table

Baseline (no penalty, validated to exactly reproduce `docs/concentration_risk_diagnostic.md`'s figures): tech3 = **36.32%** of 10-worst-day loss, full-sample Trend Sharpe = **1.0709**, CAGR = **26.55%**, max drawdown = **-18.04%**.

| Combination | Tech3 % of 10-worst-day loss | Tail reduction (relative) | Full Sharpe | Sharpe vs. baseline | Full CAGR | Full Max DD | Opp. cost: benign episodes (sum return) | Opp. cost: preceding-bad episodes (sum return) |
|---|---|---|---|---|---|---|---|---|
| A, T=40% | 25.97% | 28.4% | 1.1146 | **+4.1%** | 24.66% | -17.40% | -4.73% | -0.25% |
| A, T=50% | 31.25% | 13.9% | 1.0866 | +1.5% | 25.43% | -18.04% | -3.13% | +0.26% |
| A, T=60% | 34.19% | 5.8% | 1.1079 | +3.5% | 27.22% | -18.04% | +0.46% | +0.49% |
| **B, F=4.0** | **10.06%** | **72.3%** | **1.3209** | **+23.3%** | **29.23%** | **-16.92%** | -1.84% | -0.73% |
| B, F=4.5 | 5.37% | 85.2% | 1.2647 | +18.1% | 26.39% | -16.92% | -4.01% | -0.83% |
| B, F=5.0 | 4.82% | 86.7% | 1.2205 | +14.0% | 24.47% | -16.75% | -4.80% | -0.95% |

"Sharpe vs. baseline" is reported as a signed percentage where positive = improvement (all six combinations improve full-sample Sharpe; none degrade it — a genuinely unexpected and notable result in its own right, discussed below). Opportunity-cost columns are summed return impact (this scenario's Trend return minus baseline's, on the same days) across the 123 days where baseline tech3 share exceeded its own 75th percentile (40.90%) — split into 107 "benign" days (not within 5 trading days of one of the 10 known worst days) and 16 "preceding-bad" days (within 5 trading days before one).

## Mechanical Selection Rule Application

**Step 1 — disqualify below the 33%-relative tail-protection floor** (36.3% → above ~24.3% disqualifies):
- A, T=40%: 28.4% reduction → **disqualified**
- A, T=50%: 13.9% reduction → **disqualified**
- A, T=60%: 5.8% reduction → **disqualified**
- B, F=4.0: 72.3% reduction → clears
- B, F=4.5: 85.2% reduction → clears
- B, F=5.0: 86.7% reduction → clears

All three Candidate A (risk-contribution basis) thresholds fail the tail-protection floor. This is a real, notable empirical finding, not a coding error (verified via synthetic sanity checks before running on real data): bringing the cluster's *risk contribution* down to a target ceiling does not reduce its *dollar weight* nearly as aggressively as bringing its *effective-N* up to a floor does, because risk contribution is a correlation-weighted variance share, not a direct function of raw weight the way sum-of-squared-weights is.

**Step 2 — among the 3 surviving combinations, select smallest full-sample Sharpe degradation**: all three *improve* Sharpe rather than degrading it (B/F=4.0: +23.3%, B/F=4.5: +18.1%, B/F=5.0: +14.0%). "Smallest degradation" is applied literally as the signed minimum of the degradation metric — since more improvement registers as a smaller (more negative) degradation value, this selects **B, F=4.0** (-23.3%, the most negative / best value), not a post-hoc judgment call.

**Step 3 — tie-break check**: B/F=4.0 (Sharpe 1.3209) vs. the next-closest, B/F=4.5 (Sharpe 1.2647), differ by 0.0562 — well outside the 0.02 tie-break window. No tie-break needed; **B, F=4.0 is the unambiguous, mechanically-selected combination.**

**Abandonment condition**: not triggered. Three combinations clear the tail floor with comfortable margin, and none of them show any actual Sharpe degradation, let alone degradation exceeding 15%.

**Selected: Candidate B (Effective Number of Bets basis), F_B = 4.0.**

One deliberate note on this selection, stated plainly rather than glossed over: among the 3 floor-clearing candidates, F_B=4.0 has the *weakest* tail protection (72.3% vs. 85-87% for the tighter floors) but the *best* full-sample Sharpe. The pre-registered rule's priority order asks for smallest Sharpe degradation among floor-clearers, not the strongest tail protection among them — so F_B=4.0 wins by the rule as written, even though F_B=4.5 or 5.0 might look more conservative on a quick read of the table. This is exactly the kind of post-hoc temptation pre-registration exists to guard against, and the rule was followed as locked.

## Smoke Test — Shadow Mode Confirmed Not Touching Live Sizing

Ran `position_sizer.py` against current live data (2026-07-15):
- Standalone CLI call (`prev_weights=None`) produced sensible output; shadow log correctly wrote `n_eff_raw=2.734` (well below the F_B=4.0 floor, since a fresh dead-band start has no held-over weights to dampen the raw signal), `penalty_scalar=0.4813`, and both pre- and post-penalty weights for QQQ/XLK/SMH.
- **Critically verified, not just asserted**: re-ran the full 492-day sequential reconstruction using the *edited* `position_sizer.py` with `TECH_CLUSTER_PENALTY_LIVE=False`, carrying `prev_weights` forward exactly as the live system does. The resulting 2026-07-15 weights (IWM 0.375587, XLK 0.270836, SMH 0.210590, EEM 0.205286, QQQ 0.160437, SPY 0.135893, EWJ 0.105843) are **byte-for-byte identical** to the pre-edit reconstruction. Live order sizing is genuinely unaffected — not merely by code-path inspection, but confirmed empirically against the exact same sequential state the live system maintains.
- The shadow log (`logs/tech_cluster_penalty_shadow.jsonl`) is a new, dedicated file — `trend_state.jsonl` is written by a separate script (`trend_following_strategy.py`) that doesn't call `size_today_positions()` at all, so a new dedicated log (mirroring the `vol_scalar_observer.py` precedent) was the correct choice rather than intruding into an unrelated writer.

## What Would Need to Happen Before `TECH_CLUSTER_PENALTY_LIVE` Could Reasonably Flip to True

This is not decided here. Before that flag could reasonably move to `True`, a future decision would need: (1) enough shadow-mode history accumulated live — at minimum, several tech3-concentration episodes of the kind seen in the 492-day reconstruction (the current live system has only days of history; this needs weeks-to-months), to confirm the penalty's shadow-logged scalar behaves sensibly against real-time data and not just the reconstructed backtest; (2) a check that the smooth ramp doesn't produce excessive day-to-day turnover in live conditions (not tested here — the reconstruction measures return/Sharpe impact, not turnover/transaction-cost impact of the penalty itself); (3) confirmation that the +23.3% full-sample Sharpe improvement isn't an artifact of this specific 492-day window — the same kind of out-of-sample skepticism this project's own discipline has applied everywhere else (e.g., the vol scalar calibration's insistence on checking false-positive rates beyond the initial validation episodes). None of this is evaluated in this session; it is exactly the evidence a future, separate live-authority decision would need to weigh.
