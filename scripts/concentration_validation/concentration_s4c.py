"""
Concentration Validation — §4.3: "Stretched but kept stretching" stress case.

Spec: if you had gone equal-weight (long RSP / short SPY) the first month
concentration crossed the 90th/95th percentile, what was the drawdown and
time-underwater? This quantifies the "right but early" cost.

We use the rolling 36m RSP-minus-SPY as the concentration proxy.
  90th-pct concentration = series at 10th pct of its distribution (bottom decile)
  95th-pct concentration = series at  5th pct of its distribution (bottom 5%)

For the current regime we identify the first crossing AFTER 2022-01 to
avoid conflating with the 2020 COVID episode.

Reports:
  - Entry date at each threshold
  - Month-by-month relative P&L from entry to present
  - Max relative drawdown (from entry), and when it occurred
  - Months underwater (cumulative spread < 0 since entry)
  - Current cumulative spread
  - Sensitivity: does using a tighter threshold (95th pct) meaningfully change results?
"""

import sys, csv, math
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

RAW_DIR   = Path(r"C:\QuantTrading\quant-portfolio\data\raw")
PULL_DATE = "2026-07-01"

# ── helpers (identical to prior sections) ─────────────────────────────────────
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
        elif (dates[i+1][:7]) != d[:7]: me.add(d)
    return me

# ── load & correct (identical to prior sections) ──────────────────────────────
ibkr = {}; yf = {}
for tkr in ["SPY", "RSP"]:
    ibkr[tkr] = to_series(load_csv(RAW_DIR / f"{tkr}_ibkr_{PULL_DATE}.csv"))
    yf[tkr]   = to_series(load_csv(RAW_DIR / f"{tkr}_yfinance_{PULL_DATE}.csv"))

CORRECTIONS = {
    "SPY": ["2007-11-30"],
    "RSP": ["2007-02-28", "2008-02-29", "2008-09-30"],
}
for tkr, art_dates in CORRECTIONS.items():
    yf_r     = daily_rets(yf[tkr])
    sorted_d = sorted(ibkr[tkr].keys())
    for art_date in art_dates:
        idx = sorted_d.index(art_date)
        if idx == 0: continue
        yf_ret = yf_r.get(art_date)
        if yf_ret is None: continue
        ibkr[tkr][art_date] = ibkr[tkr][sorted_d[idx-1]] * (1 + yf_ret)

# ── monthly series ─────────────────────────────────────────────────────────────
def build_monthly(series):
    me = sorted(month_end_dates(series))
    return [(d[:7], d, series[d]) for d in me]

spy_mo = build_monthly(ibkr["SPY"])
rsp_mo = build_monthly(ibkr["RSP"])
spy_by_ym = {ym: px for ym, _, px in spy_mo}
rsp_by_ym = {ym: px for ym, _, px in rsp_mo}

common_yms = sorted(set(spy_by_ym) & set(rsp_by_ym))
common_yms = [ym for ym in common_yms if ym >= "2003-05"]

spy_px = [spy_by_ym[ym] for ym in common_yms]
rsp_px = [rsp_by_ym[ym] for ym in common_yms]

# ── rolling 36m signal ────────────────────────────────────────────────────────
ROLL = 36
roll36 = {}
for i in range(len(common_yms)):
    si = i - ROLL
    if si < 0: continue
    roll36[common_yms[i]] = (rsp_px[i]/rsp_px[si]) / (spy_px[i]/spy_px[si]) - 1

roll36_yms  = sorted(roll36)
roll36_vals = [roll36[ym] for ym in roll36_yms]

# ── percentile thresholds ─────────────────────────────────────────────────────
sorted_vals = sorted(roll36_vals)
n = len(sorted_vals)
thresh_10 = sorted_vals[int(n * 0.10)]   # 90th-pct concentration
thresh_05 = sorted_vals[int(n * 0.05)]   # 95th-pct concentration

print("=" * 68)
print("§4.3: 'STRETCHED BUT KEPT STRETCHING' — ENTRY DRAWDOWN STRESS TEST")
print("=" * 68)
print()
print(f"Rolling 36m RSP-minus-SPY: {len(roll36_yms)} monthly observations "
      f"({roll36_yms[0]} to {roll36_yms[-1]})")
print(f"Distribution:  min={min(roll36_vals)*100:.2f}%  "
      f"p5={thresh_05*100:.2f}%  p10={thresh_10*100:.2f}%  "
      f"median={sorted_vals[n//2]*100:.2f}%  max={max(roll36_vals)*100:.2f}%")
print()
print(f"Signal thresholds:")
print(f"  90th-pct concentration (10th pct of series): {thresh_10*100:.2f}%")
print(f"  95th-pct concentration ( 5th pct of series): {thresh_05*100:.2f}%")
print()

# ── find first crossing in CURRENT regime (post-2022) ─────────────────────────
CURRENT_REGIME_START = "2022-01"

def first_crossing(threshold, after_ym):
    for ym in roll36_yms:
        if ym >= after_ym and roll36[ym] <= threshold:
            return ym
    return None

entry_90 = first_crossing(thresh_10, CURRENT_REGIME_START)
entry_95 = first_crossing(thresh_05, CURRENT_REGIME_START)

print(f"Current regime first crossings (post-{CURRENT_REGIME_START}):")
print(f"  90th-pct threshold ({thresh_10*100:.2f}%): "
      f"{'NOT CROSSED YET' if not entry_90 else entry_90}")
print(f"  95th-pct threshold ({thresh_05*100:.2f}%): "
      f"{'NOT CROSSED YET' if not entry_95 else entry_95}")
print()

# ── stress-test function ──────────────────────────────────────────────────────
def stress_test(label, entry_ym):
    if entry_ym is None:
        print(f"  {label}: no crossing — threshold never reached in current regime")
        return

    entry_i = common_yms.index(entry_ym)

    # Build month-by-month relative P&L from entry
    months_out = []
    for j in range(entry_i, len(common_yms)):
        ym   = common_yms[j]
        mths = j - entry_i
        r    = rsp_px[j] / rsp_px[entry_i]
        s    = spy_px[j] / spy_px[entry_i]
        cum_rel = r / s - 1
        months_out.append({
            "ym": ym, "mths": mths, "cum_rel": cum_rel,
            "roll36": roll36.get(ym),
        })

    # Stats
    cum_rels   = [m["cum_rel"] for m in months_out]
    max_dd     = min(cum_rels)
    max_dd_ym  = months_out[cum_rels.index(max_dd)]["ym"]
    max_dd_mth = months_out[cum_rels.index(max_dd)]["mths"]
    current    = cum_rels[-1]
    current_ym = months_out[-1]["ym"]
    n_uw       = sum(1 for v in cum_rels if v < 0)
    n_total    = len(cum_rels)

    # First time cumulative spread turned positive (if ever)
    first_pos_mth = None
    for m in months_out:
        if m["cum_rel"] > 0:
            first_pos_mth = m["mths"]
            break

    print(f"─" * 68)
    print(f"§4.3 SCENARIO: {label}")
    print(f"  Entry:       {entry_ym}  "
          f"(signal = {roll36[entry_ym]*100:.2f}% rolling 36m RSP-SPY)")
    print(f"  Current:     {current_ym}  "
          f"({n_total-1} months later)")
    print()
    print(f"  Max relative drawdown: {max_dd*100:.2f}%  "
          f"(reached {max_dd_ym}, month {max_dd_mth} after entry)")
    print(f"  Current P&L:           {current*100:+.2f}%")
    print(f"  Months underwater:     {n_uw} of {n_total} "
          f"({'never surfaced' if first_pos_mth is None else f'first positive: month {first_pos_mth}'})")
    print()

    # Print month-by-month table (annual frequency + all months for last 2yr)
    print(f"  Month-by-month (annual + last 24 months):")
    print(f"  {'Month':7}  {'Mths out':>8}  {'Cum RSP-SPY':>12}  "
          f"{'Roll36m':>9}  {'Status'}")
    print(f"  {'-'*7}  {'-'*8}  {'-'*12}  {'-'*9}  {'-'*12}")

    # Annual subset + last 24 months
    annual_idxs = set()
    last_ym_of_each_yr = {}
    for m in months_out:
        yr = m["ym"][:4]
        last_ym_of_each_yr[yr] = m   # last encountered = last month of year in data
    annual_idxs = {id(m) for m in last_ym_of_each_yr.values()}

    cutoff_24m = months_out[-25]["ym"] if len(months_out) > 25 else months_out[0]["ym"]

    shown = set()
    for m in months_out:
        show = id(m) in annual_idxs or m["ym"] >= cutoff_24m
        if not show: continue
        if id(m) in shown: continue
        shown.add(id(m))
        r36_str = f"{m['roll36']*100:+.2f}%" if m["roll36"] is not None else "  N/A  "
        status = "UNDERWATER" if m["cum_rel"] < 0 else "above water"
        if m == months_out[-1]: status += " ← current"
        print(f"  {m['ym']:7}  {m['mths']:>8}  "
              f"{m['cum_rel']*100:>+11.2f}%  {r36_str:>9}  {status}")

    print()

    # Worst-case framing
    print(f"  FRAMING: An investor who went long RSP / short SPY at {entry_ym}")
    if max_dd < -0.05:
        print(f"  faced a max relative drawdown of {max_dd*100:.1f}% — meaning if they")
        print(f"  were running a 100% net long equal-weight vs cap-weight spread,")
        print(f"  the spread alone cost {abs(max_dd)*100:.1f}pp at its worst point")
        print(f"  ({max_dd_ym}, {max_dd_mth} months after entry).")
    else:
        print(f"  faced a max relative drawdown of {max_dd*100:.1f}%.")
    if first_pos_mth is None:
        print(f"  As of {current_ym} the spread has NEVER turned positive.")
        print(f"  The trade is currently {abs(current)*100:.1f}pp underwater.")
    else:
        print(f"  The spread first turned positive at month {first_pos_mth}.")
    print()

stress_test("90th-pct CONCENTRATION ENTRY", entry_90)
stress_test("95th-pct CONCENTRATION ENTRY", entry_95)

# ── Rolling-forward entry sensitivity ─────────────────────────────────────────
print("─" * 68)
print("ENTRY-DATE SENSITIVITY: all possible current-regime entry months")
print("(any month since 2022-01 where signal was in bottom decile)")
print()

signal_since_2022 = [ym for ym in roll36_yms
                     if ym >= CURRENT_REGIME_START and roll36[ym] <= thresh_10]

if not signal_since_2022:
    print("  No signal months since 2022. (Threshold not yet reached.)")
else:
    print(f"  Signal months since 2022: {len(signal_since_2022)}")
    print(f"  Earliest: {signal_since_2022[0]}  Latest: {signal_since_2022[-1]}")
    print()
    print(f"  {'Entry':7}  {'Signal':>8}  {'Curr P&L':>10}  "
          f"{'Max DD':>8}  {'Max DD mo':>10}  {'Mths UW':>8}")
    print(f"  {'-'*7}  {'-'*8}  {'-'*10}  {'-'*8}  {'-'*10}  {'-'*8}")

    for entry_ym in signal_since_2022:
        entry_i = common_yms.index(entry_ym)
        last_i  = len(common_yms) - 1
        rels = []
        for j in range(entry_i, last_i + 1):
            r = rsp_px[j] / rsp_px[entry_i]
            s = spy_px[j] / spy_px[entry_i]
            rels.append(r / s - 1)
        cur   = rels[-1]
        mxdd  = min(rels)
        mxdd_m = rels.index(mxdd)
        n_uw  = sum(1 for v in rels if v < 0)
        sig_v = roll36[entry_ym]
        print(f"  {entry_ym:7}  {sig_v*100:>+7.2f}%  {cur*100:>+9.2f}%  "
              f"{mxdd*100:>+7.2f}%  {mxdd_m:>10}  {n_uw:>8}/{len(rels)}")

print()

# ── §4.3 verdict ──────────────────────────────────────────────────────────────
print("─" * 68)
print("§4.3 VERDICT:")
print()

if entry_90:
    entry_i = common_yms.index(entry_90)
    rels_90 = [(rsp_px[j]/rsp_px[entry_i])/(spy_px[j]/spy_px[entry_i])-1
               for j in range(entry_i, len(common_yms))]
    mxdd_90   = min(rels_90)
    cur_90    = rels_90[-1]
    n_uw_90   = sum(1 for v in rels_90 if v < 0)
    ever_pos  = any(v > 0 for v in rels_90)

    print(f"  Entry at first 90th-pct crossing ({entry_90}):")
    print(f"    Max relative drawdown: {mxdd_90*100:.1f}pp")
    print(f"    Current P&L:           {cur_90*100:+.1f}pp")
    print(f"    Months underwater:     {n_uw_90} of {len(rels_90)}")
    print(f"    Ever turned positive:  {'Yes' if ever_pos else 'No — still underwater throughout'}")
    print()

    if mxdd_90 < -0.10 and not ever_pos:
        print("  The signal fired, the spread never paid off, and the max DD")
        print(f"  exceeded {abs(mxdd_90)*100:.0f}pp. This is the 'right but early' cost")
        print("  quantified. Any mandate with a 12-24 month patience limit would")
        print("  have been stopped out before seeing any return.")
    elif mxdd_90 < -0.05:
        print(f"  Drawdown reached {abs(mxdd_90)*100:.0f}pp before any recovery.")
        print("  Patience requirement exceeds typical fund mandate limits.")
    else:
        print(f"  Drawdown was modest ({abs(mxdd_90)*100:.0f}pp); patience cost is low.")

print()
print("=" * 68)
print("STOP — §4.3 complete. Awaiting approval before §4.4+.")
print("=" * 68)
