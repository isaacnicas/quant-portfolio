> **SUPERSEDED — do not cite.** Canonical record is `CONCENTRATION_VALIDATION_REPORT.md` at repo root. This file was the intermediate draft written during the analysis run. It is retained for traceability only.

# Concentration Validation Report

Pull date: 2026-07-01
Written: 2026-07-01
Status: Final

---

## 1. Data Provenance

| Item | Detail |
|------|--------|
| SPY series | IBKR ADJUSTED_LAST, 6033 daily bars (2002-07 to 2026-07-01) |
| RSP series | IBKR ADJUSTED_LAST, 5829 daily bars (2003-04-30 to 2026-07-01) |
| Adjustment basis | Total-return equivalent. RSP CAGR delta vs yfinance auto_adjust: 0.029pp/yr. SPY delta: 0.285pp/yr. Both within the 0.30pp tolerance gate. |
| Month-end corrections | 4 applied: SPY 2007-11-30; RSP 2007-02-28, 2008-02-29, 2008-09-30. Each was an IBKR 1-day timing artifact on a month-end bar. Corrected by applying the yfinance daily return to the IBKR prior-day close. |
| yfinance role | §1.5 reconciliation gate and artifact corrections only. Does not enter the spread. |
| Monthly series | 279 observations, 2003-05 to 2026-07. |
| Signal construction | Rolling 36-month RSP-minus-SPY total return (the series cited in published research as showing ~32% cap-weight dominance, a purported record). |
| Concentration measurement | Proxied by RSP/SPY spread. Constituent-level data not available; point-in-time top-10 weight series not sourced. |
| Pre-2003 history | Not tested. RSP inception bounds the clean ETF window. The 1973 Nifty-Fifty and 2000 dot-com episodes are outside the window. This is the primary data limitation. |
| Survivorship | Not applicable to the spread (SPY and RSP are total-market indices, not stock selections). |

---

## 2. Claim A: Concentration Is Historically Extreme

**CLAIM A: SUPPORTED** (within ETF era; see caveat)

| Metric | Current (2026-07) | Hist. median | Percentile | Prior months at or below |
|--------|--------------------------|-------------|-----------|--------------------------|
| Rolling 36m RSP-minus-SPY | -14.40% | -0.78% | 93th (cap-weight dom.) | 18 of 243 months |
| All-time low in ETF era | -23.12% (2025-12) | — | — | — |

The rolling 36m RSP-minus-SPY sits at the 7th percentile of its full ETF-era distribution (2006-05 to 2026-07): cap-weight has dominated more severely than the current reading in only 7% of ETF-era months.

Caveat: this is extreme relative to 2003-present. The two most severe historical concentration peaks (1973 Nifty-Fifty, 2000 dot-com) are outside the window. The current reading is "a record within the ETF era" not "a record in history."

Claim A does not imply Claim B. A descriptive reading on concentration level says nothing about the forward return to equal-weight.

---

## 3. Claim B: Equal-Weight Outperforms Cap-Weight From Concentration Peaks

**CLAIM B: KILLED**

### 3.1 Naive forward-return test (§4.1)

Signal: rolling 36m RSP-minus-SPY in bottom decile (threshold -13.06%).
25 signal months across the ETF era.

| Horizon | n overlapping | n independent | Mean | Median | Hit% |
|---------|--------------|--------------|------|--------|------|
| 6m | 19 | 4 | -0.30% | -0.85% | 25% |
| 12m | 13 | 3 | +2.20% | -0.96% | 33% |
| 24m | 8 | 2 | +1.27% | +7.26% | 50% |
| 36m | 7 | 1 | +8.75% | +8.75% | 100% |

The overlapping statistics (12m mean +2.72%, 36m hit 100%) are autocorrelation artifacts, not signal. The independent-episode counts (n=1 to n=4) drive every conclusion.

Control group (non-signal months): 12m mean -1.10%, hit 39%. The gap vs signal (+3.82pp at 12m) is driven entirely by the 2020 episode.

### 3.2 2000-exclusion fragility test (§4.2) — PRIMARY KILL

Remove the 2020 COVID episode (the analog to the 2000 dot-com unwind in the ETF era):

| Horizon | n independent | Mean | Hit% |
|---------|--------------|------|------|
| 6m | 3 | -0.08% | 33% |
| 12m | 2 | -1.57% | 0% |
| 24m | 1 | -4.73% | 0% |
| 36m | 0 | — | — |

The entire positive signal in the ETF era is the 2020 COVID rotation. Removing it, the remaining observations (2024-06 and 2025-07) show RSP underperforming at every horizon. The hypothesis reduces to "this worked once during COVID" — not a repeatable signal.

The genuine 2000 dot-com unwind (the theoretical anchor) is outside the ETF window and cannot be tested. Whether it represents a repeatable mechanism remains an honest unknown.

### 3.3 "Stretched but kept stretching" stress case (§4.3)

First signal crossing in current regime: 2024-06 (rolling 36m = -13.73%).

| Statistic | Value |
|-----------|-------|
| Max relative drawdown | -8.2pp (2025-10, month 16 after entry) |
| Current P&L (2026-07, month 25) | -4.3pp |
| Months underwater | 17 of 26 |
| First positive month | Month 1 (+3.2%), brief |

The spread briefly surfaced in months 1-5 (+3.2% to +3.5%) then went persistently underwater from December 2024 as Mag-7 dominance resumed. Concentration continued stretching for 18 months after the first threshold crossing before showing any sign of reversal. The only entries showing positive returns in the sensitivity table are ones that entered at or near the concentration peak (Oct-Dec 2025), which are only identifiable in hindsight.

**§4.4 note (not built out — moot after §4.2 kill):** 12-month mandate exits at -2.2pp; 24-month mandate exits at -4.7pp.

Key sensitivity result from §4.3:

| Entry | Signal | Max DD | Current P&L | Mths UW |
|-------|--------|--------|-------------|---------|
| 2024-06 | -13.7% | -8.2pp | -4.3pp | 17/26 |
| 2025-02 | -13.5% | -8.7pp | -4.8pp | 15/18 |
| 2025-04 | -14.1% | -9.4pp | -5.6pp | 15/16 |
| 2025-05 | -16.3% | -7.7pp | -3.8pp | 13/15 |
| 2025-09 | -19.3% | -3.2pp | +0.9pp | 5/11 |
| 2025-10 | -23.0% | 0.0pp | +4.3pp | 0/10 |
| 2025-12 | -23.1% | -1.6pp | +2.2pp | 1/8 |

Every threshold-crossing entry (first signal) produced a loss. Only entries near the concentration peak produced gains, and those are identifiable only with hindsight. This table stays in the report as the primary illustration of the "right but early" cost.

---

## 4. Regime-Conditional Result (§4.5) — Separate Hypothesis

**This is not a rescue of Claim B. It is a different claim tested independently.**

Claim tested: "Buy breadth on confirmation, not concentration on level." Enter the RSP/SPY spread when concentration is extreme AND RSP is already outperforming SPY (breadth turning). Exit when breadth turns negative.

Breadth proxy: RSP/SPY monthly momentum (1-month and 3-month relative return). The regime ensemble signals (HMM/GMM/K-Means/Hamilton) are not available as monthly time series and were not used. This is a stated proxy limitation.

**Fixed-hold (12m), entry filter only:**
- 1m breadth filter: n_indep=2, mean=+3.27%, hit=50%
  - 2020-04: +7.46%
  - 2025-02: -0.92%
- 3m breadth filter: n_indep=2, mean=-0.11%, hit=50%
  - 2020-07: +6.48%
  - 2025-04: -6.70%

**Entry+exit on 1m breadth (continuous holding periods):**

| Entry | Exit | Months | Period return |
|-------|------|--------|---------------|
| 2025-11 | 2026-02 | 3 | +6.72% |
| 2026-06 | 2026-07 OPEN | 1 | +0.44% |

**Entry+exit on 3m breadth (continuous holding periods):**

| Entry | Exit | Months | Period return |
|-------|------|--------|---------------|
| 2025-04 | 2025-05 | 1 | -1.86% |
| 2026-02 | 2026-04 | 2 | -5.11% |

**REGIME-CONDITIONAL VERDICT: WEAK — n_indep=2 at best (12m fixed hold). Directionally positive (+3.27% mean) but sample too small to conclude. The entry+exit rule shows the breadth filter does sharpen entries in the live episode; it has not been tested over enough independent periods to call it signal.**

This requires its own forward accumulation. The current ETF-era sample has at most
2 independent observations under any breadth filter — insufficient to distinguish
signal from noise. The hypothesis ("breadth on confirmation") is alive but untested at
meaningful n. It must not be used to reopen Claim B.

---

## 5. §4.6 Multiple-Comparisons Haircut

| Rule | Configs |
|------|---------|
| §4.1 naive signal, 4 horizons | 4 |
| §4.1 control group, 4 horizons | 4 |
| §4.2A: 2020 signal removed, 4 horizons | 4 |
| §4.2B: 2020 window removed, 4 horizons | 4 |
| §4.3: 90th-pct entry sensitivity | 1 |
| §4.3: 95th-pct entry sensitivity | 1 |
| §4.3: 18-entry sensitivity sweep | 1 |
| §4.5A: conc + 1m breadth entry filter, 4 horizons | 4 |
| §4.5B: conc + 3m breadth entry filter, 4 horizons | 4 |
| §4.5C: conc + 1m breadth entry+exit | 1 |
| §4.5D: conc + 3m breadth entry+exit | 1 |
| **Total** | **29** |

Bonferroni threshold at alpha=0.05 across 29 configurations: p < 0.0017.
Maximum independent n across all sections: 4. No test in this analysis can approach
statistical significance at any reasonable threshold, let alone the deflated one.
All positive findings reported above are pre-deflation. The multiple-comparisons
adjustment does not change any verdict because the verdicts are driven by the
near-zero independent n, not by borderline p-values.

---

## 6. Verdict Block

**Claim A (concentration is extreme):** SUPPORTED within ETF era.
Rolling 36m RSP-minus-SPY at -14.40%, 7th percentile of 2006-2026 distribution.
Caveat: pre-2003 episodes not tested; "extreme vs ETF era" not "extreme vs full history."

**Claim B (equal-weight outperforms from concentration peaks):** KILLED.
Fails §4.2: entire positive signal traces to the 2020 COVID episode. Excluding it,
remaining independent observations at 12m: n=2, mean=-1.57%, hit=0%. The live current
episode (entry 2024-06) is 25 months in at -4.3pp with a -8.2pp max drawdown. Every
threshold-crossing entry in the current regime produced a loss.

**Regime-conditional (breadth-on-confirmation, §4.5):** WEAK — n_indep=2 at best (12m fixed hold).
A separate hypothesis; does not reopen Claim B. Requires forward accumulation to assess.

---

## 7. What Would Change the Verdict

**Pre-2003 data.** The 2000 dot-com episode is the theoretical anchor. If that episode
shows a repeatable concentration-mean-reversion mechanism rather than a one-off structural
shift, the ETF-era conclusion is incomplete. A full-history S&P 500 Equal Weight Index
total-return series (sourced from an index provider, not reconstructed) would allow a proper
§4.2 test on the genuine episode.

**Point-in-time constituent data.** The RSP/SPY spread conflates the concentration signal
with the equal-weight performance outcome. Direct measurement of top-10 weight percentage
(using a point-in-time constituent list, not current members applied historically) would
separate signal from outcome and allow a cleaner Claim A measurement independent of Claim B.

**A third ETF-era episode resolving.** Two concentration peaks in the ETF era (2020 and
2024-present). 2020 showed brief equal-weight outperformance; 2024-present is currently
underwater. A third episode at sufficient forward horizon would materially narrow the
confidence interval.

**Regime ensemble monthly signals.** The §4.5 test used RSP/SPY momentum as a breadth
proxy. The actual HMM/GMM/K-Means/Hamilton ensemble signals, if extracted as monthly series,
would allow a cleaner test of the "breadth on confirmation" hypothesis.

---

*Data sources: IBKR TWS port 7497, ADJUSTED_LAST, pull date 2026-07-01.*
*Script: concentration_s45_report.py*
*PEAD_ORDERS_ENABLED: False (unchanged; this report covers the concentration validation only).*
