# Tech3 Cluster Penalty — Pre-Registration
Date: 2026-07-15
Status: LOCKED before any candidate has been evaluated. No results exist yet at the time this file is written and committed.

## Scope

Build-and-validate project for a tech3 cluster concentration control inside Trend's own sizing logic, following the same pre-registration discipline as the vol scalar calibration project (`docs/vol_scalar_calibration_prereg.md`): lock methodology and selection rule before seeing any results. If a mechanism is selected, it ships in **shadow mode only** — computed and logged, never applied to live/paper order sizing in this project. Going live (`TECH_CLUSTER_PENALTY_LIVE = True`) is an explicit, separate future decision, not made here.

## Step 0 findings (confirmed against actual source, not assumed)

- **Insertion point**: `position_sizer.py`, between line 35 (`raw = raw * regime_scalar`) and line 37 (the `divers_gross_cap` block's comment). This operates on `raw` — the vol-target-sized, regime-scaled weights — before the diversifier cap, the leverage cap, and the dead-band, so the penalty acts on the same basis as the rest of the sizing pipeline and its effects aren't distorted by downstream constraints that haven't been applied yet.
- **UNIVERSE structure**: a flat module-level dict in `signal_engine.py` (`{ticker: asset_class}`), with `equity_tickers`/`divers_tickers` derived once at import time. There is no existing cluster-grouping concept — QQQ/XLK/SMH must be identified via a new fixed constant (`TECH3 = ['QQQ', 'XLK', 'SMH']`), the same pattern already used for `CFG['lev_etfs']`.
- **No existing duplicate logic**: confirmed by reading both files in full. The only per-instrument/per-bucket adjustments present are the vol-target sizing itself (uniform per-instrument formula), the diversifier gross cap (whole bond/commodity/fx bucket, not an equity sub-cluster), the portfolio leverage cap (uniform across all instruments), and the tiered dead-band (per-instrument thresholds by asset class, not a scaling penalty). Nothing resembling a risk-contribution or effective-N adjustment exists anywhere in either file.

## Fixed cluster definition

**QQQ + XLK + SMH.** Fixed, not dynamically reclustered. Reviewed at most annually — that review is not part of this project; it is a future, separate decision.

## Candidate penalty formulations (exactly 2, both tested identically)

Both operate on Trend's 7 equity instruments (SPY, QQQ, IWM, XLK, SMH, EEM, EWJ) — the same 7 used throughout `docs/concentration_risk_diagnostic.md` and `docs/phase_d_concentration_simulation.md`. Diversifiers (TLT, IEF, GLD, FXE, FXY) are untouched by either candidate; they are already governed by their own existing cap.

### Candidate A — Risk-contribution basis (counsel 1)

Using a rolling 63-trading-day covariance matrix Σ of the 7 equity instruments' daily returns, and the raw (pre-penalty) weight vector `w`, the cluster's risk contribution as a fraction of total portfolio variance is:

```
Var_total   = w' Σ w
RC_cluster  = (sum over i in {QQQ,XLK,SMH} of w_i * (Σw)_i) / Var_total
```

(Euler's theorem: risk contributions of all 7 instruments sum exactly to `Var_total`, so `RC_cluster` is a true percentage-of-variance share, not an approximation.)

If `RC_cluster` exceeds a target ceiling `T_A` (tested at **40%, 50%, 60%**), the cluster's 3 weights are scaled by a single factor `s ∈ (0, 1]`, applied to `w_QQQ, w_XLK, w_SMH` only (SPY/IWM/EEM/EWJ unchanged). Decomposing:

```
Var(s) = s² * A + s * B + C
  A = w_cluster' Σ_cluster,cluster w_cluster        (cluster's own variance term)
  B = 2 * w_cluster' Σ_cluster,other w_other          (cluster-to-rest cross term)
  C = w_other' Σ_other,other w_other                  (rest-of-book variance term)

RC_cluster(s) = (s² * A + s * B/2) / Var(s)
```

`s_full` is the value of `s` that solves `RC_cluster(s) = T_A` exactly, found via bisection on `s ∈ (0, 1]` (numerically robust, avoids transcription error in the closed-form quadratic root). When `RC_cluster` at `s=1` is already `<= T_A`, `s_full = 1.0` (no correction needed) — this is continuous with the penalized region by construction, since the bisection target at exactly `RC_cluster = T_A` returns `s=1`.

**Smoothness (no discontinuity at the threshold)**: a piecewise-linear ramp, width `w_A = 0.05` (5 percentage points of risk-contribution) either side of `T_A`:

```
raw_RC <= T_A - w_A            → scalar = 1.0
T_A - w_A < raw_RC < T_A + w_A → scalar = linear interpolation between 1.0 (at T_A - w_A) and s_full (at T_A + w_A)
raw_RC >= T_A + w_A            → scalar = s_full
```

`s_full` at the ramp's upper edge is recomputed using `raw_RC` evaluated at `T_A + w_A` (i.e., the actual bisection target is always "what scale brings RC to `T_A`", evaluated using that day's real A/B/C decomposition — the ramp only interpolates the blend between no-penalty and full-penalty, not the target itself).

### Candidate B — Effective Number of Bets basis (counsel 5)

```
N_eff = 1 / Σ w_i²   (across the 7 equity weights)
```

If `N_eff` drops below a floor `F_B` (tested at **4.0, 4.5, 5.0**) due to tech3 concentration, the cluster's 3 weights are scaled by `s`, other 4 unchanged. Because sum-of-squares decomposes additively (no cross terms, unlike covariance), this has an exact closed form:

```
SS_cluster = w_QQQ² + w_XLK² + w_SMH²
SS_other   = w_SPY² + w_IWM² + w_EEM² + w_EWJ²
s_full     = sqrt( max(0, (1/F_B - SS_other) / SS_cluster) )     (clipped to [0, 1])
```

**Smoothness**: same piecewise-linear ramp construction, mirrored since `N_eff` is a "higher is better" metric (opposite direction from Candidate A's "lower is better" `RC_cluster`), width `w_B = 0.5` (half an effective bet) either side of `F_B`:

```
raw_N_eff >= F_B + w_B            → scalar = 1.0
F_B - w_B < raw_N_eff < F_B + w_B → scalar = linear interpolation between 1.0 (at F_B + w_B) and s_full (at F_B - w_B)
raw_N_eff <= F_B - w_B            → scalar = s_full
```

## Evaluation criteria (in this exact priority order, fixed before seeing results)

1. **Tail protection**: tech3's contribution to the original 10 worst days (36.3% baseline, from `docs/concentration_risk_diagnostic.md`) — measure the reduction under each candidate/threshold combination.
2. **Opportunity cost**: measured across the full historical distribution of tech3 concentration episodes (not just the 10 worst days) — specifically, total return/Sharpe impact during all periods where tech3 share exceeded its 75th percentile (per the original diagnostic, this threshold has been crossed multiple times without a subsequent bad day — this criterion is designed to capture whether the penalty destroys value during those benign episodes, separated explicitly from episodes that were followed by a bad day).
3. **Full-sample impact**: Trend sleeve's overall CAGR, Sharpe, and max drawdown across the entire reconstructed 492-day history, capped vs. uncapped — not just the stress episodes.

## Selection rule (fixed before seeing results)

Among all candidate/threshold combinations (2 formulations × 3 thresholds = 6 total):

1. **Disqualify** any combination that reduces tech3's 10-worst-day contribution by less than 33% relative (i.e., from 36.3% to above ~24.3%) — the tail-protection floor. Non-negotiable, not traded off against the other criteria.
2. Among combinations clearing that floor, **select the one with the smallest full-sample Sharpe degradation** (criterion 3).
3. **Tie-break** if within 0.02 Sharpe of each other: prefer the formulation with the smaller opportunity cost during benign high-concentration episodes (criterion 2).

## What would make this project conclude "no viable mechanism exists"

If **every one of the 6 combinations** either fails the tail-protection floor (criterion 1) **or** degrades full-sample Sharpe by more than **15% relative** — stop. Do not widen the threshold search or invent new formulations in this same pass. Report and escalate, same discipline as the vol scalar calibration's abandonment condition.

**Why 15%**: this mirrors the order of magnitude already used elsewhere in this project's own discipline as an "operationally unusable" bar (the vol scalar calibration's 25%-false-positive ceiling for a materially different metric, but the same spirit — a threshold large enough that no reasonable reading of "the fix is worth its cost" survives it). A 15% relative Sharpe hit to the anchor sleeve, in exchange for fixing a tail-concentration issue, is large enough that even a mechanism which fully solves the tail problem would plausibly not be worth deploying at that cost — Trend is described everywhere in this codebase as "the anchor" sleeve; degrading its normal-times performance by double digits to fix an 8-of-15-episode-style tail issue would very likely fail a basic cost-benefit test regardless of the tail benefit. This is stated as a hypothesis to be checked, not a foregone conclusion — if all 6 combinations land in the 10-15% range with strong tail protection, that would be a close, real judgment call worth escalating rather than silently passing or failing.

## Process commitment

This file is written and committed to `quant-portfolio` (its own commit) BEFORE any of the 6 candidate/threshold combinations are evaluated. Step 2 (building the candidate functions) and Step 3 (running them) do not begin until this commit has landed. The cluster definition, candidate formulations, evaluation criteria, selection rule, and abandonment condition above will not be edited, added to, or reinterpreted after results are seen.
