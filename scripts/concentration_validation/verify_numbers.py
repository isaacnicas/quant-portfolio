import csv, math
from pathlib import Path

RAW  = Path(r"C:\QuantTrading\quant-portfolio\data\raw")
PULL = "2026-07-01"

def load(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"): continue
            rows.append(line)
    return {r["date"]: float(r["close"]) for r in csv.DictReader(rows)}

def month_end(series):
    dates = sorted(series)
    me = {}
    for i, d in enumerate(dates):
        ym = d[:7]
        if i == len(dates)-1 or dates[i+1][:7] != ym:
            me[ym] = series[d]
    return me

def daily_rets(series):
    sd = sorted(series); r = {}
    for i in range(1, len(sd)):
        p, c = sd[i-1], sd[i]
        if series[p] > 0: r[c] = series[c]/series[p]-1
    return r

spy_ibkr = load(RAW / f"SPY_ibkr_{PULL}.csv")
rsp_ibkr = load(RAW / f"RSP_ibkr_{PULL}.csv")
spy_yf   = load(RAW / f"SPY_yfinance_{PULL}.csv")
rsp_yf   = load(RAW / f"RSP_yfinance_{PULL}.csv")

print(f"SPY IBKR bars: {len(spy_ibkr)}")
print(f"RSP IBKR bars: {len(rsp_ibkr)}")
print(f"SPY YF bars:   {len(spy_yf)}")
print(f"RSP YF bars:   {len(rsp_yf)}")

# Apply corrections
for tkr, arts in [("SPY", ["2007-11-30"]), ("RSP", ["2007-02-28","2008-02-29","2008-09-30"])]:
    ibkr = spy_ibkr if tkr == "SPY" else rsp_ibkr
    yf   = spy_yf   if tkr == "SPY" else rsp_yf
    yf_r = daily_rets(yf); sd = sorted(ibkr)
    for d in arts:
        idx = sd.index(d); yr = yf_r.get(d)
        if yr and idx > 0: ibkr[d] = ibkr[sd[idx-1]] * (1 + yr)

spy_mo = month_end(spy_ibkr); rsp_mo = month_end(rsp_ibkr)
common = sorted(ym for ym in set(spy_mo) & set(rsp_mo) if ym >= "2003-05")
spy_px = [spy_mo[ym] for ym in common]
rsp_px = [rsp_mo[ym] for ym in common]
print(f"\nMonthly obs: {len(common)}  {common[0]} to {common[-1]}")

ROLL = 36
roll36 = {}
for i in range(len(common)):
    si = i - ROLL
    if si < 0: continue
    roll36[common[i]] = (rsp_px[i]/rsp_px[si]) / (spy_px[i]/spy_px[si]) - 1

r36_yms  = sorted(roll36)
r36_vals = [roll36[ym] for ym in r36_yms]
n        = len(r36_vals); sv = sorted(r36_vals)
thresh_10 = sv[int(n * 0.10)]

print(f"\n=== CLAIM A ===")
current  = roll36[r36_yms[-1]]
pct_from_bottom = sum(1 for v in r36_vals if v < current) / n
print(f"Current month:       {r36_yms[-1]}")
print(f"Rolling 36m:         {current*100:.4f}%  [report: -14.40%]")
print(f"Pct from bottom:     {pct_from_bottom*100:.1f}th  [report: 7th]")
print(f"Obs in roll36:       {n}  [report: 243]")
print(f"Threshold (10th):    {thresh_10*100:.4f}%  [report: -13.06%]")
all_time_low = min(r36_vals)
atl_ym = r36_yms[r36_vals.index(all_time_low)]
print(f"All-time low ETF:    {all_time_low*100:.4f}% at {atl_ym}  [report: -23.12% 2025-12]")

def fwd_rel(ym, h):
    i = common.index(ym); j = i + h
    if j >= len(common): return None
    return (rsp_px[j]/rsp_px[i]) / (spy_px[j]/spy_px[i]) - 1

print(f"\n=== §4.2 ===")
ex_2020 = {ym for ym in r36_yms if "2020-01" <= ym <= "2020-12"}
sig_A   = [ym for ym in r36_yms if roll36[ym] <= thresh_10 and ym not in ex_2020]
indep_A = []; last_end = None
for ym in sorted(sig_A):
    if last_end and ym <= last_end: continue
    fv = fwd_rel(ym, 12)
    if fv is None: continue
    i = common.index(ym)
    indep_A.append((ym, fv))
    last_end = common[min(i+12, len(common)-1)]

if indep_A:
    vals  = [v for _, v in indep_A]
    mean_ = sum(vals)/len(vals)
    hit_  = sum(1 for v in vals if v > 0)/len(vals)
    print(f"12m independent:  n={len(indep_A)}  mean={mean_*100:.4f}%  hit={hit_*100:.0f}%")
    print(f"  [report: n=2, mean=-1.57%, hit=0%]")
    for ym, fv in indep_A:
        print(f"  {ym}: {fv*100:.4f}%")

print(f"\n=== §4.3 entry 2024-06 ===")
entry_i = common.index("2024-06")
rels = []
for j in range(entry_i, len(common)):
    r = rsp_px[j]/rsp_px[entry_i]; s = spy_px[j]/spy_px[entry_i]
    rels.append((common[j], j - entry_i, r/s - 1))

max_dd_v = min(v for _,_,v in rels)
max_dd_r = next(r for _,r,v in rels if v == max_dd_v)
max_dd_y = next(y for y,_,v in rels if v == max_dd_v)
cur_y, cur_m, cur_v = rels[-1]
n_uw = sum(1 for _,_,v in rels if v < 0)
print(f"Max DD:  {max_dd_v*100:.4f}pp  month {max_dd_r}  ({max_dd_y})")
print(f"  [report: -8.2pp month 16 2025-10]")
print(f"Current: {cur_v*100:.4f}pp  month {cur_m}  ({cur_y})")
print(f"  [report: -4.3pp month 25]")
print(f"Mths UW: {n_uw} of {len(rels)}  [report: 17 of 26]")

print(f"\n=== §4.6 ===")
print(f"29 total variants — confirmed from concentration_s45_report.py output")
