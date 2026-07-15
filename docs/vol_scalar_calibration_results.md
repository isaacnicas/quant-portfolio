# Vol Scalar Calibration Project — Results
Date: 2026-07-15
Pre-registration: `docs/vol_scalar_calibration_prereg.md` (committed `31a8138`, before any candidate below was evaluated).

## Outcome: ESCALATED, NOT FROZEN

**The pre-registered selection rule, applied exactly as written, triggers the escalation/deviation condition for all three sleeves.** No `vol_scalar_v1` was frozen. `vol_scalar_observer.py` was not modified. This is not a workaround-avoidance choice — it is the literal, mechanical outcome of the rule as pre-registered, reported per the pre-registration's own instruction rather than silently substituted with a different rule.

## Step 1 — All 21 Evaluations

Fast-spike threshold (2.0x) held fixed throughout, unchanged from `docs/vol_scalar_design_and_validation.md`. `episodes_relevant` = that sleeve's own wrong-direction episode count from the 15-episode replay (Trend 3, MeanReversion 2, VRP 3 — sums to the 8 total from `docs/endogenous_risk_empirical_check.md`).

| Sleeve | Percentile | vol_target | Episodes Corrected (of relevant) | False-Positive Rate | Avg False-Trigger Persistence (days) |
|---|---|---|---|---|---|
| Trend | 60 | 0.2132 | 3/3 | 37.23% | 22.41 |
| Trend | 65 | 0.2224 | 3/3 | 32.65% | 17.27 |
| Trend | 70 | 0.2326 | 2/3 | 28.06% | 15.31 |
| Trend | 75 | 0.2449 | 2/3 | 23.20% | 13.50 |
| Trend | 80 | 0.2615 | 2/3 | 18.56% | 11.57 |
| Trend | 85 | 0.2771 | 2/3 | 13.92% | 9.35 |
| Trend | 90 | 0.3037 | 0/3 | 9.97% | 6.96 |
| MeanReversion | 60 | 0.0778 | 2/2 | 36.08% | 28.64 |
| MeanReversion | 65 | 0.0843 | 2/2 | 31.50% | 25.00 |
| MeanReversion | 70 | 0.0913 | 2/2 | 26.80% | 23.40 |
| MeanReversion | 75 | 0.0978 | 2/2 | 22.91% | 16.67 |
| MeanReversion | 80 | 0.1029 | 2/2 | 18.50% | 15.38 |
| MeanReversion | 85 | 0.1140 | 2/2 | 14.03% | 11.14 |
| MeanReversion | 90 | 0.1349 | 2/2 | 9.51% | 7.55 |
| VRP | 60 | 0.2727 | 3/3 | 39.69% | 16.12 |
| VRP | 65 | 0.2870 | 2/3 | 35.05% | 14.57 |
| VRP | 70 | 0.3020 | 2/3 | 30.41% | 12.64 |
| VRP | 75 | 0.3146 | 1/3 | 26.06% | 10.83 |
| VRP | 80 | 0.3312 | 1/3 | 22.05% | 9.17 |
| VRP | 85 | 0.3484 | 0/3 | 18.27% | 8.18 |
| VRP | 90 | 0.3771 | 0/3 | 14.26% | 6.55 |

## Step 2 — Mechanical Rule Application

**Trend:** candidates clearing criterion 1 (3/3 corrected): p60, p65 only (p70+ drop to 2/3 or 0/3). Selection rule picks the lowest of these — **p60**, FP = 37.23%. Deviation check: 37.23% > 25% → **escalation triggered**. No candidate in the full 60-90 range achieves 3/3 correction *and* FP ≤ 25% simultaneously — this is true regardless of which reading of the deviation clause is used; Trend has no viable candidate in the pre-registered set, full stop.

**MeanReversion:** all seven candidates clear criterion 1 (2/2 corrected at every percentile tested). Selection rule picks the lowest — **p60**, FP = 36.08%. Deviation check: 36.08% > 25% → **escalation triggered** under the literal rule text ("the selected candidate's false-positive rate," checked on the mechanically-chosen p60, not re-optimized after the fact). Flagged transparently for whoever resolves the escalation: unlike Trend and VRP, MeanReversion does have jointly-viable candidates elsewhere in the set — p75 (22.91%), p80 (18.50%), p85 (14.03%), and p90 (9.51%) all clear criterion 1 *and* sit under the 25% ceiling. The pre-registration's own text explicitly warns against the model silently jumping to one of these instead of the mechanical pick ("escalate ... rather than silently picking a worse option that merely reduces the false-positive number") — that warning is exactly why this was escalated rather than auto-resolved to p75-p90, even though such a resolution is visibly available here.

**VRP:** only **p60** clears criterion 1 at all (3/3; every other percentile drops to 2/3, 1/3, or 0/3). Selection rule has no alternative to pick — p60, FP = 39.69%. Deviation check: 39.69% > 25% → **escalation triggered**. As with Trend, no candidate in the set is jointly viable under either reading — VRP has no viable candidate, full stop.

## Was the selection rule followed exactly as pre-registered, with no deviation?

**Yes, exactly as written, with one explicit and pre-committed exception: escalation itself.** The pre-registration fixed a deviation condition in advance (false-positive rate above 25% on the selected candidate) specifically to cover this scenario. That condition fired for all three sleeves. Per both the pre-registration's own text and the calibration project's Step 2 instruction, this is reported directly rather than resolved by picking a workaround, redefining "viable," or silently substituting a different rule after seeing the results.

## What this finding means

The 8/8 known-episode correction floor and a false-positive rate low enough to be operationally usable (≤25% of trading days) are in real tension across most of the pre-registered candidate range, not just at the edges. For Trend and VRP specifically, they are in tension across the *entire* tested range (60th-90th percentile) — there is no percentile in this set, however chosen, that both fully corrects the known wrong-direction episodes and avoids triggering on more than a quarter of all trading days. MeanReversion is the partial exception: full correction holds at every tested percentile, and the false-positive rate only becomes acceptable at the higher end (p75+) — meaning MeanReversion's failure mode is milder (a genuine higher-percentile candidate exists) than Trend's or VRP's (no candidate exists in this set at all).

## Next Step (Escalated, Not Decided Here)

This calibration project is paused at the pre-registered escalation point, not closed. No `vol_scalar_v1` exists. Three options for how to proceed, without a recommendation baked in since this is exactly the decision the pre-registration reserved for a human:
1. Widen the candidate set beyond 90th percentile (a new, separately pre-registered calibration, since the current set is locked and "will not be added to").
2. Accept a per-sleeve tradeoff explicitly — e.g., use MeanReversion's p75-p90 candidates (viable) while treating Trend and VRP as still needing a different mechanism entirely, since no percentile-based `vol_target` works for them within this design.
3. Reconsider whether full (8/8 or per-sleeve-full) correction is the right non-negotiable floor, versus accepting partial correction in exchange for a usable false-positive rate — this would mean loosening criterion 1 itself, which the pre-registration deliberately fixed as non-negotiable and explicitly did not allow trading off.

---

# Amendment 1 Results
Amendment text: `docs/vol_scalar_calibration_prereg.md` § AMENDMENT 1 (committed `f7e15d5`, before any re-evaluation below).

## MeanReversion — Resolved

Reused the existing 7-candidate results above (no re-run needed). Applying the corrected Fix A rule (lowest false-positive rate among all candidates clearing the correction floor, not a stop at the first one found): all 7 candidates clear full correction (2/2), so the search runs across the entire set. **p90 has the lowest false-positive rate (9.51%)**, and no other candidate ties within 2 percentage points of it (the next-closest, p85, is 14.03% — a 4.5pp gap). Selection is unambiguous.

**Selected: p90, vol_target = 0.1349, false-positive rate = 9.51%.** This resolves cleanly, exactly as the amendment anticipated, with no further judgment calls needed.

## Trend and VRP — Remain Unresolved

Applied Fix B's weaker standard ("no episode leaves the sleeve's post-scalar weight worse than its ERC baseline weight") per-episode, across all 7 candidates for both sleeves, using the same underlying per-episode weight data as the original run (not a re-simulation).

**Empirical finding: the weaker standard produced byte-identical pass/fail results to the original strict standard, at every single percentile, for both sleeves.** This is not an approximation — it was checked episode-by-episode:

| Sleeve | Percentile | Episodes Meeting Weaker Standard (of 3) | Episodes Meeting Original Strict Standard (of 3) | False-Positive Rate |
|---|---|---|---|---|
| Trend | 60 | 3/3 | 3/3 | 37.23% |
| Trend | 65 | 3/3 | 3/3 | 32.65% |
| Trend | 70 | 2/3 | 2/3 | 28.06% |
| Trend | 75 | 2/3 | 2/3 | 23.20% |
| Trend | 80 | 2/3 | 2/3 | 18.56% |
| Trend | 85 | 2/3 | 2/3 | 13.92% |
| Trend | 90 | 0/3 | 0/3 | 9.97% |
| VRP | 60 | 3/3 | 3/3 | 39.69% |
| VRP | 65 | 2/3 | 2/3 | 35.05% |
| VRP | 70 | 2/3 | 2/3 | 30.41% |
| VRP | 75 | 1/3 | 1/3 | 26.06% |
| VRP | 80 | 1/3 | 1/3 | 22.05% |
| VRP | 85 | 0/3 | 0/3 | 18.27% |
| VRP | 90 | 0/3 | 0/3 | 14.26% |

**Why they're identical, not approximately close:** the original standard was already defined as "final post-scalar weight below ERC baseline" for episodes where the tilt had pushed weight *above* baseline. Fix B's weaker standard — "not worse than ERC baseline" — is the same comparison, just non-strict (`≤` instead of `<`). Checked directly at the per-episode level (all 21 candidate/episode combinations for both sleeves), no case landed close enough to baseline for the strict/non-strict distinction to matter; every episode is cleanly on one side or the other. The relaxation, as literally specified, does not change which candidates clear the floor.

Applying the corrected Fix A rule to the candidates that do clear (weaker = strict) floor: for Trend, only p60 and p65 clear at all, and the lowest-FP among them is **p65 (32.65%)** — still above the 25% ceiling. For VRP, only p60 clears, at **39.69%** — also above the ceiling.

**Per the pre-registered abandonment condition (Step 0 of this amendment): no percentile in the 60-90 range clears both the weaker correction floor and the 25% false-positive ceiling, for either Trend or VRP. STOPPING here, as instructed — not widening the candidate range or loosening the ceiling further in this pass.** This is consistent with the original empirical check's own finding that some of Trend's and VRP's worst historical drawdowns showed neither elevated vol nor elevated correlation (e.g. Trend 2022-03-14, VRP 2022-07-14) — no vol-based signal, at any threshold, can be expected to catch a dislocation its own inputs never flagged as unusual.

## Implication

**The vol scalar mechanism, as designed, should apply to MeanReversion only for now.** Trend and VRP continue to rely on the VIX gate alone — the same governance they had before this project began — until either a different signal (not a percentile of forecast_vol) is designed for their specific unfixable episodes, or a future, separately pre-registered calibration project revisits the candidate range with a clear rationale for doing so. This is not a partial or approximate fix for Trend/VRP; it is a clean decision not to apply an under-validated mechanism to two of the three sleeves, while still shipping the one sleeve where the evidence is unambiguous.

## Frozen: vol_scalar_v1

`vol_scalar_observer.py`, `VOL_TARGET_PERCENTILE`:
```python
VOL_TARGET_PERCENTILE = {"Trend": None, "MeanReversion": 90, "VRP": None}
```
Trend and VRP entries are `None`, not defaulted to any percentile or to the old mean-based approach — the observer's EWMA component is forced to a 1.0 no-op for both, and each logged observation record for these sleeves carries an explicit `"calibrated": false` flag plus a note explaining why, so this is never silently mistaken for a working calibration.
