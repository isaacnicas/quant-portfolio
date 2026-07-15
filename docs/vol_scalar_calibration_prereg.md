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
