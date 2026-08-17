# Equity Carry — Gate 1 Leverage Threshold, Locked Pre-Registration

**Status: SEALED.** No return data was examined at any point before
this was locked. Companion to `equity_carry_prereg.md` (Gate 1/Gate 2's
original design) and `quant_lab/docs/equity_carry_missingness_audit.md`
(the missingness investigation that preceded this).

**Machine-readable spec:** `equity_carry_gate1_leverage_config.yaml` in
this directory. SHA-256: `688a2c2b044880622fa1d6e45ddd15666c09a106d89cf1e0c1226b3712654fa8`
(recorded here and in the commit message that added both files). Any
Gate 2 execution script must load its thresholds from that file, not
accept ad hoc threshold arguments.

## Estimation sample (Step 1)

Non-financial, non-REIT, non-financial-institution firm-years,
2018-2023 (report_date fiscal year), high-confidence debt tiers only
(`consolidated_tag_high_confidence` + `bare_total_tag_confirmed` —
*not* `current_noncurrent_sum`, *not* the low-confidence
consolidated-equals-noncurrent tier). Utilities are included in the
primary universe — 2 of 4 counsel reviews argued for a carve-out, 2
argued retain; retaining is the less-discretionary default, and
utilities remain subject to Gate 1's other three filters (cash-flow
coverage, payout ratio, price-collapse exclusion) regardless.

696 of 1,356 base rows (51.3%) survive the high-confidence-tier filter.

## Leverage computation (Step 2)

`net_debt = total_debt - cash`. EBITDA ≤ 0 is an automatic fail,
excluded from the percentile distribution (not from the fail count).
Net cash (net_debt < 0) is an automatic pass. No winsorization is
applied to the pass/fail determination at any point — winsorization is
display-only, used only if reporting summary stats on an
outlier-distorted distribution.

Of the 696-row base: 480 (69.0%) have a fully computable ratio, 45
(6.5%) are automatic passes (net cash), 21 (3.0%) are automatic fails
(EBITDA ≤ 0), and 150 (21.6%) are indeterminate — 124 EBITDA missing,
26 cash/debt missing.

## The real distribution (Step 3)

n=480 (ratio_computed population only):

| P50 | P75 | P80 | P85 | P90 | P95 | P97.5 | P99 |
|---|---|---|---|---|---|---|---|
| 2.43x | 3.94x | 4.55x | 5.05x | 5.72x | 7.70x | 9.96x | 13.60x |

Fraction above threshold: >2.0x = 60.0%, >2.5x = 47.7%, >3.0x = 37.9%,
>4.0x = 25.0%, >5.0x = 15.6%, >6.0x = 9.6%.

## Primary cutoff (Step 4)

`primary_cutoff = min(4.00, P90=5.72) = 4.00x`.

**Stated explicitly, per instruction, because it matters for how this
number gets described later: 4.00x is the pre-registered CEILING
binding here, not an empirically-discovered percentile or a structural
knee in the data.** P90 of the real distribution is 5.72x — well above
the ceiling. The ceiling is what determined the cutoff; the shape of
the distribution did not. Do not describe 4.00x in any later writeup as
"where the data naturally breaks" — it isn't. It's a pre-registered
cap that happened to bind.

## Stability check (Step 5)

At 4.00x, pass rate by year:

| Year | n determinable | pass rate |
|---|---|---|
| 2018 | 179 | 79.9% |
| 2019 | 168 | 74.4% |
| 2020 | 150 | 64.0% |
| 2021 | 49 | 83.7% |
| 2022 | 0 | — |
| 2023 | 0 | — |

All non-empty years fall inside the pre-registered [40%, 98%] band —
no flags. 2020's 64.0% is the low point, economically explained by
COVID-era EBITDA compression pushing ratios up, not an anomaly. 2022
and 2023 show zero determinable observations for a structural reason,
not a data-quality one: this universe's filings cluster around
December fiscal year-ends, filed roughly February-March the following
year, so FY2022/2023 10-Ks mostly publish past the `IN_SAMPLE_END`
holdout boundary (2023-12-31). The 2018-2021 read is real and clean.

## True pass rate vs. determinable-only pass rate — both reported, not just the favorable one

Two different denominators produce two different numbers, and both are
recorded so neither stands alone:

- **Pass rate among determinable cases only** (150 indeterminate rows
  excluded from the denominator entirely): 405/546 = **74.2%**.
- **True pass rate** (all 696 high-confidence-tier rows in the
  denominator; the 150 indeterminate rows count as non-passes, since a
  ticker-year Gate 1 cannot evaluate is not a pass): 405/696 = **58.2%**.

The 58.2% figure is the honest one for understanding what fraction of
the *real, full* high-confidence-tier universe would actually clear
Gate 1's leverage component. The 74.2% figure describes only the
subset where a leverage determination was even possible.

## Locked variant set (Step 6)

All four locked together, none chosen after seeing Gate 2:

| Variant | Debt tiers | Cutoff | n_total | True pass rate | Determinable pass rate |
|---|---|---|---|---|---|
| **PRIMARY** | high-confidence | 4.00x | 696 | 58.2% | 74.2% |
| **SENSITIVITY A** | high-confidence | 2.50x | 696 | 42.5% | 54.2% |
| **SENSITIVITY B** | high-confidence | 3.00x | 696 | 49.3% | 62.8% |
| **ROBUSTNESS** | high-confidence + `current_noncurrent_sum` | 4.00x (same as PRIMARY) | 1,052 | 59.3% | 74.4% |

ROBUSTNESS uses the *same* 4.00x cutoff as PRIMARY by design — it tests
whether admitting a lower-confidence debt tier into the eligible
population changes the result (it doesn't materially: 59.3% vs. 58.2%
true pass rate), not a second threshold to re-tune. This is a data-
confidence sensitivity check, not an alternative calibration.

## Status

Sealed 2026-08-17. No return data examined before sealing. Gate 2's
execution script must load thresholds from
`equity_carry_gate1_leverage_config.yaml`, not accept ad hoc arguments.
