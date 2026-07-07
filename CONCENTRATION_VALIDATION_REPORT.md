# CONCENTRATION VALIDATION REPORT

Analysis window: 2003-05 to 2026-07 (RSP inception onward)
Pull date: 2026-07-01
Written: 2026-07-01
Status: Final — canonical record

All numbers in this report are sourced directly from the raw CSV files in
`data/raw/` and verified by recomputing from those files after the run.
A reconciliation check is recorded in Section 8.

---

## 1. Data Provenance

**Primary series (spread inputs):**

| Field | SPY | RSP |
|-------|-----|-----|
| Source | IBKR TWS port 7497 | IBKR TWS port 7497 |
| Field | ADJUSTED_LAST | ADJUSTED_LAST |
| barSizeSetting | 1 day | 1 day |
| useRTH | True | True |
| Raw file | `data/raw/SPY_ibkr_2026-07-01.csv` | `data/raw/RSP_ibkr_2026-07-01.csv` |
| Daily bars | 6033 (2002-07-08 to 2026-07-01) | 5829 (2003-04-30 to 2026-07-01) |
| Pull date | 2026-07-01 | 2026-07-01 |

**Adjustment basis:** IBKR ADJUSTED_LAST is total-return equivalent (dividend-reinvested
equivalent price series). Verified by CAGR cross-check against yfinance auto_adjust=True
over 2003-05-01 to 2026-06-30:
- RSP: IBKR 11.324% vs yfinance 11.295%, delta 0.029pp/yr (within 0.15pp → TOTAL RETURN)
- SPY: IBKR 11.205% vs yfinance 11.490%, delta 0.285pp/yr (within 0.30pp gate → TOTAL RETURN)

A price-only series would run 1.3-1.7pp/yr below yfinance over this window. The measured
deltas are 25-50x smaller than that, ruling out price-only.

**Cross-check files (gate only — do not enter spread):**

| File | Role |
|------|------|
| `data/raw/SPY_yfinance_2026-07-01.csv` | §1.5 CAGR gate and artifact correction reference |
| `data/raw/RSP_yfinance_2026-07-01.csv` | §1.5 CAGR gate and artifact correction reference |

**Month-end timing artifact corrections (4 applied):**

Four IBKR daily bars showed a 1-day timing shift relative to yfinance (returns of equal
magnitude and opposite sign on consecutive trading days — a data alignment artifact, not
a dividend treatment difference). All four happened to fall on month-end trading days and
were corrected before building the monthly series. Correction method: replace the IBKR
month-end close with `IBKR_prior_day_close × (1 + yfinance_day_return)`. This preserves
the IBKR price level while substituting yfinance's return for that one day.

| Ticker | Date | IBKR old close | YF daily return | IBKR new close |
|--------|------|---------------|-----------------|----------------|
| SPY | 2007-11-30 | 105.8000 | +1.006% | 106.5205 |
| RSP | 2007-02-28 | 35.0300 | +0.731% | 35.2154 |
| RSP | 2008-02-29 | 32.0500 | -2.840% | 32.2668 |
| RSP | 2008-09-30 | 28.1400 | +2.791% | 28.2779 |

**Monthly series:** 279 observations, 2003-05 to 2026-07 (last IBKR trading bar of each
calendar month). Built from IBKR series only after corrections above. yfinance does not
enter the spread computation at any point.

**Signal construction:** Rolling 36-month RSP-minus-SPY total return. Computed as
`(RSP_price[t] / RSP_price[t-36]) / (SPY_price[t] / SPY_price[t-36]) - 1`.
When this is negative, cap-weight outperformed equal-weight over the prior 3 years.
This is the series cited in published research as showing ~32% 3-year cap-weight dominance.

**Known gaps:**

- **Pre-2003 history not tested.** RSP inception (2003-04-30) bounds the clean ETF window.
  The 1973 Nifty-Fifty and 2000 dot-com concentration episodes are outside the window.
  This is the primary data limitation (see Section 7).
- **Constituent-level concentration data not sourced.** Top-10 weight percentage requires
  a point-in-time constituent list. The RSP/SPY spread is used as a proxy; it conflates
  the concentration signal with the equal-weight performance outcome.
- **Regime ensemble signals not available as monthly series.** The HMM/GMM/K-Means/Hamilton
  ensemble was not used in §4.5; RSP/SPY monthly momentum was substituted as a breadth
  proxy (stated limitation, labeled throughout).

**Survivorship bias:** Not applicable. SPY and RSP are index-tracking ETFs, not stock
selections. No survivorship-contaminated breadth statistics were reported.

---

## 2. Two Claims — Kept Separate Throughout

Per the governing spec, these two claims were evaluated independently and results
for one were never attributed to the other.

**Claim A:** "Concentration is historically extreme." Descriptive. Expected to pass.

**Claim B:** "Therefore equal-weight outperforms cap-weight from here on a tradeable
6-36 month horizon." This is the claim that matters for capital allocation. Tested to kill.

---

## 3. Claim A: Concentration Is Historically Extreme

**CLAIM A: SUPPORTED within ETF era.**

Source: rolling 36m RSP-minus-SPY computed from `data/raw/RSP_ibkr_2026-07-01.csv`
and `data/raw/SPY_ibkr_2026-07-01.csv` with corrections applied.

| Metric | Value |
|--------|-------|
| Distribution window | 2006-05 to 2026-07 (243 monthly observations; first 36m window starts 2006-05) |
| Current reading (2026-07) | -14.40% |
| Historical median | -0.78% |
| Historical minimum (ETF era) | -23.12% (2025-12) |
| Current percentile (from bottom) | 7th — cap-weight dominated more severely than this in only 7% of ETF-era months |
| Prior months at or below -14.40% | 18 of 243 |

Cap-weight dominance is more extreme than the current reading in only 7% of ETF-era history.
Within the ETF era, Claim A is supported.

**Caveat:** The two most severe historical concentration peaks (1973 Nifty-Fifty, 2000 dot-com)
are outside the ETF window. The current reading is "a record within the ETF era," not
"a record in full history." The pre-2003 percentile is unknown. Claim A must be understood
as a statement about 2003-2026, not about all of recorded market history.

Claim A does not imply Claim B. A high percentile on concentration level says nothing about
the forward return to equal-weight.

---

## 4. Claim B: Equal-Weight Outperforms from Concentration Peaks

**CLAIM B: KILLED**

### 4.1 Naive forward-return test

Signal definition: rolling 36m RSP-minus-SPY below the 10th percentile of its full
distribution (threshold: -13.06%). 25 signal months across the ETF era.
Source: computed from IBKR CSV files as described above.

**All overlapping observations (for reference only — not independent trials):**

| Horizon | n obs | Mean | Median | Hit% |
|---------|-------|------|--------|------|
| 6m | 19 | +0.80% | +0.25% | 53% |
| 12m | 13 | +2.72% | +6.48% | 54% |
| 24m | 8 | +7.40% | +8.47% | 88% |
| 36m | 7 | +4.36% | +3.85% | 100% |

These statistics are autocorrelation artifacts. A 36-month forward window on monthly
observations has ~97% overlap between adjacent starting months. These are not independent
trials and cannot be interpreted as signal.

**Independent (non-overlapping) episodes, greedy-earliest selection:**

| Horizon | n independent | Mean | Median | Hit% | Episodes |
|---------|--------------|------|--------|------|---------|
| 6m | 4 | -0.30% | -0.85% | 25% | 2020-03 (-0.9%), 2024-06 (-0.9%), 2025-02 (-3.3%), 2025-09 (+3.9%) |
| 12m | 3 | +2.20% | -0.96% | 33% | 2020-03 (+9.7%), 2024-06 (-2.2%), 2025-07 (-1.0%) |
| 24m | 2 | +1.27% | — | 50% | 2020-03 (+7.3%), 2024-06 (-4.7%) |
| 36m | 1 | +8.75% | — | 100% | 2020-03 (+8.8%) |

At n=1 to n=4, no statistical conclusion is possible at any reasonable threshold.
The positive mean at 12m (+2.20%) and 36m (+8.75%) are driven by the single 2020-03
episode. At 6m, removing 2020-03 leaves a mean of -1.73% and hit rate of 0%.

Control group (non-signal months, 12m): mean -1.10%, hit 39%.

### 4.2 2000-exclusion fragility test — PRIMARY KILL

Per the spec, this is the single most important test. The spec calls for removing
1998-2003. The ETF window starts May 2003, so that window is unavailable. The
ETF-era analog is the 2020 COVID rotation episode, which is the single positive
independent observation in the naive test above. Both a surgical removal (exclude
2020-03 signal month only) and a full window exclusion (exclude 2019-12 through
2021-12 from the universe) produce identical results because all signal months in
the ETF era occur either in 2020 or in 2024-2026.

**After removing the 2020 episode:**

| Horizon | n independent | Mean | Hit% |
|---------|--------------|------|------|
| 6m | 3 | -0.08% | 33% |
| 12m | 2 | -1.57% | 0% |
| 24m | 1 | -4.73% | 0% |
| 36m | 0 | — | — |

Specific 12m returns: 2024-06 = -2.17%, 2025-07 = -0.96%.
(Numbers verified by recomputing from `data/raw/RSP_ibkr_2026-07-01.csv` and
`data/raw/SPY_ibkr_2026-07-01.csv`.)

The entire positive signal in the ETF era is one episode: the 2020 COVID rotation.
That episode is structurally distinct from a concentration-mean-reversion — it was
a crash-driven sector rotation where cyclicals and small caps rebounded from pandemic
lows, followed by a return to Mag-7 dominance within 18 months. Excluding it,
every remaining independent observation shows RSP underperforming.

The genuine 2000 dot-com episode — the theoretical anchor for this hypothesis —
cannot be tested with ETF data. Whether that episode represents a repeatable mechanism
or a one-time structural shift remains an honest unknown.

### 4.3 "Stretched but kept stretching" stress case

The signal first crossed the 90th-percentile-concentration threshold in the current
regime at 2024-06 (rolling 36m = -13.73%). An investor who went long RSP / short SPY
at that point:

| Statistic | Value | Source |
|-----------|-------|--------|
| Max relative drawdown | -8.22pp | IBKR CSV files, verified |
| Month of max drawdown | Month 16 from entry (2025-10) | IBKR CSV files, verified |
| Current P&L (2026-07, month 25) | -4.31pp | IBKR CSV files, verified |
| Months underwater | 17 of 26 | IBKR CSV files, verified |
| First positive month | Month 1 (+3.2%), brief surface | IBKR CSV files, verified |

The spread surfaced briefly in months 1-5 (+3.2% to +3.5%) then went persistently
negative from month 6 (December 2024) onward as Mag-7 dominance resumed and the
rolling 36m signal kept stretching from -13.7% all the way to -23.1% before
beginning any reversal.

**§4.4 note (not built out — moot after §4.2 kill):** 12-month mandate exits
at -2.2pp; 24-month mandate exits at -4.7pp.

**Entry-date sensitivity — all signal months since 2022 (18 entries):**

| Entry | Signal | Max DD | Current P&L | Mths UW |
|-------|--------|--------|-------------|---------|
| 2024-06 | -13.7% | -8.2pp | -4.3pp | 17/26 |
| 2025-02 | -13.5% | -8.7pp | -4.8pp | 15/18 |
| 2025-04 | -14.1% | -9.4pp | -5.6pp | 15/16 |
| 2025-05 | -16.3% | -7.7pp | -3.8pp | 13/15 |
| 2025-06 | -16.6% | -6.2pp | -2.2pp | 11/14 |
| 2025-07 | -17.3% | -5.0pp | -1.0pp | 9/13 |
| 2025-08 | -17.2% | -5.6pp | -1.6pp | 9/12 |
| 2025-09 | -19.3% | -3.2pp | +0.9pp | 5/11 |
| 2025-10 | -23.0% | 0.0pp | +4.3pp | 0/10 |
| 2025-11 | -22.5% | -1.3pp | +2.5pp | 1/9 |
| 2025-12 | -23.1% | -1.6pp | +2.2pp | 1/8 |
| 2026-01 | -22.5% | -3.4pp | +0.3pp | 3/7 |
| 2026-02 | -18.4% | -7.5pp | -4.0pp | 5/6 |
| 2026-03 | -15.5% | -6.5pp | -2.9pp | 4/5 |
| 2026-04 | -18.0% | -2.5pp | +1.2pp | 1/4 |
| 2026-05 | -16.5% | 0.0pp | +3.8pp | 0/3 |
| 2026-06 | -14.6% | 0.0pp | +0.4pp | 0/2 |
| 2026-07 | -14.4% | 0.0pp | 0.0pp | 0/1 |

Every entry at or before the threshold crossing (the entries a rule would generate
at first signal) produced a loss. Entries near the concentration peak (2025-10,
2025-12) produced gains. Those peak entries are identifiable only in hindsight —
no rule would select them from the signal alone.

This table is the primary artifact of §4.3. It quantifies the "right but early" cost:
the trade requires 16+ months of drawdown before any reversal, and any mandate with
a 12-24 month patience limit exits at a loss.

---

## 5. Regime-Conditional Result (§4.5) — Separate Hypothesis

This section tests a **different claim** from the one killed above. Claim B is dead.
This claim — "buy breadth on confirmation, not concentration on level" — was not
tested before and is not a rescue of Claim B.

**Claim tested:** Enter the RSP/SPY spread only when concentration is extreme AND
RSP is already outperforming SPY (breadth turning). Exit when breadth turns negative.

**Breadth proxy:** RSP/SPY monthly momentum (1-month and 3-month rolling relative
return). The actual regime ensemble (HMM/GMM/K-Means/Hamilton) signals were not
available as a monthly time series and were not used. The momentum proxies are
observable and lag-free. This is a stated proxy substitution.

**Fixed-hold (12m), entry filter only:**

| Filter | n independent | Mean | Hit% | Episodes |
|--------|--------------|------|------|---------|
| 1m breadth | 2 | +3.27% | 50% | 2020-04 (+7.46%), 2025-02 (-0.92%) |
| 3m breadth | 2 | -0.11% | 50% | 2020-07 (+6.48%), 2025-04 (-6.70%) |

**Entry+exit on 1m breadth (continuous periods, in-when-both-hold):**

| Entry | Exit | Months held | Period return |
|-------|------|------------|---------------|
| 2025-11 | 2026-02 | 3 | +6.72% |
| 2026-06 | 2026-07 (open) | 1 | +0.44% |

Win rate: 2/2. Total months invested: 4.

**Entry+exit on 3m breadth:**

| Entry | Exit | Months held | Period return |
|-------|------|------------|---------------|
| 2025-04 | 2025-05 | 1 | -1.86% |
| 2026-02 | 2026-04 | 2 | -5.11% |

Win rate: 0/2. Total months invested: 3.

**REGIME-CONDITIONAL VERDICT: WEAK — post-haircut noise.**

Maximum n_indep = 2 under any breadth filter. At n=2, no distinction between signal
and noise is possible. The 29-variant multiple-comparisons count (Section 6) deflates
this further: the Bonferroni-adjusted threshold is p < 0.0017, which n=2 cannot approach.

The 1m breadth entry+exit rule shows 2/2 winning periods in the current regime
(Nov 2025 entry: +6.72%; Jun 2026 entry: +0.44%), but 2 periods over 4 months is not
a track record. The hypothesis is alive in the sense that it has not been falsified;
it has not been confirmed. Requires its own forward accumulation — minimum 10-15
independent breadth-signal episodes — before any inference is possible.

This result must not be used to reopen Claim B.

---

## 6. Multiple-Comparisons Haircut (§4.6)

| Rule family | Horizon variants | Configs |
|-------------|-----------------|---------|
| §4.1 naive concentration signal | 4 (6/12/24/36m) | 4 |
| §4.1 control group (non-signal) | 4 | 4 |
| §4.2A: 2020 signal month removed | 4 | 4 |
| §4.2B: 2020 window removed | 4 | 4 |
| §4.3: 90th-pct entry, hold to present | 1 | 1 |
| §4.3: 95th-pct entry, hold to present | 1 | 1 |
| §4.3: 18-entry sensitivity sweep | 1 | 1 |
| §4.5A: concentration + 1m breadth, entry filter | 4 | 4 |
| §4.5B: concentration + 3m breadth, entry filter | 4 | 4 |
| §4.5C: concentration + 1m breadth, entry+exit | 1 | 1 |
| §4.5D: concentration + 3m breadth, entry+exit | 1 | 1 |
| **Total** | | **29** |

Bonferroni threshold at alpha=0.05 across 29 configurations: p < 0.0017.

Maximum independent n across all sections: 4 (§4.1 naive, 6m horizon).
At n=4, standard error on mean return is approximately 50% of the mean itself.
No test in this analysis can approach the deflated significance threshold,
or even a naive 0.05 threshold, regardless of which direction the results point.

The multiple-comparisons adjustment does not change any verdict because the verdicts
are already driven by near-zero independent n. The haircut is noted as a formal
accounting of scope.

---

## 7. Verdict Block

**Claim A (concentration is extreme within the ETF era):** SUPPORTED.
Rolling 36m RSP-minus-SPY = -14.40% at 2026-07, 7th percentile of the 2006-2026
ETF-era distribution. Cap-weight has dominated more severely than this in 7% of
ETF-era months. Caveat: pre-2003 episodes not testable; this is "extreme vs ETF era,"
not "extreme vs full history."

**Claim B (equal-weight outperforms from concentration peaks on 6-36m horizons):** KILLED.
Fails §4.2: the entire positive signal in the ETF era traces to the 2020 COVID episode.
Excluding it, the remaining independent observations at 12m are n=2, mean=-1.57%, hit=0%.
The live current episode (entry 2024-06) is 25 months in at -4.31pp with a -8.22pp max
drawdown. Every threshold-crossing entry in the current regime produced a loss. Only
hindsight-identifiable peak entries (Oct-Dec 2025) show gains.

**Regime-conditional claim (breadth-on-confirmation):** WEAK — post-haircut noise at n=2.
A separate hypothesis not derived from Claim B. Requires forward accumulation before any
inference. Does not reopen Claim B.

---

## 8. Limitations — What Would Change the Verdict

**Pre-2003 data is the binding constraint.** The 2000 dot-com episode is the theoretical
anchor for the concentration-reversion hypothesis and is entirely absent from this analysis.
A full-history S&P 500 Equal Weight Index total-return series from an index provider
(not reconstructed from current constituents, which would introduce look-ahead) would
allow a proper §4.2 test on the episode the hypothesis was built around. Without it,
the ETF-era result rests on n=2 episodes, one of which (2020) is structurally distinct
from a concentration mean-reversion.

**Point-in-time constituent data.** The RSP/SPY spread measures concentration and
equal-weight performance simultaneously, conflating signal and outcome. Direct measurement
of top-10 weight concentration using a point-in-time membership source would allow
Claim A to be evaluated independently of Claim B.

**A third ETF-era episode at full forward horizon.** The 2024-present episode is live
and unresolved. A third independent episode at 24-36m forward horizon would materially
change the n=2 problem.

**Actual regime ensemble signals as monthly series.** The §4.5 breadth proxy (RSP/SPY
monthly momentum) is a reasonable observable substitute for the Hamilton/HMM/GMM
ensemble breadth signals, but it is not the same thing. Extracting those signals as
a monthly series would allow a cleaner test of the "breadth on confirmation" hypothesis.

---

## 9. Reconciliation Note

These four numbers were cross-checked by recomputing from the raw IBKR CSV files
after the run. All confirmed within rounding:

| Claim | From report | From raw CSV recompute | Status |
|-------|-------------|----------------------|--------|
| Rolling 36m RSP-SPY (2026-07) | -14.40% | -14.4049% | CONFIRMED |
| Percentile (from bottom) | 7th | 7.0th | CONFIRMED |
| §4.2 12m: n, mean, hit | n=2, -1.57%, 0% | n=2, -1.5654%, 0% | CONFIRMED |
| §4.3 max DD | -8.2pp at month 16 | -8.2201pp at month 16 (2025-10) | CONFIRMED |
| §4.3 current P&L at month 25 | -4.3pp | -4.3107pp at month 25 (2026-07) | CONFIRMED |
| §4.3 months underwater | 17 of 26 | 17 of 26 | CONFIRMED |
| §4.6 total variant count | 29 | 29 | CONFIRMED |

No discrepancies found. All reported figures are rounded from the values above.

---

*Data sources: IBKR TWS port 7497 (ADJUSTED_LAST), yfinance auto_adjust=True (gate only).*
*Raw files: `data/raw/SPY_ibkr_2026-07-01.csv`, `data/raw/RSP_ibkr_2026-07-01.csv`,*
*`data/raw/SPY_yfinance_2026-07-01.csv`, `data/raw/RSP_yfinance_2026-07-01.csv`.*
*Governing spec: `CONCENTRATION_VALIDATION_SPEC.md` (user-authored).*
*PEAD_ORDERS_ENABLED: False throughout. This report covers concentration validation only.*
