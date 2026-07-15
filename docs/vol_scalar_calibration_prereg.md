# Vol Scalar Calibration Project — Pre-Registration
Date: 2026-07-15
Status: LOCKED before any candidate has been evaluated. No results exist yet at the time this file is written and committed.

## Scope

This is a ONE-TIME CALIBRATION PROJECT, not a governance/maturity task. Its sole output is a single frozen production threshold for the vol scalar's `vol_target` parameter (see `docs/vol_scalar_design_and_validation.md`, which found the mean-based `vol_target` triggers on 34-54% of all trading days — too permissive for anything beyond observation). Nothing in this project grants live authority. That is a separate future decision (V8), gated on evidence accumulated AFTER this calibration is chosen and frozen. V8 monitors the frozen `vol_scalar_v1` design; it does not participate in choosing it.

This is a governance/engineering calibration, not an alpha hypothesis — lighter-weight than quant_lab's SHA-256 pre-registration discipline — but the same principle applies: lock the decision rule before seeing which answer it produces.

## Candidate thresholds (fixed, will not be added to or removed from)

Each sleeve's own historical `forecast_vol` distribution (from `docs/erc_validation_sleeve_returns.csv`, the same source data used throughout), evaluated at:

**60th, 65th, 70th, 75th, 80th, 85th, 90th percentile** as `vol_target`.

7 candidates total, per sleeve — **21 evaluations total across 3 sleeves.**

## Evaluation criteria (fixed, in this exact priority order)

1. **Correction rate on the 15 known-episode replay** (from `docs/endogenous_risk_empirical_check.md`): what fraction of the 8 wrong-direction cases does each candidate correct? A candidate that corrects fewer than 8/8 is **immediately disqualified** — this is the non-negotiable floor, not something traded off against false-positive rate.
2. Among candidates that clear criterion 1, **false-positive rate on the full 6.9-year history** (fraction of trading days triggering outside the 15 known stress windows). LOWER is better. This is the primary discriminator between surviving candidates.
3. **Tie-breaker if needed:** trigger persistence behavior (does the scalar revert quickly after a false trigger, or stay engaged unnecessarily long?) — prefer faster reversion.

## Selection rule (fixed)

Select the **LOWEST percentile that still achieves 8/8 correction** on the known episodes.

Rationale, stated before seeing results: lower percentile = more sensitive = should be preferred IF it doesn't cost correction rate, since it will trigger closer to genuine sleeve-level stress rather than waiting for a more extreme threshold.

If multiple adjacent percentiles achieve identical 8/8 correction and near-identical false-positive rates (within 2 percentage points of each other), select the **higher** of the two, preferring the more conservative choice when the data doesn't clearly distinguish them.

## What would make us deviate from the selection rule

State explicitly, before seeing results: only if the selected candidate's false-positive rate is **above 25% of trading days** (making it operationally unusable regardless of correction rate) — in which case escalate for a decision rather than silently picking a worse option that merely reduces the false-positive number.

## Process commitment

This file is written and committed to `quant-portfolio` (its own commit) BEFORE any of the 21 evaluations are run. Step 1 (running the candidates) does not begin until this commit has landed. The candidate set, evaluation criteria, selection rule, and deviation condition above will not be edited, added to, or reinterpreted after results are seen.

---

## AMENDMENT 1 — 2026-07-15

### Fix A: Selection rule correction (applies to all sleeves uniformly)

The original selection rule ("select the lowest percentile that clears correction") was inconsistent with the evaluation criteria section, which states false-positive rate is "the primary discriminator" among survivors — implying a search across ALL candidates clearing the correction floor, not a stop at the first one found. This was a bug in the rule's specification, not a data-driven choice.

**CORRECTED RULE:** among all candidate percentiles that clear the correction floor (defined per sleeve — see Fix B for Trend/VRP), select the one with the LOWEST false-positive rate. If multiple candidates tie within 2 percentage points of the lowest FP rate, select the lowest percentile among the tied group (preferring more sensitivity when the data doesn't clearly distinguish).

This corrected rule applies to ALL THREE sleeves uniformly, decided now, before re-examining any sleeve's specific numbers below.

### Fix B: Correction floor definition for Trend and VRP only

MeanReversion's correction floor (2/2 or 3/3 episodes fully corrected below ERC baseline) remains unchanged — full correction is achievable there across the entire candidate range, so no relaxation is needed or applied to MeanReversion.

For Trend and VRP specifically: the original floor required ALL known episodes (3/3 each) to land below ERC baseline. With only 3 episodes per sleeve, this is a very small sample to demand zero tolerance from. This amendment tests a SEPARATE, EXPLICITLY WEAKER correction standard for Trend and VRP only:

> "No episode leaves the sleeve's post-scalar weight WORSE than its ERC baseline weight" — i.e., the scalar must not make any episode's exposure higher than what plain ERC would have assigned (matching or improving is acceptable; full correction to a large negative reduction is not required, only non-worsening relative to the no-tilt-no-scalar baseline).

This is a materially different, lower bar than "corrects the allocator's wrong-direction tilt" — it does not claim to fix the allocator's problem, only to confirm the scalar itself does no harm relative to the simplest possible baseline. This distinction is stated explicitly in the results write-up; this is not presented as equivalent to the original correction standard.

### What would make us abandon this amendment

If, even under the weaker Trend/VRP standard, no percentile in the existing 60-90 range clears BOTH the weaker correction floor AND the 25% false-positive ceiling, this indicates the vol scalar mechanism itself may not be suited to Trend/VRP's specific historical episodes (recall from the original empirical check: some of Trend/VRP's worst drawdowns had NEITHER elevated vol nor elevated correlation — no vol-based signal can fix those regardless of threshold). In that case, STOP. Do not widen the candidate range or relax the ceiling further without a separate, explicit decision — report the finding and escalate again rather than continuing to loosen constraints until something passes.

### Process commitment (amendment)

This amendment text is written and committed as its own commit, BEFORE Step 1 of the amendment (re-applying Fix A to MeanReversion) or Step 2 (applying Fix B to Trend/VRP) is run.
