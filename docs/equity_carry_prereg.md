# Equity Carry — Gate 1 / Gate 2 pre-registration

Written and committed **before** any Phase 2 backtest of the Equity Carry
mechanism runs, per standing project discipline (design → pre-register →
approve → run, never the reverse). No backtest of this mechanism runs until
both gates below are satisfied and this document is committed.

## Scope

Governs Phase 2 (strategy design/backtest) of the Equity Carry foundation-build
effort, greenlit in
[`factor_timing_equity_carry_schedule_review.md`](factor_timing_equity_carry_schedule_review.md)'s
2026-08-12 decision. Does **not** authorize live capital or shadow-mode wiring
into any live sizing path — that boundary is unchanged, gated on the
2026-12-01 reminder date and a real go/no-go decision at that time.

## Background: why these two gates, specifically

Two independent risks apply to a naive dividend-yield strategy, both flagged
by counsel 5 in the six-counsel review round:

1. **Yield-trap risk.** A high dividend yield is frequently a symptom of a
   falling price (yield rises mechanically as price falls) or an unsustainable
   payout about to be cut, not a genuine risk premium. A naive high-yield
   screen with no quality filter systematically selects for distressed names.
2. **Factor-attribution risk.** Dividend-yield strategies are well documented
   in the academic literature to load heavily on the value factor (HML).
   Without a residual-return test, a positive backtest result could be fully
   explained by known value exposure rather than a distinct carry/income
   premium — which would mean this sleeve isn't actually diversifying against
   the portfolio's other sleeves, and shouldn't be presented to it as an
   independent return stream.

## Gate 1: yield-trap / quality filter

A candidate universe may only be constructed from names passing **all** of:

| Filter | Threshold | Rationale |
|---|---|---|
| Cash-flow coverage | trailing-12mo FCF ≥ dividends paid (coverage ≥ 1.0x) | excludes payouts funded by debt or balance-sheet drawdown rather than earnings power |
| Payout sustainability | dividends / net income ≤ 75% | standard sustainability ceiling; above it, one earnings miss forces a cut |
| Leverage | net debt / EBITDA ≤ **[Phase 1 open item — propose 3.5x, standard investment-grade ceiling, to confirm once a fundamentals data source is selected]** | excludes over-levered "yield" that is really default risk |
| Recent price collapse | exclude names down ≥ 30% over trailing 6 months | the mechanical signature of a yield trap — yield rising because price fell, not because the payout grew |

Universe construction happens **after** this filter, not before — a raw
high-yield screen that has not first passed Gate 1 is not eligible to enter
the candidate set at all.

**Data source: open Phase 1 item.** Fundamentals data must be point-in-time
(as-reported), not restated, for the same look-ahead reason as Factor
Timing's ISM PMI dependency. Candidates to evaluate: SEC EDGAR (already
integrated for PEAD in `quant_lab`) or SimFin (already integrated; see
`quant_lab/docs/edgar_vs_simfin_data_quality.md` for the existing
comparison — reuse that finding, don't re-litigate it).

## Gate 2: HML / market residual-return test

Regress the candidate strategy's return series against the Fama-French market
and HML (value) factors:

```
r_strategy = alpha + beta_mkt * r_mkt + beta_hml * r_HML + epsilon
```

**Pass condition** — alpha must be:
- Statistically distinguishable from zero at a pre-registered p < 0.10
  (one-sided). Deliberately looser than this project's typical p < 0.05 bar:
  carry/income sleeves are lower-Sharpe by design, and the stricter bar would
  reject the entire asset class even if the effect is real.
- Economically non-trivial: alpha ≥ 1%/year annualized (matches PEAD's
  minimum-detectable-effect precedent).

**Fail condition → honest relabeling, not automatic rejection.** If alpha
fails this bar but `beta_hml` is significant and positive, the mechanism is
not killed outright — it is relabeled as a **value tilt**, not an independent
carry sleeve, and evaluated for inclusion under that label, with the
diversification case reassessed accordingly (does the portfolio already carry
adequate value exposure via existing sleeves' incidental style tilts —
checked directly against the sleeves' actual factor loadings, not assumed).

## Order of operations

1. Gate 1 filter applied to construct the candidate universe.
2. Backtest the income/carry rule (DVY/VYM-style construction, per the
   original reminder's instrument list) on the Gate-1-filtered universe.
3. Gate 2 regression run on the resulting return series.
4. Only after both gates clear (or the mechanism is honestly relabeled per
   Gate 2's fail condition) does the sleeve proceed to this project's standard
   Confirmation-stage discipline — DSR/PBO, out-of-sample holdout, the same
   statistical gates every other sleeve has cleared. Gates 1 and 2 here are
   Equity-Carry-specific **Stressing**-stage checks (see
   `quant_lab/RESEARCH.md`'s 3-Stage Research Architecture); they precede
   Confirmation, they do not replace it.

## Explicit non-authorization

This document authorizes Phase 2 backtest work only. No live capital, no
shadow-mode wiring into any live sizing path, until 2026-12-01 is reached and
a real go/no-go decision is made — unchanged from the original
foundation-build boundary.
