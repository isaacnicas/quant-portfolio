# Tech/Semi Concentration Risk: Diagnostic
Date: 2026-07-15
Scope: read-only diagnostic. No code changes, no new mechanisms, no pre-registration.

## Correction to the task's stated universe

The task listed Trend's 7 instruments as "SPY, QQQ, IWM, XLK, EEM, SMH, XLE." Checked against `signal_engine.py`'s actual `UNIVERSE` dict: this is wrong on one ticker. **The real 7 equity instruments are SPY, QQQ, IWM, XLK, SMH, EEM, EWJ** (Japan equity ETF) — XLE is not in Trend's universe at all (it belongs to MeanReversion's universe instead, which may be the source of the mix-up). All analysis below uses the real universe (EWJ, not XLE).

## Method note

Trend's live state log (`trend_state.jsonl`) has only 7 records — far too thin for this analysis. Per-instrument daily weights were reconstructed by running `signal_engine.py`'s and `position_sizer.py`'s actual vectorized signal/regime/sizing math (imported directly, not reimplemented) across the full `data/prices.csv` history (752 days, 2023-07-17 to 2026-07-15), applying the tiered dead-band sequentially day-by-day exactly as `size_today_positions()` does. This requires ~260 days of warmup for the longest (252-day) trend horizon, so the usable reconstructed weight history is **492 days, 2024-07-29 to 2026-07-15**.

**Validated before use**: the reconstructed Trend daily return (yesterday's weight × today's instrument return, summed) was checked against the pre-existing, independently-built `docs/erc_validation_sleeve_returns.csv`'s `trend_return` column over their 473-day overlap: correlation 0.979, mean absolute difference 0.19%/day. Close enough to trust for this diagnostic.

## Step 1 — Tech/Semi Cluster Share of Trend's Gross Exposure

| | Value |
|---|---|
| Current (2026-07-15) | **43.8%** |
| Historical mean | 28.6% |
| Historical median | 26.3% |
| Historical min | 0.1% (2025-06-02) |
| Historical max | 61.3% (2025-10-23) |
| Current value's percentile in own history | 78th |

Quarterly mean tech share (QQQ+XLK+SMH ÷ total gross):

| Quarter | Tech Share |
|---|---|
| 2024 Q3 | 17.4% |
| 2024 Q4 | 29.7% |
| 2025 Q1 | 25.6% |
| 2025 Q2 | 2.7% |
| 2025 Q3 | 31.4% |
| 2025 Q4 | 49.9% |
| 2026 Q1 | 23.4% |
| 2026 Q2 | 42.1% |

**Current concentration is elevated (78th percentile) but not unprecedented** — the max (61.3%) is well above today's level, and the series has swung from near-zero to 61% and back multiple times in under two years (note the 2025 Q2 near-total absence, 2.7%, followed by a rebuild to 49.9% by Q4). This is not a flat, permanently-elevated line.

**Is this a signal effect or a structural one?** Checked directly, not asserted: individual mean weights across all 7 instruments are comparable (SPY 17.1%, QQQ 14.3%, IWM 12.3%, XLK 12.3%, SMH 14.7%, EEM 20.2%, EWJ 9.1% — EEM, not a tech name, has the *highest* average weight of any instrument). Mean weight *conditional on being active* is also unremarkable for the tech names (QQQ 16.2%, XLK 16.2%, SMH 15.2% vs SPY 17.9%, EEM 23.4%). **There is no evidence the sizing methodology structurally favors these 3 instruments** — no built-in weighting bias toward tech/semi exists in the code. The current elevated share is a **signal-driven, time-varying concentration**, not a structural feature of the universe or sizing method.

## Step 2 — Correlation Among the 7 Trend Instruments

Correlation matrix, trailing 63-day window ending 2026-07-15:

| | SPY | QQQ | IWM | XLK | SMH | EEM | EWJ |
|---|---|---|---|---|---|---|---|
| SPY | 1.000 | 0.916 | 0.788 | 0.840 | 0.777 | 0.826 | 0.774 |
| QQQ | 0.916 | 1.000 | 0.725 | 0.963 | 0.932 | 0.903 | 0.791 |
| IWM | 0.788 | 0.725 | 1.000 | 0.675 | 0.707 | 0.775 | 0.708 |
| XLK | 0.840 | 0.963 | 0.675 | 1.000 | 0.933 | 0.888 | 0.719 |
| SMH | 0.777 | 0.932 | 0.707 | 0.933 | 1.000 | 0.898 | 0.758 |
| EEM | 0.826 | 0.903 | 0.775 | 0.888 | 0.898 | 1.000 | 0.857 |
| EWJ | 0.774 | 0.791 | 0.708 | 0.719 | 0.758 | 0.857 | 1.000 |

**Tech/semi internal**: QQQ-XLK 0.963, QQQ-SMH 0.932, XLK-SMH 0.933 → mean **0.942**.
**Tech/semi to the other 4** (SPY, IWM, EEM, EWJ): mean **0.800** (per-instrument means: QQQ 0.834, XLK 0.781, SMH 0.785).
**Gap: 0.142.** The tech/semi cluster is a genuinely distinct, tightly-bound block, not just nominally "more correlated."

**Stability over time**: sampled the same gap monthly across the full 3-year history. Tech-internal correlation has been **persistently high throughout — it has never dropped below ~0.84** in any monthly sample (range 0.837–0.981), while the tech-to-other-4 correlation swings much more (0.50–0.88). First half vs. second half of history: tech-internal correlation is essentially unchanged (0.919 → 0.920), but **tech-to-other-4 correlation rose (0.638 → 0.740)** — meaning the diversification benefit of the *other 4* instruments has been eroding over time (the rest of the book becoming more correlated to tech), not that the tech cluster itself has tightened further. The persistently-high internal correlation is a structural, near-permanent feature of holding QQQ+XLK+SMH together (they are inherently overlapping products); the narrowing gap versus the rest of the book is the more novel, evolving part of the picture.

## Step 3 — Contribution to the 10 Worst Single-Day Portfolio Drawdowns

Source: the reconstructed Trend daily-return series (validated above) combined with MeanReversion/VRP returns from `erc_validation_sleeve_returns.csv` over their shared window, blended at the static ERC baseline (Trend 60% / MeanReversion 30% / VRP 10%). This 492-day window (2024-07-29 to 2026-07-15) was used rather than the longer 2019-2026 sleeve-return history, because it's the only window where Trend's *instrument-level* detail (needed for the tech3-vs-other4 split) is actually available — the tradeoff is fewer days but full internal decomposition on every one of them.

All figures are portfolio-level (ERC-weighted) contributions to that day's total return:

| Date | Portfolio Return | Trend Total | Trend Tech3 (QQQ+XLK+SMH) | Trend Other4 | Trend Diversifiers | MR | VRP |
|---|---|---|---|---|---|---|---|
| 2026-06-05 | -5.21% | -5.16% | -3.43% | -1.73% | 0.00% | +0.33% | -0.37% |
| 2026-03-03 | -3.75% | -3.36% | -0.55% | -2.18% | -0.63% | -0.19% | -0.20% |
| 2026-01-30 | -3.72% | -3.44% | -0.56% | -0.75% | -2.12% | -0.27% | -0.02% |
| 2024-12-18 | -3.66% | -2.95% | -0.80% | -1.79% | -0.36% | +0.15% | -0.87% |
| 2025-10-10 | -3.40% | -2.94% | -2.10% | -0.95% | +0.11% | +0.17% | -0.64% |
| 2024-09-03 | -3.24% | -2.20% | -1.17% | -0.91% | -0.13% | -0.02% | -1.01% |
| 2026-03-20 | -3.01% | -2.54% | -0.60% | -1.38% | -0.56% | -0.12% | -0.35% |
| 2026-03-26 | -2.57% | -2.40% | -0.95% | -0.87% | -0.57% | -0.17% | 0.00% |
| 2026-03-12 | -2.45% | -2.16% | -0.67% | -1.15% | -0.35% | -0.28% | 0.00% |
| 2025-11-13 | -2.38% | -1.95% | -1.30% | -0.63% | -0.02% | -0.11% | -0.32% |

**Summed across all 10 days**: Trend accounts for **87.2%** of total portfolio loss — disproportionately more than its 60% baseline weight, i.e. Trend's own losses are somewhat concentrated on the portfolio's worst days generally (a separate finding from the tech question). *Within* Trend's own loss: tech3 = 41.7%, other4 = 42.4%, diversifiers = 15.9%. Three instruments (tech3) contributing essentially as much as the other four combined is a real overweight relative to headcount (an even split would put tech3 at 3/7 ≈ 42.9% of the *equity-only* total — close to what's observed, so headcount-neutral there — but tech3's 41.7% share of Trend's *total* loss is well above its 28.6% average share of Trend's *gross exposure* from Step 1, meaning tech3 is disproportionately present specifically on bad days relative to its typical weight). **Tech3 alone accounts for 36.3% of total portfolio-level loss summed across the 10 worst days** — more than a third of all portfolio drawdown, from 3 of 12 total Trend instruments.

MR and VRP's contributions on these specific days are small and mixed in sign (MR sums to -0.5% net across all 10 days; VRP to -3.8%), versus Trend's -29.1%. These are Trend-driven bad days, not broad cross-sleeve crashes.

## Step 4 — Does MeanReversion Have the Same Problem?

**Actual universe** (`mean_reversion_strategy.py`, `UNIVERSE`, 22 tickers): JPM, GS, MS, XOM, CVX, KO, PEP, COST, HD, TGT, UNH, V, MA, QQQ, XLF, XLE, XLV, AAPL, MSFT, NVDA, JNJ, WMT.

**Tech-classified** (per the code's own `SECTOR_MAP`, restricted to names actually in `UNIVERSE`): **MSFT, AAPL, NVDA, QQQ — 4 of 22 (18.2%)**.

**Correlation structure is fundamentally different from Trend's.** Fetched 3 years of price history for the full 22-ticker universe and computed the same trailing-63-day check: MR's tech names' internal pairwise correlations are MSFT-AAPL 0.34, MSFT-NVDA 0.19, MSFT-QQQ 0.03, AAPL-NVDA 0.04, AAPL-QQQ 0.15, NVDA-QQQ 0.63 — **mean internal correlation 0.23**, versus Trend's tech cluster at **0.94**. MR's "tech cluster" is not a tight, single-moving block the way Trend's is; these are four largely idiosyncratic single-name/ETF exposures that happen to share a sector label.

**A structural safeguard already exists in MR that Trend has no equivalent of.** `MeanReversionStrategy.MAX_PER_SECTOR = 2`, actively enforced in `_sector_capped_picks()` (`mean_reversion_strategy.py:327-349`) — MR can never hold more than 2 simultaneous positions in any one `SECTOR_MAP` sector, including Technology, out of a maximum 10 concurrent equal-dollar slots (5 longs + 5 shorts). This hard-caps tech's maximum possible share of MR's book at 20% by construction. Trend's sizing has no analogous per-cluster cap.

**Does MR compound Trend's losses on the same bad days?** Using the Step 3 table directly: MR's contribution on Trend's 10 worst days sums to -0.51% (versus Trend's -29.1%), and is mixed in sign — positive (offsetting) on 4 of the 10 days, negative (compounding) but small on the other 6. There is no evidence of a consistent same-day compounding pattern. **MeanReversion does not have the same concentration problem, both structurally (sector cap, low internal correlation) and empirically (small, mixed-sign contribution on Trend's worst days).**

## Position

**Primary explanation: (b) signal-driven, and likely to rotate away over time** — with one structural caveat worth stating precisely rather than glossing over. The *weight concentration* itself (Step 1) is clearly signal-driven: individual instrument weights are unremarkable across the whole 7-name universe, and the tech share has swung between 0.1% and 61.3% within two years, currently sitting at an elevated-but-not-extreme 78th percentile. There is no evidence the sizing code favors these instruments; it's whatever the momentum signal currently says. That points toward rotation, not permanence.

The caveat: the *correlation structure* that makes this concentration matter (Step 2) — QQQ, XLK, and SMH's ~0.94 mean internal correlation — is structurally permanent, not signal-driven; these are inherently overlapping products and will be highly correlated whenever they're all meaningfully weighted, in any future episode of concentration, not just this one. So the risk isn't that *this specific* concentration is dangerous and unique — it's that *every* future concentration episode in this cluster will carry the same structurally-guaranteed correlation, and Step 3 shows this isn't hypothetical: tech3 already accounts for over a third of total portfolio loss across the 10 worst days on record. Cross-sleeve compounding (option c) is not supported by the evidence — MeanReversion's own tech exposure is both structurally capped and empirically uncorrelated with Trend's bad days. If a fix is ever considered, this points toward something that manages Trend's own within-sleeve cluster exposure specifically (the way MR's `MAX_PER_SECTOR` already does), rather than a cross-sleeve mechanism or a structural universe change — the concentration will recur because the signal will keep producing it from time to time, and each time it does, the correlation will be just as tight.
