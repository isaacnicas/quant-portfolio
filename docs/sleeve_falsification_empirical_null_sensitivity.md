# Sleeve Falsification — Empirical Null Sensitivity Check

Follow-up to `sleeve_falsification_results.md`. That result flagged the std=1.0 null convention (borrowed from `quant_lab`'s signal-screening use case) as the likely dominant driver of both FAIL-A verdicts, disclosed as an open question rather than resolved. This document reconstructs the **real** population of variants actually tried during each sleeve's development and re-runs DSR against it. This is a post-hoc sensitivity analysis, not a re-run of the pre-registered test — the original FAIL-A verdicts in `sleeve_falsification_results.md` stand as committed.

## Real populations reconstructed (not a hypothetical grid)

**Trend** — TrendFollowing has no git history (not a repo), but `trend_following_strategy.ipynb`'s v3→v4 redesign cells document real, actually-backtested standalone Sharpes for each signal component considered, plus the superseded v3 combined result:

| Variant | Sharpe | Disposition |
|---|---|---|
| Kalman signal (standalone) | 0.208 | Rejected — "complexity without payoff" |
| Carry signal (standalone) | 0.357 | Rejected — "doesn't justify the plumbing" |
| CS-Mom (standalone) | 0.339 | Kept (20% weight) |
| v3 combined (HRP + 3 compounding gates) | 0.24 | Superseded by v4 |
| TSMOM (standalone) | 0.52 | Kept (80% weight) — "the engine" |
| v4 final (observed_sharpe under test) | 0.87 | Live |

n=6. **Caveat, disclosed not hidden**: this mixes standalone signal-component Sharpes (Kalman/Carry/TSMOM/CS-Mom — sub-parts of a signal) with full-strategy Sharpes (v3 combined, v4 final) — different levels of the pipeline, pooled because they're what the actual design record contains, not because they're a clean like-for-like population.

**MeanReversion** — `RESEARCH.md`'s "Development path: what failed first" section documents exactly two backtested Sharpes for genuinely different parameterizations (pairs trading was also tried but rejected at the statistical-filter stage before producing a Sharpe, so it isn't a numeric data point):

| Variant | Sharpe | Disposition |
|---|---|---|
| Single-name z-score, no dead-band | -0.30 | Rejected — 70% weekly turnover ate the edge |
| Final (dead-band + momentum filter) | 0.45 | Live |

n=2. **Caveat, stated plainly**: a standard deviation computed from 2 points carries enormous estimation uncertainty in its own right — this is the real, honestly-smallest population that survives in the documentation, not a confident statistical estimate.

## Empirical stats

| | n | mean | std (ddof=0) |
|---|---|---|---|
| Trend | 6 | 0.4223 | 0.2237 |
| MeanReversion | 2 | 0.0750 | 0.3750 |

## DSR side by side

**Trend** (observed_sharpe = 0.8619, full 2008-2026 series):

| Configuration | n_trials | mean | std | DSR |
|---|---|---|---|---|
| Original run (param-count floor) | 21 | 0 | 1.0 | 0.0000 |
| Same real n_trials, still default std | 6 | 0 | 1.0 | 0.0317 |
| **Literal ask: empirical std, mean=0** | 6 | 0 | 0.2237 | **0.9922 — crosses 0.95** |
| Fully empirical (mean and std both real) | 6 | 0.4223 | 0.2237 | **0.7355 — does not cross** |

**MeanReversion** (observed_sharpe = 0.3453, full 2019-2026 series):

| Configuration | n_trials | mean | std | DSR |
|---|---|---|---|---|
| Original run (param-count floor) | 10 | 0 | 1.0 | 0.0006 |
| Same real n_trials, still default std | 2 | 0 | 1.0 | 0.3228 |
| **Literal ask: empirical std, mean=0** | 2 | 0 | 0.3750 | 0.6541 — does not cross |
| Fully empirical (mean and std both real) | 2 | 0.0750 | 0.3750 | 0.5788 — does not cross |

## Reading this honestly — the divergence is real, but it doesn't cleanly flip the verdict

The user's own framing was: if the numbers diverge meaningfully, that confirms the null-convention mismatch was the actual driver, not the strategies. **They diverge meaningfully — by two to three orders of magnitude in DSR terms, in every single configuration tested, for both sleeves.** That part is unambiguous: std=1.0 was doing most of the work in the original FAIL-A verdicts, exactly as flagged.

What it does **not** do is cleanly convert both sleeves to PASS. Only one of four configurations — Trend, literal "swap std only, keep mean=0" — actually crosses the pre-registered 0.95 line. Every other configuration, including the more internally consistent "fully empirical" version for Trend, and both empirical versions for MeanReversion, still falls short of 0.95, even though all are dramatically higher than the original near-zero results.

The choice between "std-only-swap, mean=0" and "fully empirical" is not cosmetic — it answers different questions. Mean=0 asks "does the winner beat a null of zero average skill across trials of this type," which is the textbook DSR convention but is arguably inconsistent with using an empirical std drawn from a population that clearly wasn't zero-skill on average (Trend's own component Sharpes averaged 0.42, not 0). The fully-empirical version asks "does the winner stand out even relative to how good this specific development process's own trials tended to be" — a harder bar, and the one with real precedent in this codebase (`quant_lab/backtester-mcp-audit/compare_pbo_dsr.py`'s Test Case C used real population mean and std together for exactly this reason, explicitly rejecting mean=0/std=1 as "a placeholder-only assumption... not appropriate here" once a real population exists). That precedent favors the fully-empirical reading, which keeps both sleeves as FAIL, just far less decisively than the original run.

## Verdict on this sensitivity check

**The null-convention mismatch is confirmed as a major driver of the original FAIL-A results — not a minor footnote.** DSR moved from ~0.000-0.0006 to 0.32-0.99 across the board once real trial counts and real dispersion replaced the borrowed defaults. **The FAIL does not stand on firmer ground purely from the original result** — it was materially inflated by an ill-fitting null. But the FAIL also isn't cleanly overturned: under the more methodologically defensible fully-empirical convention, both sleeves still fall short of the pre-registered 0.95 bar (Trend 0.74, MeanReversion 0.58) — meaningfully closer to passing, genuinely uncertain, not a clean exoneration either. The honest summary is that the original test was measuring the wrong null more than it was measuring these two sleeves, and a better-specified null still leaves an open, materially-improved-but-unresolved question rather than a clean answer in either direction. Given n=6 and n=2 real trial counts, neither number should be treated as precise — both are small-sample estimates of an estimate.
