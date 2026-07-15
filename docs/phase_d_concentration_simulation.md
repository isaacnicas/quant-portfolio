# Phase D Concentration Simulation
Date: 2026-07-15
Scope: read-only investigation. No production code changes.

## Premise Correction (lead finding)

**The task's premise — that TLT/IEF/GLD are a planned, not-yet-implemented "Phase D" addition to Trend's universe — is false.** Checked directly against `signal_engine.py`'s `UNIVERSE` dict (lines 6-13): TLT, IEF, and GLD are already there (classified `bond`/`bond`/`commodity`), alongside FXE/FXY (`fx`). They were already present in `data/prices.csv` and already included in the exact reconstruction that produced `docs/concentration_risk_diagnostic.md`'s 43.8% tech3-share and 36.3% loss-contribution figures — that reconstruction's `total_gross` denominator already summed across all 12 instruments, TLT/IEF/GLD included.

**They are not just present — they are already substantially used.** Checked directly against the already-validated 492-day reconstruction:

| | Mean weight | Current weight | Max weight | % of days active (nonzero) |
|---|---|---|---|---|
| TLT | 1.00% | 0.00% | 24.27% | 12.4% |
| IEF | 2.42% | 0.00% | 37.17% | 22.2% |
| GLD | 25.60% | 0.00% | 50.13% | **92.9%** |
| TLT+IEF+GLD combined | **22.44%** | 0.00% | 66.93% | — |
| All 5 diversifiers (+FXE/FXY) | **28.79%** | 0.00% | 98.89% | — |

GLD alone is active on 93% of all reconstructed trading days, averaging over a quarter of Trend's total gross exposure. There is no "before Phase D" state to compare against — the 43.8%/36.3% figures in the original diagnostic **already reflect a world where fixed income and gold are available and substantially allocated.** Re-running "the same reconstruction with TLT/IEF/GLD added" would be a no-op, reproducing identical numbers, because nothing would change.

## What This Means for the Six-Counsel Round

The shared recommendation to "test whether Phase D organically dilutes the concentration before building anything custom" was reasonable advice given what the six counsels were told — but the underlying assumption behind it is now known to be false. The organic-dilution hypothesis was not an untested, deferred option; it was already in effect, and despite that, the tech3 cluster still reached 43.8% of gross exposure and still drove 36.3% of the 10 worst days' total portfolio loss. This doesn't invalidate the rest of the counsels' advice (a continuous mechanism rather than a hard trigger, embedding the fix in sizing rather than bolting it on, defining the cluster fixed rather than dynamically, using an N_eff/risk-contribution basis rather than a raw weight-sum threshold, validating against the full return distribution rather than only the worst days) — it removes exactly one candidate path forward: waiting for organic diversification to solve this on its own. That path has already been tried, continuously, for the full reconstructed history, and it has not been sufficient.

## Exploratory Cap-Relaxation Test (not a validated design decision)

Since the diversifiers are already present and active, the one remaining structural lever that could still plausibly let them absorb more of tech3's allocation is `position_sizer.py`'s diversifier cap:

```python
# position_sizer.py:37-45
eq_gross  = raw[equity_tickers].sum()
div_gross = raw[divers_tickers].sum()
total_gross = eq_gross + div_gross
if total_gross > 0 and div_gross / (total_gross + 1e-10) > CFG['divers_gross_cap']:
    scale_div = (CFG['divers_gross_cap'] * total_gross) / (div_gross + 1e-10)
    for t in divers_tickers:
        if t in raw.index:
            raw[t] *= scale_div
```

`CFG['divers_gross_cap'] = 0.30` (`signal_engine.py:20`): if the diversifier bucket (TLT+IEF+GLD+FXE+FXY combined) would exceed 30% of pre-leverage-cap total gross exposure, it's scaled down to exactly 30%. This is a real, currently-active constraint — confirmed binding on **242 of the 492 reconstructed days overall** (49%).

**But checked specifically on the 10 known worst days (same dates as the original diagnostic, using the prior trading day's weights that actually drove each day's return): the cap binds on only 1 of the 10.**

| Worst day | Prior-day pre-cap diversifier ratio | Cap binding? |
|---|---|---|
| 2026-06-05 | 0.0% | No |
| 2026-03-03 | 15.6% | No |
| 2026-01-30 | 23.0% | No |
| 2024-12-18 | 20.9% | No |
| 2025-10-10 | 12.4% | No |
| 2024-09-03 | 37.5% | **Yes** |
| 2026-03-20 | 21.1% | No |
| 2026-03-26 | 22.3% | No |
| 2026-03-12 | 19.7% | No |
| 2025-11-13 | 3.0% | No |

On 9 of the 10 days, the signal itself wasn't demanding more diversifier exposure — pre-cap diversifier demand was already below 30% (in one case, 2026-06-05, exactly 0%). The cap simply wasn't the limiting factor on those days; relaxing it has nothing to act on.

**Reran the full day-by-day reconstruction with `divers_gross_cap` at 0.30 (baseline), 0.50, and 1.0 (effectively removed), then recomputed the same 10-day decomposition under each:**

| Scenario | Tech3 % of total portfolio loss (10 days) | Change vs. baseline |
|---|---|---|
| 0.30 (current, baseline) | 36.32% | — |
| 0.50 | 36.21% | -0.11pp |
| 1.0 (removed) | 36.21% | -0.11pp |

Only 2024-09-03 changes at all across scenarios (the one day the cap actually bound); the other 9 days are numerically identical in every scenario. Raising the cap to 50% already captures the full effect of removing it entirely — the signal never demanded more than ~37.5% diversifier share on any of these 10 days, so a 50% ceiling and no ceiling are indistinguishable here.

**Verdict on the cap-relaxation lever specifically: it does not materially help.** 36.3% → 36.2% is not a meaningful reduction by any reasonable threshold, let alone the 20% bar that would signal a genuinely material effect. This is consistent with, not contradictory to, the premise-correction finding above: the diversifiers are already unconstrained enough, on the days that matter, to allocate more if the signal wanted to — it simply didn't want to, on 9 of these 10 days. Loosening the cap further doesn't change a signal that isn't asking for more room.

## Implication for Next Steps

This makes a dedicated cluster mechanism more clearly necessary, not less. Two independent paths that could plausibly have diluted tech3's concentration — "wait for organic diversification via the existing universe" and "loosen the one constraint that limits how much of that diversification can be used" — have both now been checked directly against the same 10 worst days and both show negligible-to-no effect. Neither is a matter of degree that more patience or a bigger cap would fix: the diversifier bucket wasn't capital-constrained on 9 of these days, and even fully relaxing the one place it was constrained barely moves the number. This isn't sufficient on its own to finalize a cluster-cap design — that still needs the same pre-registered validation discipline the counsel round called for (defining the cluster's basis, testing against the full distribution and not just these 10 days, deciding whether it's a hard trigger or a continuous mechanism) — but the two most likely reasons to skip building one have each been tested now and neither holds up.
