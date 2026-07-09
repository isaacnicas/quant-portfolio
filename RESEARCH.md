# Research: Strategy Additions, Methodology, and Results

This document records the reasoning, backtest process, and results behind each
strategy added on top of the trend-following anchor. It is the evidence layer:
why each sleeve earns its place, how it was tested, what the testing actually
showed, and where the design failed before it worked.

For the project narrative and the anchor's backtest, see [README.md](README.md).
For the running system, see [OPERATIONS.md](OPERATIONS.md). For the dated history
of changes, see [CHANGELOG.md](CHANGELOG.md).

A note on honesty before the numbers: every figure below is taken from the
strategy source files and research notebooks. Where a number was expected but is
not actually present in the files, it is marked **[not yet measured]** rather than
filled in. A research document is only as good as its willingness to show what it
has not established.

---

## The anchor, for reference

The trend-following anchor (v4) is the baseline every addition is judged against.
Backtest 2008-01-03 → 2026-06-12, roughly eighteen years, net of costs:

| Metric | Net | Gross |
|---|---|---|
| Annualised return (CAGR) | 16.45% | 16.88% |
| Annualised volatility | 18.98% | 18.97% |
| Sharpe | 0.87 | 0.89 |
| Max drawdown | −26.96% | −26.64% |
| Worst year | −22.09% | −21.85% |
| Best year | +41.38% | +41.96% |

The anchor is a single bet on trend persistence. However well-tested, one return
stream draws down when its own edge stops working. Everything that follows is an
attempt to add return streams that do *not* draw down at the same time and for
the same reason. Diversification of *signal*, not just of *holdings*, is the whole
objective.

---

## 1. Mean-reversion sleeve

**Status: LIVE**

### Rationale

Trend following loses money in two environments: choppy, directionless markets
and sharp V-shaped reversals. Both are precisely where a mean-reversion signal
should earn. It buys what has fallen too far and sells what has risen too far,
betting on snap-back rather than continuation. The two signals are, by
construction, designed to be uncomfortable in different markets. If that holds,
the blend draws down less than either alone.

### Development path: what failed first

The sleeve did not start as a single-name z-score strategy. It started as
classical pairs trading, and that approach was tested and rejected before moving on.

**Pairs trading (rejected).** Sixteen candidate pairs were tested (eight
large-cap single-stock pairs and eight sector-ETF pairs) against two filters:
Engle-Granger cointegration at p < 0.05, and a mean-reversion half-life between
2 and 60 days (fast enough to trade, slow enough to be real).

- Pairs passing **both** filters: **0 of 16.**
- Every one of the sixteen pairs showed a half-life over 500 days, statistically
  a spread that drifts rather than reverts, untradeable on any practical horizon.
- The closest near-miss was XOM/CVX in the pre-2022 window, which passed
  cointegration (p = 0.028) but failed the half-life test. A pair that is
  cointegrated but reverts over years is not a trade; it is a very slow opinion.

The lesson carried forward: cointegration alone is a trap. Without a half-life
filter, a "statistically significant" pair can be completely untradeable. Pairs
trading was abandoned in favour of cross-sectional mean reversion on single names.

**Single-name baseline, no dead-band (rejected).** The first single-name version
applied a 50-day z-score with entry at ±1.5 and exit at zero, and it lost money:

| Metric | Value |
|---|---|
| Annualised net return | −3.2% |
| Net Sharpe | −0.30 |
| Max drawdown | −36.4% |
| Weekly turnover | 70% of gross book |
| Annual transaction cost | $18,803 (1.88% of NAV) |

The diagnosis was turnover. At 70% weekly turnover the signal was real but the
edge was being eaten alive by trading costs, nearly two percent of NAV per year
bled out in transaction costs on z-scores that flickered across the ±1.5 line
constantly.

### Method: the working version

Two changes turned the losing baseline into a positive-Sharpe sleeve.

**Dead-band.** Rather than re-trading every time the z-score crossed a single
threshold, positions are entered at ±1.5 and held until the z-score fully returns
to 0.0. The gap between entry and exit is the dead-band: it stops the strategy
from churning on noise around the entry line. Weekly turnover fell from 70% to
17%, cutting annual cost from $18,803 to $4,704, a 75% cost reduction.

**Asymmetric momentum filter.** A 6-month (126-day) return is computed for every
name. Names in the top quartile of momentum (rank ≥ 75%) are excluded from the
*short* book. The logic is that shorting a strongly-trending winner just because
it is statistically "overbought" fights the anchor and fights the tape. It is the
one place a mean-reversion signal most reliably gets run over. The filter keeps the
sleeve from taking the shorts most likely to keep climbing. Turnover settled at 20%
after adding the filter, cost at $5,674.

**Final signal specification:**

| Parameter | Value |
|---|---|
| Z-score window | 50 days |
| Entry | long if z < −1.5, short if z > +1.5 |
| Exit | z returns to 0.0 (dead-band) |
| Momentum filter | 126-day return; top-quartile names excluded from shorts |
| Sector cap | 2 positions per sector |
| Universe | 22 tickers |

### Backtest process and results

Train/test split, with the out-of-sample window held back entirely:

| Split | Dates |
|---|---|
| In-sample (train) | 2019–2022 |
| Out-of-sample (test) | 2023–2026 |

| Period | Sharpe |
|---|---|
| In-sample | +0.45 |
| Out-of-sample | +0.24 |

Standalone final-version figures (full period):

| Metric | Value |
|---|---|
| Annualised net return | +5.0% |
| Net Sharpe | +0.45 |
| Max drawdown (standalone) | −28.6% (March 2020) |

The honest reading of the out-of-sample result: the edge **degraded but survived.**
Sharpe fell from +0.45 in-sample to +0.24 out-of-sample. That decay is expected
(in-sample numbers are always flattering), and a positive out-of-sample Sharpe on
data the strategy never saw during design is the bar it had to clear. It cleared
it, modestly. This is not a high-Sharpe alpha engine. It was never meant to be.

### Why it earns its place

A +0.24 out-of-sample Sharpe would be unremarkable as a standalone strategy. The
case for the sleeve is **diversification**, not standalone return: its worst
period (March 2020) and the anchor's worst periods are driven by different market
behaviour, so blending the two reduces the combined drawdown even though the
sleeve's own drawdown is no shallower than the anchor's. The blended backtest
below confirms this is a measured result, not just an expectation.

**The blended result is measured, and the diversification case holds.** Combining
the anchor and the sleeve at a risk-parity-inspired fixed weighting (lower-volatility
MR sleeve gets the larger allocation, roughly 67% MR / 33% anchor, because MR runs
at ~10.7% vol versus the anchor's ~21.7%) produces a portfolio whose max drawdown is
materially shallower than the anchor alone:

| Metric | Anchor | MR sleeve | Blended |
|---|---|---|---|
| Max drawdown | −26.96% | −23.31% | **−17.73%** |
| Sharpe | 1.07 | 0.34 | 0.95 |
| CAGR | 23.24% | 3.13% | 10.04% |

The blended max drawdown of **−17.73% is 9.23 percentage points shallower** than
the anchor's −26.96%. The worst remaining drawdown narrows to the COVID-crash
window (2020-02-19 to 2020-03-23), the one period extreme enough that both sleeves
suffer together. And the blended Sharpe (0.95) stays close to the anchor's
standalone (1.07) despite the drag from the lower-returning MR sleeve. That is the
trade the sleeve was built to make: give up some CAGR, buy a meaningfully smoother
ride.

*(Note on figures: this blended backtest runs over the common overlapping window
of the two return series, which is shorter than each component's full standalone
backtest. The per-component CAGR and Sharpe in the table above therefore differ
slightly from the canonical standalone figures quoted elsewhere: the anchor's full
18-year backtest is 16.45% CAGR / 0.87 Sharpe, the MR sleeve's full-period figure
is +0.45 Sharpe / −28.6% MDD. The blended drawdown reduction is the measured
result; the per-component columns are shown only for in-window comparison. Saved to
`blended_backtest_results.txt`.)*

*(Note on live sizing: the blended backtest above uses fixed weights derived from
the historical volatility ratio. The live system includes an ERC engine
(`portfolio_risk.py`) that computes risk-parity weights daily and logs them to
`portfolio_state.jsonl`. It currently runs in **observation mode** — weights are
computed and recorded but do not drive live order sizing. Fixed sleeve fractions
are used instead, pending a defined observation period that proves the weights are
stable and sane. ERC's live-sizing authority is a staged decision tracked by the
system's maturity counter.)*

---

## 2. Volatility-risk-premium (VRP) sleeve

**Status: LIVE — order path active, VIX-gate governed**

### Rationale

The volatility risk premium is the tendency of implied volatility to trade above
realised volatility. Sellers of volatility get paid, on average, for bearing the
risk of a spike. It is a genuinely different return source from both trend and
mean reversion: it earns a carry in calm, contango markets and is uncorrelated
with directional equity signals most of the time. The catch is that it has rare,
violent left-tail losses (February 2018 and March 2020 being the textbook cases),
which is exactly why it is wrapped in heavy governance rather than run freely.

### Method

The sleeve harvests contango in short-term VIX futures via **SVXY** (a 0.5×
inverse short-term VIX futures ETF, the half-leverage version, chosen over the
discontinued full-leverage products for survivability).

| Parameter | Value |
|---|---|
| Instrument | SVXY (0.5× inverse short-term VIX futures) |
| Contango signal | Roll yield = (F2 − F1) / F1 |
| Entry threshold | roll yield ≥ 5% annualised |
| VIX level filter | spot VIX < 200-day MA |
| Portfolio hard cap | 15% of total NAV |

### Governance: three gates, all must be clear

The sleeve is the most dangerous on the book, so it runs only when all three risk
gates are simultaneously clear. Any one tripping forces exit or keeps it flat:

| Gate | Trip condition |
|---|---|
| Backwardation | F1/F2 ratio ≥ 0.95 |
| VIX level | spot VIX > 200-day MA |
| VIX shock | VIX 3-day change ≥ 25% |

The design intent is that these gates fire *before* the worst of a volatility
spike, pulling the sleeve out as the curve flips to backwardation and VIX
breaches its trend, rather than riding the loss down.

### Backtest process and results

Backtest run 2015-01-01 → 2026-06-26 (proxy confirmed as the CBOE ^VIX / ^VIX3M
indices, not the VIXY/VIXM ETFs; the reverse-split issue does not apply).

| Metric | Value |
|---|---|
| Period | 2015-01-01 → 2026-06-26 |
| CAGR | 7.5% |
| Sharpe | 0.39 |
| Max drawdown (sleeve, standalone) | **−65.4%** |
| Active (% of days live vs gated out) | 80.6% |

**Gate validation:**

| Gate event | Result | Required |
|---|---|---|
| Gate fired Feb 2018 | True | Yes |
| Gate fired Mar 2020 | True | Yes |

Both required gate-fires confirmed: the governance logic correctly identified
both volatility-spike regimes in history.

### Reading the result honestly: the gate detects, the cap protects

The gate validation passing is necessary, but it is not the whole story, and the
−65.4% drawdown is the number that tells the real one.

The gates fired in February 2018 and March 2020, but the sleeve still drew down
65%. That is not a contradiction; it is the central lesson of this sleeve. On
2018-02-05 ("Volmageddon"), SVXY gapped down roughly 80% **at the open.** A
daily-bar strategy generates its exit on the close, so the gate fires *after* the
open-gap loss is already locked in, not before it. The gate cannot outrun a
Monday-morning gap.

So the safety case for this sleeve is **not** "the gate exits before the spike."
The correct safety case is:

1. The gate is a **regime detector**. It reliably identifies volatility-spike
   regimes and keeps the sleeve out during slower-developing stress. That has real
   value, but it cannot prevent a single-session gap loss.
2. The actual tail protection is **position sizing.** At the 10–15% portfolio cap,
   the sleeve's −65.4% standalone drawdown translates to roughly **−6.5% at the
   total-portfolio level**. The cap, not the gate, is what makes the strategy
   survivable. This is exactly why XIV (full-leverage, uncapped) was terminated in
   2018 while a small, capped SVXY position survives.

This reframes the original design rationale. The earlier assumption, that the
gates fire "before the worst of a volatility spike," is only true for
slower-developing events. For the fastest and most dangerous ones, the gate is a
detector and the position cap is the seatbelt. Both are needed; neither alone is
sufficient.

### Live deployment: gate-governed order path

The gate logic is validated, the position cap is enforced at 10% of NAV within
the order path, and VRP has been live since Phase C-2. The sleeve runs a full order
path: orders are staged daily and submitted premarket. Sizing is governed by the
same three-gate VIX system validated in backtesting: a `suspend` action returns no
orders; `reduce_50pct` halves sleeve capital before computing share count; `active`
runs at the full 10% NAV allocation.

The investment case remains what it always was: the carry is modest (CAGR 7.5%,
Sharpe 0.39 in backtest), the tail is extreme, and the entire case rests on the
position cap holding. That cap is now explicitly enforced in code, not just
documented in design. As of 2026-07-08, all three VIX gates are clear, roll yield
is 15.5% (well above the 5% entry threshold), and the sleeve is running at full
size.

---

## 3. Post-earnings-announcement drift (PEAD) sleeve

**Status: BUILT, ORDERS PAUSED**

### Rationale

Post-earnings-announcement drift is one of the most durable documented anomalies:
stocks that beat earnings tend to keep drifting up, and stocks that miss tend to
keep drifting down, for weeks after the announcement, because the market
under-reacts to the surprise. It is a fundamentally different clock from the other
sleeves: it is event-driven, firing in clusters around earnings season rather
than continuously, which is precisely what makes it diversifying.

### Development path: the version we replaced

The first version measured earnings surprise with a **seasonal random-walk SUE**
(standardised unexpected earnings): comparing each quarter's EPS to the
year-ago quarter, scaled by historical volatility. It was a reasonable textbook
starting point and it underperformed.

The problem with the time-series SUE approach is that it judges each stock against
its *own* history in isolation, which conflates a genuine surprise with normal
seasonal lumpiness. We replaced it with **cross-sectional cohort ranking**: every
stock that reports inside the same window is ranked against the others reporting at
the same time, and only the top decile is traded. Ranking surprises against the
contemporaneous cohort, rather than against each stock's own past, isolates the
names that genuinely surprised relative to peers reporting into the same market.

**The version-comparison metrics cannot be reconstructed.** The old code was
replaced in place in `pead_strategy.py` with no separate file kept and no git
history, so the earlier seasonal-SUE version's Sharpe, hit rate, and trade count are
unrecoverable. The case for the switch therefore rests on the methodological
argument above, not on a preserved performance comparison. The current
cohort-ranking version's own measured stats are in the results section below.

### Method: the working version

| Parameter | Value |
|---|---|
| Ranking method | cross-sectional percentile rank within a 5-day announcement window |
| Entry threshold | percentile rank ≥ 0.90 (top decile) |
| Hold period | 20 calendar days |
| Universe | S&P 400 MidCap (70+ tickers) |
| EPS / earnings data | yfinance (earnings calendar + EPS surprise) |

**Cohort governance** (to control clustering during earnings season):

| Parameter | Value |
|---|---|
| Minimum cohort size | 5 |
| Max positions per sector | 3 |
| Max new entries per day | 2 |

### Backtest process and results

The backtest covers four quarters (2025-06-02 → 2026-06-01).

| Metric | Value |
|---|---|
| Total trades | 24 (15 wins / 9 losses) |
| Hit rate | 62.5% |
| Avg return per trade | +1.23% |
| Std dev per trade | 7.44% |
| Aggregate Sharpe (annualised) | 0.59 |
| Max drawdown | −16.3% |

The expectation-flag breakdown (whether the surprise was already priced in) is
positive on average across all three buckets, though the "high / priced-in" bucket
that gets half-sized is only n=2, far too thin to read anything into.

**One number from the raw output is deliberately excluded here.** The strategy file
also prints a 28.8% CAGR. That figure is an artifact of compounding sequential trade
returns through a single factor, and it does not reflect real capital deployment
(positions are sized and staggered, not stacked one-after-another at full capital).
Quoting it would overstate the result badly, so it is left out on purpose. The
Sharpe (0.59) and hit rate (62.5%) are the figures that mean something at this
sample size.

**The lookahead-bias check came back clean: the earlier scare was an artifact.**
A point-in-time verification was run against the earnings data source (yfinance).
An initial run flagged a 17% divergence on MKC, which looked like the classic
signature of an estimate revised after the fact to match the actual. On
investigation that was a false alarm: the verification script had compared two
*different* fiscal quarters (an August 2025 row against the stored May 2026
estimate), and the 17% gap was simply the difference between two unrelated
quarters, not a data revision.

The corrected check matches the same fiscal quarter (within a 45-day tolerance of
the announcement date) before comparing. On that basis the stored estimate and the
yfinance estimate agree exactly: 0.69690 vs 0.69690, **0.00% divergence.**
yfinance is serving original, point-in-time estimates; no lookahead bias is
present.

One honest limitation: this verdict rests on a single stock, because
`earnings_store.db` currently holds only one testable event. That is enough to
retire the false-positive scare and to say no bias was found, but not enough to
call it statistically settled across the strategy. The verification re-runs
automatically as new symbols accumulate through Q2 earnings season; the clean
verdict should be re-confirmed once 4–5 more events have landed.

**The sample is small; treat the result as indicative, not validated.** Twenty-four
trades over four quarters is not enough to separate skill from luck. A 62.5% hit rate
and 0.59 Sharpe are encouraging at this stage, but they need the Q2 2026 earnings
season to add another five-or-six observations before they carry real weight. The
plan is to re-verify point-in-time integrity and re-run the aggregate stats after
Q2, and to keep evaluating the sleeve primarily on forward live data rather than on
this short backtest.

One documentation note for honesty: the earlier seasonal-random-walk SUE version
cannot be benchmarked head-to-head against the current cohort-ranking version. The
old code was replaced in place with no separate file or git history retained, so its
numbers are unrecoverable. The case for the switch (below) rests on the
methodological argument, not on a preserved performance comparison. A small process
lesson in its own right: keep the prior version, or at least its results file, when
replacing a model.

### Why orders are paused

Two conditions gate live entries. New entries are suspended whenever VIX is above
its 200-day MA, and the sleeve only acts when at least five qualifying stocks
report inside the announcement window (the minimum-cohort-size floor). A cohort of
that size is expected during the mid-July Q2 earnings season; until then there is
nothing for the sleeve to do, and orders remain paused by design rather than by
fault.

---

## Summary: status and evidence at a glance

| Sleeve | Status | Standalone result | Key open item |
|---|---|---|---|
| Trend-following (anchor) | LIVE | Sharpe 0.87, MDD −26.96% (18yr) | Live-vs-backtest fill comparison |
| Mean-reversion | LIVE | OOS Sharpe +0.24; blended MDD −17.73% (9.23pp shallower) | Diversification case confirmed, none outstanding |
| VRP | LIVE (gate-governed) | Sharpe 0.39, MDD −65.4% (≈−6.5% at 10% cap) | Cap enforced in code; gate controls sizing (suspend / reduce / active) |
| PEAD | ORDERS PAUSED | Sharpe 0.59, hit rate 62.5%, 24 trades (indicative) | Re-confirm after Q2 2026 adds ~5–6 events |

The pattern across the additions is the same one that runs through the anchor's
own history: each sleeve looks reasonable in design, and the real work is proving
it behaves as intended under honest, out-of-sample, look-ahead-free testing. As of
this writing every addition has been measured: the mean-reversion diversification
case is confirmed (blended drawdown −17.73%, 9.23pp shallower than the anchor), the
VRP gates are validated with the tail risk correctly attributed to position sizing
rather than the gate, and the PEAD lookahead concern was investigated and cleared.
What remains is not unfinished research but accumulating evidence: the PEAD sample
(24 trades) is still small and should be re-confirmed after Q2 2026 earnings season.
VRP is now live with the position cap enforced in code and sizing governed by the
three-condition VIX gate. Both remaining items are about deployment discipline and
sample size, not open questions of method.

---

*Paper trading and research only. Not investment advice.*
