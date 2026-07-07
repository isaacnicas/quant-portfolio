# CONCENTRATION_VALIDATION_SPEC.md

**Purpose:** Validate or kill the "concentration-gap" hypothesis — that extreme cap-weight/equal-weight divergence in the US large-cap index is a tradeable signal favouring equal-weight (breadth) from here.

**Governing principle:** This spec is designed to *falsify*, not confirm. The default posture is skepticism. A result that looks impressive is a reason to distrust the test design, not to size up. If the hypothesis survives every kill-test below, it is *weakly* supported. If it fails any structural one, it is dead for discretionary sizing.

**Author's warning to the executor (read first):** The modern US data contains only ~3 genuine concentration peaks (approx. 1973 Nifty-Fifty, 2000 dot-com, 2023–present). Any "buy equal-weight after concentration peaks" backtest is effectively n=3 and will be dominated by whether the 2000 episode sits in the window. Treat every performance statistic accordingly. Do not report a Sharpe ratio for the peak-conditional trade without also reporting how many distinct episodes drive it. A confidence interval on n=3 is theatre.

---

## 0. Two claims — keep them separate at all times

Do **not** let these merge in any output. They have very different evidentiary support.

- **Claim A — "Concentration is historically extreme."** Well-supported, low controversy. Descriptive. Testable with current-vs-history percentile.
- **Claim B — "Therefore equal-weight outperforms cap-weight from here on a tradeable (6–36 month) horizon."** Weakly supported, catalyst-dependent, and has been *wrong every year 2023–2025*. This is the claim that matters for capital and the one most likely to be false.

Every conclusion must state which claim it addresses. A finding for A is not evidence for B.

---

## 1. Data acquisition (IBKR via existing Gateway on 4002)

### 1.1 Core series (blocking — do these first)
Via `reqHistoricalData` through the running IB Gateway:
- **SPY** (cap-weight proxy), daily TRADES bars, `durationStr` back to RSP inception, `whatToShow=TRADES`, `useRTH=1`.
- **RSP** (equal-weight proxy), daily, same params. RSP inception ~2003-04-24 — this bounds the clean ETF sample.
- Prefer **total-return** series if your subscriptions expose them (adjusted for dividends). If only price bars are available, pull dividends separately and build TR yourself — the equal-weight vs cap-weight dividend yield differs enough (~0.3–0.5%/yr) to matter over long holds. **Document which you used.** A price-return-only backtest understates equal-weight (it yields more) — note the direction of the bias.

### 1.2 Longer history (non-blocking, high value)
The ETF era (2003+) misses the two most informative episodes. To get 1973 and the full 2000 cycle you need index-level total-return data, which IBKR will not serve. Options, in order of preference:
- S&P 500 Equal Weight Index total return vs S&P 500 TR — source from a data vendor CSV if available; otherwise flag as a gap.
- **Do NOT** hardcode remembered index levels to fill this. A fabricated long series is worse than an honest short one. If you cannot source it cleanly, state "pre-2003 untested" and move on.

### 1.3 Concentration series (non-blocking)
Top-10 (and top-1, top-5) share of total index weight, monthly. IBKR does not serve this.
- Preferred: reconstruct from constituent market caps if you have a point-in-time constituent list (watch survivorship bias — a *current* constituent list applied historically is look-ahead and will corrupt this; use a point-in-time membership source or don't compute it).
- Fallback: source top-10-weight history from a published series and cite it. Mark as external.

### 1.4 Breadth series (non-blocking)
% of index constituents above their own 200-day MA, daily/weekly.
- Reconstruct bottom-up: pull all current+historical constituents' daily bars, compute 200-day MA, take the cross-sectional %.
- **Survivorship warning:** using only *surviving* constituents inflates historical breadth (dead companies were often the weak ones). Use point-in-time membership or explicitly caveat.
- **IBKR pacing:** ≤ ~60 historical requests per 10-min rolling window. ~500 constituents ⇒ build a queue with sleep/backoff. Persist each pull to disk (`data/constituents/{ticker}.parquet`) so the job is resumable and you never re-pull. Log every request timestamp.

### 1.5 Data integrity gates (fail loudly)
- Assert no duplicate dates, monotonic index, no all-zero/forward-filled gaps > 3 trading days without flagging.
- Cross-check RSP/SPY total-return CAGR over the full window against a published figure (within ~0.3%). If it doesn't reconcile, stop — the pull is wrong.
- Store raw pulls immutably; do all transforms on copies. Record the pull date (data as of) in every output file header.

---

## 2. Construct the signal

- **Spread series:** cumulative and rolling relative return, `RSP_TR / SPY_TR`. Report rolling 3-year relative return (this is the series the research cites: cap-weight beat equal-weight by ~32% over 3yr, an alleged record).
- **Valuation gap:** if you can get forward or trailing P/E for both indices, compute the premium (cap-weight P/E ÷ equal-weight P/E). Research claims ~30% now vs ~13% pre-COVID. Verify or refute.
- **Concentration z-score / percentile** of top-10 weight vs its own history.
- Everything monthly for signal work; keep daily for execution realism later.

---

## 3. Claim A test (descriptive — expected to pass)

Report current readings as percentiles of full available history:
- Top-10 weight percentile.
- Cap/equal valuation-gap percentile.
- Rolling 3yr relative return percentile (how extreme is the current cap-weight dominance).

Output a single table: metric | current | historical median | percentile | prior instances above this level (with dates). If current readings are >95th percentile, Claim A is supported. **This says nothing about B.**

---

## 4. Claim B tests (the real work — designed to kill)

### 4.1 Naïve conditional-forward-return test
For each month, bucket by concentration/valuation-gap decile (or simply "extreme" vs "not"). Compute forward RSP-minus-SPY total return at 6/12/24/36m horizons. Report mean, median, hit-rate, min, max **and n distinct non-overlapping episodes** per bucket.
- **Overlap correction:** 36m forward windows on monthly data are ~97% autocorrelated. Do NOT treat 300 overlapping monthly observations as 300 independent trials. Report block-bootstrap CIs with block length ≥ horizon, and separately report the count of *independent* episodes. If independent n < 5, say so in bold next to the result.

### 4.2 The 2000-exclusion fragility test (mandatory)
Re-run 4.1 with the 1998–2003 window removed entirely. If the entire edge disappears, the hypothesis is "the dot-com unwind happened once" — not a repeatable signal. Report both versions side by side. **This is the single most important test in the spec.**

### 4.3 The 2023–2025 "stretched but kept stretching" stress case (mandatory)
Concentration was already extreme by early 2023 and got *more* extreme for three years while equal-weight underperformed by ~32%. Any signal that would have flipped to equal-weight in 2023 got run over. Explicitly compute: if you had gone equal-weight the first month concentration crossed the 90th/95th percentile, what was the drawdown and time-underwater before any payoff? This quantifies the "right but early" cost — the core risk. Report max relative drawdown and months-underwater.

### 4.4 Persistence / early-exit realism
The signal has no known catalyst. Test whether a naïve "hold equal-weight while concentration > threshold" rule survives realistic patience limits: what if the mandate forces exit after 12/24 months of underperformance? Show how sensitive the result is to how long you can stay wrong. If it only works for someone who can hold 5+ years through -30% relative DD, say that plainly — it changes who the trade is for.

### 4.5 Regime conditioning (leverages existing tooling)
Feed the existing regime-detection ensemble (Hamilton/HMM/K-Means/GMM). Test whether conditioning the equal-weight tilt on regime state (e.g. only when breadth is *already* improving, not merely when concentration is stretched) improves the risk-adjusted result vs the unconditional version. Hypothesis to test: concentration level is a *valuation* signal (says nothing about timing); breadth turning is the *catalyst* signal. If regime-conditioning materially beats level-only, that's the actual finding — buy breadth on confirmation, not concentration on level.

### 4.6 Multiple-comparisons honesty
Log every threshold, horizon, and rule variant tried. Report how many configurations were tested. If you tried 40 variants and 3 look great, that's noise-mining — apply a deflated-Sharpe / Bonferroni-style haircut and report the adjusted result, not the cherry-picked best.

---

## 5. Simulation (only if §4 doesn't kill it)

- Walk-forward, no look-ahead: signal at month t from data through t-1 only; execute at t+1 open.
- Costs: RSP/SPY spreads + commissions + RSP's higher turnover drag (quarterly rebalance ~14% one-way historically) + the ~10–17bp fee gap. Equal-weight's real-world implementation cost is a genuine drag — do not omit it.
- Report net-of-cost, and report the trade *as a spread* (long RSP / short SPY) as well as long-only tilt, since the pure hypothesis is relative.
- Stress: bootstrap block-resample returns; report distribution of outcomes, not a single equity curve. Show the 5th percentile path, not just the median.

---

## 6. Output / verdict format

Produce `concentration_validation_report.md` with, in order:
1. Data provenance block (sources, pull date, TR vs PR, survivorship treatment, known gaps).
2. Claim A verdict (one line + table).
3. Claim B verdict — must take the form:
   - Naïve result, then result after each kill-test (4.2, 4.3, 4.4).
   - Independent-episode count.
   - **VERDICT line**, one of:
     - `KILLED` — edge vanishes under 4.2 or requires implausible patience under 4.4.
     - `WEAK/CONDITIONAL` — survives only when regime-conditioned (4.5); state the exact condition.
     - `SURVIVES` — persists after 2000-exclusion, realistic patience, and costs, with independent n stated. (Prior: unlikely. If you get here, re-audit for look-ahead before believing it.)
4. What would change the verdict (the specific data that's missing — pre-2003 episodes, point-in-time constituents).

**Style:** match the operator's dislikes — no em-dash overuse, no "this isn't X, it's Y" antithesis, no salesman lines. Report numbers, state the verdict, note the caveat. If it's dead, say it's dead in the first sentence of the verdict.

---

## 7. Explicit non-goals / guardrails
- No hardcoded/remembered price series. Real pulls or an honest gap.
- No survivorship-contaminated breadth presented without the caveat.
- No overlapping-window statistics presented as independent.
- No single hero equity curve. Distributions or nothing.
- Do not conclude B from A. Ever.
- The trade is a factor rotation with an unknown catalyst. Even `SURVIVES` does not imply "act now" — it implies "this is a real edge whose timing you still cannot call," which points back to regime-detection for entry, not a static allocation today.
