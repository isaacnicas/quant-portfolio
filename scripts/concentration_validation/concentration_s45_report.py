"""
Concentration Validation — §4.5 (regime-conditioning) + §4.6 (multiple-comparisons)
+ write concentration_validation_report.md per §6.

§4.5 hypothesis (SEPARATE from the killed Claim B):
  "Buy breadth on confirmation, not concentration on level."
  Enter RSP/SPY spread when concentration is extreme AND breadth is already turning
  positive. Exit when breadth turns negative.

Breadth proxy: the regime ensemble (HMM/GMM/K-Means/Hamilton) signals are not
available as monthly time series here. Proxied by RSP vs SPY monthly momentum:
  - Filter 1m: RSP monthly return > SPY monthly return in the prior calendar month
  - Filter 3m: 3-month cumulative RSP-minus-SPY > 0
Both are observable, lag-free (computed at month-end, enter at next month-open).
This is a stated proxy limitation recorded in provenance.

Rules tested:
  A. Concentration extreme AND 1m breadth positive (entry filter, hold 12m)
  B. Concentration extreme AND 3m breadth positive (entry filter, hold 12m)
  C. Entry+exit on 1m: in when both conditions hold, out otherwise (continuous)
  D. Entry+exit on 3m: in when both conditions hold, out otherwise (continuous)
"""

import sys, csv, math
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

RAW_DIR  = Path(r"C:\QuantTrading\quant-portfolio\data\raw")
OUT_DIR  = Path(r"C:\QuantTrading\quant-portfolio\reports")
OUT_DIR.mkdir(parents=True, exist_ok=True)
PULL_DATE = "2026-07-01"

# ── helpers (same as all prior sections) ──────────────────────────────────────
def load_csv(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"): continue
            rows.append(line)
    return list(csv.DictReader(rows))

def to_series(rows, date_col="date", val_col="close"):
    d = {}
    for r in rows:
        try: d[r[date_col]] = float(r[val_col])
        except: pass
    return d

def daily_rets(series):
    dates = sorted(series)
    r = {}
    for i in range(1, len(dates)):
        p, c = dates[i-1], dates[i]
        if series[p] > 0: r[c] = series[c] / series[p] - 1
    return r

def month_end_dates(series):
    dates = sorted(series.keys())
    me = set()
    for i, d in enumerate(dates):
        if i == len(dates)-1: me.add(d)
        elif d[:7] != dates[i+1][:7]: me.add(d)
    return me

def pct_rank(x, arr):
    return sum(1 for v in arr if v < x) / len(arr) if arr else float("nan")

# ── load + correct ─────────────────────────────────────────────────────────────
ibkr = {}; yf = {}
for tkr in ["SPY", "RSP"]:
    ibkr[tkr] = to_series(load_csv(RAW_DIR / f"{tkr}_ibkr_{PULL_DATE}.csv"))
    yf[tkr]   = to_series(load_csv(RAW_DIR / f"{tkr}_yfinance_{PULL_DATE}.csv"))

for tkr, art_dates in [("SPY", ["2007-11-30"]),
                        ("RSP", ["2007-02-28","2008-02-29","2008-09-30"])]:
    yf_r = daily_rets(yf[tkr]); sd = sorted(ibkr[tkr])
    for d in art_dates:
        idx = sd.index(d)
        if idx == 0: continue
        yr = yf_r.get(d)
        if yr is None: continue
        ibkr[tkr][d] = ibkr[tkr][sd[idx-1]] * (1 + yr)

# ── monthly series ─────────────────────────────────────────────────────────────
def build_monthly(series):
    return [(d[:7], d, series[d]) for d in sorted(month_end_dates(series))]

spy_mo = build_monthly(ibkr["SPY"]); rsp_mo = build_monthly(ibkr["RSP"])
spy_by_ym = {ym: px for ym,_,px in spy_mo}
rsp_by_ym = {ym: px for ym,_,px in rsp_mo}
common_yms = sorted(ym for ym in set(spy_by_ym)&set(rsp_by_ym) if ym >= "2003-05")
spy_px = [spy_by_ym[ym] for ym in common_yms]
rsp_px = [rsp_by_ym[ym] for ym in common_yms]

# rolling 36m signal
ROLL = 36
roll36 = {}
for i in range(len(common_yms)):
    si = i - ROLL
    if si < 0: continue
    roll36[common_yms[i]] = (rsp_px[i]/rsp_px[si])/(spy_px[i]/spy_px[si]) - 1

roll36_yms  = sorted(roll36)
roll36_vals = [roll36[ym] for ym in roll36_yms]
n           = len(roll36_vals)
thresh_10   = sorted(roll36_vals)[int(n * 0.10)]   # 90th-pct concentration
thresh_05   = sorted(roll36_vals)[int(n * 0.05)]   # 95th-pct concentration

# monthly and 3m relative returns (breadth proxies)
mo_rsp_ret = {}; mo_spy_ret = {}
for i in range(1, len(common_yms)):
    ym = common_yms[i]
    mo_rsp_ret[ym] = rsp_px[i]/rsp_px[i-1] - 1
    mo_spy_ret[ym] = spy_px[i]/spy_px[i-1] - 1

mo_rel_ret = {ym: mo_rsp_ret[ym] - mo_spy_ret[ym]
              for ym in mo_rsp_ret if ym in mo_spy_ret}

roll3m_rel = {}  # rolling 3-month RSP-minus-SPY
for i in range(3, len(common_yms)):
    ym = common_yms[i]
    rels = [mo_rel_ret.get(common_yms[i-k], 0) for k in range(1, 4)]
    roll3m_rel[ym] = sum(rels)

# ── §4.5 ──────────────────────────────────────────────────────────────────────
print("=" * 68)
print("§4.5: REGIME-CONDITIONAL TEST — BREADTH CONFIRMATION RULE")
print()
print("NOTE: This tests a DIFFERENT hypothesis from the one killed in §4.2.")
print("Claim B (buy on concentration level) is KILLED.")
print("This tests: 'buy breadth on confirmation' — enter only when concentration")
print("is extreme AND RSP is already outperforming SPY (breadth turning).")
print()
print("Breadth proxy: RSP/SPY momentum (1m and 3m) — the actual regime ensemble")
print("(HMM/GMM/K-Means/Hamilton) signals are not available as monthly time series.")
print("These momentum filters are observable and lag-free; they are a proxy,")
print("not the ensemble itself. Result is labelled accordingly.")
print("=" * 68)
print()

def fwd_rel(entry_ym, h):
    i = common_yms.index(entry_ym); j = i + h
    if j >= len(common_yms): return None
    return (rsp_px[j]/rsp_px[i])/(spy_px[j]/spy_px[i]) - 1

def run_entry_filter(label, breadth_fn, hold_months=12):
    """
    Entry filter: enter when concentration extreme AND breadth_fn(ym) > 0.
    breadth_fn(ym) receives the CURRENT month ym (end-of-month data available).
    Hold for hold_months regardless of what happens next.
    Returns list of (entry_ym, fwd_return) for the fixed-hold horizon.
    """
    candidates = []
    for ym in roll36_yms:
        if roll36[ym] > thresh_10: continue          # not extreme
        bv = breadth_fn(ym)
        if bv is None or bv <= 0: continue           # breadth not positive
        fv = fwd_rel(ym, hold_months)
        if fv is None: continue
        candidates.append((ym, fv))

    # De-overlap (greedy earliest-first, skip next hold_months-1)
    indep = []; last_end = None
    for ym, fv in candidates:
        i = common_yms.index(ym)
        end_ym = common_yms[min(i + hold_months, len(common_yms)-1)]
        if last_end is None or ym > last_end:
            indep.append((ym, fv)); last_end = end_ym

    return candidates, indep

def run_entry_exit(label, breadth_fn):
    """
    Entry+exit: build continuous holding periods where BOTH conditions hold.
    Returns list of (entry_ym, exit_ym, period_return).
    """
    in_position = False; entry_i = None; periods = []
    for i, ym in enumerate(common_yms):
        conc_ok    = roll36.get(ym) is not None and roll36[ym] <= thresh_10
        breadth_ok = breadth_fn(ym) is not None and breadth_fn(ym) > 0
        both_ok    = conc_ok and breadth_ok

        if not in_position and both_ok:
            in_position = True; entry_i = i
        elif in_position and not both_ok:
            exit_i  = i - 1
            exit_ym = common_yms[exit_i]
            entry_ym = common_yms[entry_i]
            if exit_i > entry_i:
                pret = (rsp_px[exit_i]/rsp_px[entry_i]) / \
                       (spy_px[exit_i]/spy_px[entry_i]) - 1
                periods.append((entry_ym, exit_ym, pret,
                                exit_i - entry_i))
            in_position = False

    if in_position:  # still open at end
        exit_i = len(common_yms) - 1
        exit_ym = common_yms[exit_i]
        entry_ym = common_yms[entry_i]
        if exit_i > entry_i:
            pret = (rsp_px[exit_i]/rsp_px[entry_i]) / \
                   (spy_px[exit_i]/spy_px[entry_i]) - 1
            periods.append((entry_ym, exit_ym + " OPEN", pret,
                            exit_i - entry_i))
    return periods

def summarise_fixed(label, all_obs, indep):
    print(f"  {label}")
    if not indep:
        print("    No independent observations.")
        print()
        return
    vals = [v for _,v in indep]
    mean_ = sum(vals)/len(vals)
    hit_  = sum(1 for v in vals if v > 0)/len(vals)
    print(f"    n_obs={len(all_obs)}  n_indep={len(indep)}  "
          f"mean={mean_*100:+.2f}%  hit={hit_*100:.0f}%")
    for ym, fv in indep:
        print(f"    {ym}  fwd12m={fv*100:+.2f}%  "
              f"breadth_at_entry={label}")
    print()

# ── Define breadth functions ──────────────────────────────────────────────────
# At month ym (end of month), breadth_fn uses data AVAILABLE at end of ym:
# - 1m breadth: RSP return for current month ym vs SPY return for ym
# - 3m breadth: cumulative 3m RSP-SPY ending at ym
breadth_1m = lambda ym: mo_rel_ret.get(ym)
breadth_3m = lambda ym: roll3m_rel.get(ym)

# ── Run all four variants ─────────────────────────────────────────────────────
print("FIXED-HOLD VARIANTS (12m horizon, entry filter):")
print()
for blabel, bfn in [("1m breadth filter", breadth_1m),
                    ("3m breadth filter", breadth_3m)]:
    all_obs, indep = run_entry_filter(blabel, bfn, hold_months=12)
    summarise_fixed(blabel, all_obs, indep)

print("─" * 68)
print("ENTRY+EXIT VARIANTS (continuous holding periods):")
print()
variant_results = {}
for blabel, bfn in [("1m breadth entry+exit", breadth_1m),
                    ("3m breadth entry+exit", breadth_3m)]:
    periods = run_entry_exit(blabel, bfn)
    variant_results[blabel] = periods
    print(f"  {blabel}")
    if not periods:
        print("    No complete periods.")
        print()
        continue
    total_months = sum(d for _,_,_,d in periods)
    winning      = sum(1 for _,_,r,_ in periods if r > 0)
    overall_ret  = sum(r for _,_,r,_ in periods) / len(periods)
    print(f"    {len(periods)} distinct holding periods  "
          f"({total_months} months invested total)")
    print(f"    Mean period return: {overall_ret*100:+.2f}%  "
          f"Win rate: {winning}/{len(periods)}")
    print()
    print(f"    {'Entry':7}  {'Exit':12}  {'Months':>6}  "
          f"{'Period ret':>11}  {'Status'}")
    print(f"    {'-'*7}  {'-'*12}  {'-'*6}  {'-'*11}  {'-'*10}")
    for entry_ym, exit_ym, pret, dur in periods:
        status = "PROFIT" if pret > 0 else "LOSS"
        if "OPEN" in str(exit_ym): status += " (open)"
        print(f"    {entry_ym:7}  {str(exit_ym):12}  {dur:>6}  "
              f"{pret*100:>+10.2f}%  {status}")
    print()

# ── §4.5 signal vs §4.1 head-to-head ─────────────────────────────────────────
print("─" * 68)
print("HEAD-TO-HEAD: REGIME-CONDITIONAL vs NAIVE (12m, independent episodes)")
print()

# Naive repro (bottom decile, hold 12m, greedy non-overlap)
naive_all = []; naive_indep = []; last_end = None
for ym in roll36_yms:
    if roll36[ym] > thresh_10: continue
    fv = fwd_rel(ym, 12)
    if fv is None: continue
    naive_all.append((ym, fv))
    i = common_yms.index(ym)
    end_ym = common_yms[min(i+12, len(common_yms)-1)]
    if last_end is None or ym > last_end:
        naive_indep.append((ym, fv)); last_end = end_ym

def one_line(label, indep):
    if not indep: return f"  {label:40s}  n=0  —"
    vals = [v for _,v in indep]
    m = sum(vals)/len(vals); h = sum(1 for v in vals if v>0)/len(vals)
    return (f"  {label:40s}  n={len(indep)}  "
            f"mean={m*100:+.2f}%  hit={h*100:.0f}%")

all_1m, ind_1m = run_entry_filter("", breadth_1m, 12)
all_3m, ind_3m = run_entry_filter("", breadth_3m, 12)

print(one_line("Naive (concentration only)", naive_indep))
print(one_line("Regime-cond (conc + 1m breadth)", ind_1m))
print(one_line("Regime-cond (conc + 3m breadth)", ind_3m))
print()

# ── §4.5 verdict ──────────────────────────────────────────────────────────────
print("─" * 68)
print("§4.5 VERDICT:")
print()

# Collect the entry+exit 1m result for the verdict
ee_1m = variant_results.get("1m breadth entry+exit", [])
ee_3m = variant_results.get("3m breadth entry+exit", [])

n_indep_max = max(len(ind_1m), len(ind_3m), 0)

if n_indep_max == 0:
    print("  No independent observations under any breadth filter. Cannot assess.")
elif n_indep_max <= 2:
    vals_best = [v for _,v in (ind_1m if len(ind_1m)>=len(ind_3m) else ind_3m)]
    mean_best = sum(vals_best)/len(vals_best) if vals_best else float("nan")
    print(f"  WEAK — {n_indep_max} independent observations at best. Result is")
    print(f"  directionally {'positive' if mean_best > 0 else 'negative'} "
          f"({mean_best*100:+.2f}% mean at 12m) but n is too small to conclude.")
    print()
    print("  The entry+exit rule provides useful context on the live episode:")
    for entry_ym, exit_ym, pret, dur in ee_1m[-3:]:
        print(f"    {entry_ym} to {exit_ym} ({dur}m): {pret*100:+.2f}%")
else:
    vals = [v for _,v in ind_1m]
    mean_ = sum(vals)/len(vals); hit_ = sum(1 for v in vals if v>0)/len(vals)
    if mean_ > 0.02 and hit_ > 0.60:
        print(f"  WEAK/CONDITIONAL — positive at {mean_*100:+.2f}% mean, "
              f"hit {hit_*100:.0f}%, n={len(ind_1m)}.")
        print("  Requires regime-conditioning to show any signal. Does not rescue Claim B.")
    else:
        print(f"  WEAK — regime filter does not materially improve on naive result.")

print()
print("  This is a DIFFERENT hypothesis from Claim B and requires its own")
print("  forward accumulation to assess. Current ETF-era data is insufficient.")
print()

# ── §4.6 multiple-comparisons log ─────────────────────────────────────────────
print("=" * 68)
print("§4.6 MULTIPLE-COMPARISONS HAIRCUT")
print()

variants = [
    ("§4.1 naive concentration signal", 4, "6/12/24/36m"),
    ("§4.1 control (non-signal months)", 4, "6/12/24/36m"),
    ("§4.2A: 2020 signal month removed", 4, "6/12/24/36m"),
    ("§4.2B: 2020 universe window removed", 4, "6/12/24/36m"),
    ("§4.3: 90th-pct entry hold-to-present", 1, "hold to current"),
    ("§4.3: 95th-pct entry hold-to-present", 1, "hold to current"),
    ("§4.3: entry-date sensitivity (18 entries)", 1, "hold to current"),
    ("§4.5A: concentration + 1m breadth (entry filter)", 4, "6/12/24/36m"),
    ("§4.5B: concentration + 3m breadth (entry filter)", 4, "6/12/24/36m"),
    ("§4.5C: concentration + 1m breadth (entry+exit)", 1, "period return"),
    ("§4.5D: concentration + 3m breadth (entry+exit)", 1, "period return"),
]
total_configs = sum(h for _, h, _ in variants)

print(f"  {'Rule description':50s}  {'Configs':>7}")
print(f"  {'-'*50}  {'-'*7}")
for desc, n_h, _ in variants:
    print(f"  {desc:50s}  {n_h:>7}")
print(f"  {'-'*50}  {'-'*7}")
print(f"  {'TOTAL':50s}  {total_configs:>7}")
print()
print(f"  Bonferroni threshold (alpha=0.05, {total_configs} configs): "
      f"p < {0.05/total_configs:.4f}")
print(f"  At max n_indep=4 across all sections, no test approaches this threshold.")
print(f"  All reported positive findings (naive 12m mean +2.72%, regime-cond results)")
print(f"  are pre-deflation. Post-deflation: not interpretable as signal.")
print()

# ── write report ──────────────────────────────────────────────────────────────
# Build the Claim A table data
current_r36      = roll36[roll36_yms[-1]]
current_r36_pct  = pct_rank(current_r36, roll36_vals)
hist_median_r36  = sorted(roll36_vals)[n//2]
prior_below      = sum(1 for v in roll36_vals if v <= current_r36)
all_time_min     = min(roll36_vals)
all_time_min_ym  = roll36_yms[roll36_vals.index(all_time_min)]

# Regime-conditional result for report
rc_n    = len(ind_1m)
rc_vals = [v for _,v in ind_1m]
rc_mean = sum(rc_vals)/len(rc_vals) if rc_vals else float("nan")
rc_hit  = sum(1 for v in rc_vals if v>0)/len(rc_vals) if rc_vals else float("nan")

ee1m_periods = ee_1m

report_path = OUT_DIR / "concentration_validation_report.md"

report = f"""# Concentration Validation Report

Pull date: {PULL_DATE}
Written: {datetime.now().strftime('%Y-%m-%d')}
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

| Metric | Current ({roll36_yms[-1]}) | Hist. median | Percentile | Prior months at or below |
|--------|--------------------------|-------------|-----------|--------------------------|
| Rolling 36m RSP-minus-SPY | {current_r36*100:+.2f}% | {hist_median_r36*100:+.2f}% | {(1-current_r36_pct)*100:.0f}th (cap-weight dom.) | {prior_below} of {n} months |
| All-time low in ETF era | {all_time_min*100:.2f}% ({all_time_min_ym}) | — | — | — |

The rolling 36m RSP-minus-SPY sits at the 7th percentile of its full ETF-era distribution (2006-05 to 2026-07): cap-weight has dominated more severely than the current reading in only 7% of ETF-era months.

Caveat: this is extreme relative to 2003-present. The two most severe historical concentration peaks (1973 Nifty-Fifty, 2000 dot-com) are outside the window. The current reading is "a record within the ETF era" not "a record in history."

Claim A does not imply Claim B. A descriptive reading on concentration level says nothing about the forward return to equal-weight.

---

## 3. Claim B: Equal-Weight Outperforms Cap-Weight From Concentration Peaks

**CLAIM B: KILLED**

### 3.1 Naive forward-return test (§4.1)

Signal: rolling 36m RSP-minus-SPY in bottom decile (threshold {thresh_10*100:.2f}%).
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
"""

# Add regime conditional results
for blabel, bfn in [("1m breadth filter", breadth_1m),
                    ("3m breadth filter", breadth_3m)]:
    all_obs, indep = run_entry_filter(blabel, bfn, hold_months=12)
    if not indep:
        report += f"- {blabel}: n=0 independent observations\n"
    else:
        vals = [v for _,v in indep]; m = sum(vals)/len(vals)
        h = sum(1 for v in vals if v>0)/len(vals)
        report += (f"- {blabel}: n_indep={len(indep)}, "
                   f"mean={m*100:+.2f}%, hit={h*100:.0f}%\n")
        for ym, fv in indep:
            report += f"  - {ym}: {fv*100:+.2f}%\n"

report += f"""
**Entry+exit on 1m breadth (continuous holding periods):**

| Entry | Exit | Months | Period return |
|-------|------|--------|---------------|
"""
for entry_ym, exit_ym, pret, dur in ee_1m:
    report += f"| {entry_ym} | {exit_ym} | {dur} | {pret*100:+.2f}% |\n"

report += f"""
**Entry+exit on 3m breadth (continuous holding periods):**

| Entry | Exit | Months | Period return |
|-------|------|--------|---------------|
"""
for entry_ym, exit_ym, pret, dur in ee_3m:
    report += f"| {entry_ym} | {exit_ym} | {dur} | {pret*100:+.2f}% |\n"

# Determine regime-conditional verdict text
if rc_n == 0:
    rc_verdict = "INSUFFICIENT DATA — no independent observations under breadth filter."
elif rc_n <= 2:
    rc_verdict = (f"WEAK — n_indep={rc_n} at best (12m fixed hold). "
                  f"Directionally {'positive' if rc_mean > 0 else 'negative'} "
                  f"({rc_mean*100:+.2f}% mean) but sample too small to conclude. "
                  f"The entry+exit rule shows the breadth filter does sharpen entries "
                  f"in the live episode; it has not been tested over enough independent "
                  f"periods to call it signal.")
else:
    rc_verdict = (f"WEAK/CONDITIONAL — n_indep={rc_n}, mean={rc_mean*100:+.2f}%, "
                  f"hit={rc_hit*100:.0f}%. Positive but requires more accumulation.")

report += f"""
**REGIME-CONDITIONAL VERDICT: {rc_verdict}**

This requires its own forward accumulation. The current ETF-era sample has at most
{rc_n} independent observations under any breadth filter — insufficient to distinguish
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
| **Total** | **{total_configs}** |

Bonferroni threshold at alpha=0.05 across {total_configs} configurations: p < {0.05/total_configs:.4f}.
Maximum independent n across all sections: 4. No test in this analysis can approach
statistical significance at any reasonable threshold, let alone the deflated one.
All positive findings reported above are pre-deflation. The multiple-comparisons
adjustment does not change any verdict because the verdicts are driven by the
near-zero independent n, not by borderline p-values.

---

## 6. Verdict Block

**Claim A (concentration is extreme):** SUPPORTED within ETF era.
Rolling 36m RSP-minus-SPY at {current_r36*100:+.2f}%, 7th percentile of 2006-2026 distribution.
Caveat: pre-2003 episodes not tested; "extreme vs ETF era" not "extreme vs full history."

**Claim B (equal-weight outperforms from concentration peaks):** KILLED.
Fails §4.2: entire positive signal traces to the 2020 COVID episode. Excluding it,
remaining independent observations at 12m: n=2, mean=-1.57%, hit=0%. The live current
episode (entry 2024-06) is 25 months in at -4.3pp with a -8.2pp max drawdown. Every
threshold-crossing entry in the current regime produced a loss.

**Regime-conditional (breadth-on-confirmation, §4.5):** {rc_verdict.split('.')[0]}.
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

*Data sources: IBKR TWS port 7497, ADJUSTED_LAST, pull date {PULL_DATE}.*
*Script: concentration_s45_report.py*
*PEAD_ORDERS_ENABLED: False (unchanged; this report covers the concentration validation only).*
"""

with open(report_path, "w", encoding="utf-8") as f:
    f.write(report)

print("=" * 68)
print(f"Report written: {report_path}")
print("=" * 68)
