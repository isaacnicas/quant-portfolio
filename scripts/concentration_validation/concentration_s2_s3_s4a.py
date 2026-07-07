"""
Concentration Validation — §2 through §4.1 (first Claim B result).

Steps:
  0. Identify IBKR/YF daily-return divergence artifacts (abs > 0.5%)
  1. Check whether any artifact dates are month-end trading days
  2. Correct those month-end prices against YF reference; log all corrections
  3. Build clean monthly series (last trading day of each calendar month)
  4. §2: Construct spread + rolling 3yr relative return signal
  5. §3: Claim A — descriptive extremity table
  6. §4.1: Naive Claim B — conditional forward returns with overlap accounting
     STOP and print results; do not proceed to §4.2 without approval.

Provenance (confirmed in earlier session):
  - Both legs: IBKR ADJUSTED_LAST (total-return equivalent; RSP CAGR gap vs YF = 0.029pp)
  - yfinance enters ONLY as correction reference for artifact dates, not in the spread
  - Pull date: 2026-07-01
"""

import sys, csv, math, itertools
from pathlib import Path
from datetime import datetime, date, timedelta
from collections import defaultdict

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

RAW_DIR   = Path(r"C:\QuantTrading\quant-portfolio\data\raw")
OUT_DIR   = Path(r"C:\QuantTrading\quant-portfolio\reports")
OUT_DIR.mkdir(parents=True, exist_ok=True)
PULL_DATE = "2026-07-01"
ARTIFACT_THRESH = 0.005   # 0.5% daily-return divergence triggers artifact flag

# ── I/O helpers ───────────────────────────────────────────────────────────────
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
        except (ValueError, KeyError): pass
    return d          # {date_str: float}

def daily_rets(series):
    dates = sorted(series)
    r = {}
    for i in range(1, len(dates)):
        p, c = dates[i-1], dates[i]
        if series[p] > 0:
            r[c] = series[c] / series[p] - 1
    return r

def pct(x, arr):
    """Percentile rank of x in arr (fraction of arr < x)."""
    return sum(1 for v in arr if v < x) / len(arr) if arr else float("nan")

# ── Load data ─────────────────────────────────────────────────────────────────
print("=" * 68)
print("CONCENTRATION VALIDATION — §0 ARTIFACT CHECK THROUGH §4.1")
print("=" * 68)
print()

ibkr = {}; yf = {}
for tkr in ["SPY", "RSP"]:
    ibkr[tkr] = to_series(load_csv(RAW_DIR / f"{tkr}_ibkr_{PULL_DATE}.csv"))
    yf[tkr]   = to_series(load_csv(RAW_DIR / f"{tkr}_yfinance_{PULL_DATE}.csv"))
    print(f"Loaded {tkr}: IBKR={len(ibkr[tkr])} bars  YF={len(yf[tkr])} bars")
print()

# ── §0: Identify artifact dates ───────────────────────────────────────────────
print("─" * 68)
print("§0: ARTIFACT DATES (|IBKR daily ret – YF daily ret| > 0.50%)")
print()

artifacts = {}   # tkr -> set of date_str
for tkr in ["SPY", "RSP"]:
    ibkr_r = daily_rets(ibkr[tkr])
    yf_r   = daily_rets(yf[tkr])
    common = sorted(set(ibkr_r) & set(yf_r))
    arts = {d for d in common if abs(ibkr_r[d] - yf_r[d]) > ARTIFACT_THRESH}
    artifacts[tkr] = arts
    print(f"  {tkr}: {len(arts)} artifact dates  "
          f"(out of {len(common)} common trading days)")

print()

# ── §1: Check artifact vs month-end overlap ───────────────────────────────────
print("─" * 68)
print("§1: MONTH-END ARTIFACT OVERLAP CHECK")
print()

def month_end_dates(series):
    """Return set of date_str that are the last trading day of their calendar month."""
    dates = sorted(series.keys())
    me = set()
    for i, d in enumerate(dates):
        yr, mo = d[:4], d[5:7]
        if i == len(dates) - 1:
            me.add(d)
        else:
            nyr, nmo = dates[i+1][:4], dates[i+1][5:7]
            if (nyr, nmo) != (yr, mo):
                me.add(d)
    return me

corrections_applied = {}    # tkr -> {date_str: (old_px, new_px)}
for tkr in ["SPY", "RSP"]:
    me_dates = month_end_dates(ibkr[tkr])
    hits = artifacts[tkr] & me_dates
    corrections_applied[tkr] = {}

    if not hits:
        print(f"  {tkr}: 0 artifact dates fall on month-end — no correction needed")
    else:
        print(f"  {tkr}: {len(hits)} artifact date(s) fall on month-end — CORRECTING")
        ibkr_r = daily_rets(ibkr[tkr])
        yf_r   = daily_rets(yf[tkr])
        sorted_dates = sorted(ibkr[tkr].keys())

        for art_date in sorted(hits):
            # Previous IBKR trading day
            idx = sorted_dates.index(art_date)
            if idx == 0:
                print(f"    {art_date}: cannot correct — first bar, no predecessor")
                continue
            prev_date = sorted_dates[idx - 1]

            ibkr_prev = ibkr[tkr][prev_date]
            yf_ret_day = yf_r.get(art_date)
            if yf_ret_day is None:
                print(f"    {art_date}: no YF return available — skipping")
                continue

            # Corrected price: IBKR level × YF day return
            old_px  = ibkr[tkr][art_date]
            new_px  = ibkr_prev * (1 + yf_ret_day)
            ibkr[tkr][art_date] = new_px
            corrections_applied[tkr][art_date] = (old_px, new_px)

            print(f"    {art_date}  IBKR_old={old_px:.4f}  "
                  f"YF_ret={yf_ret_day*100:+.4f}%  IBKR_new={new_px:.4f}  "
                  f"delta={((new_px-old_px)/old_px)*100:+.4f}%")

print()
total_corr = sum(len(v) for v in corrections_applied.values())
print(f"Total corrections applied: {total_corr}")
print()

# ── §2: Build monthly series + spread ────────────────────────────────────────
print("─" * 68)
print("§2: MONTHLY SERIES + SPREAD CONSTRUCTION")
print()

# Month-end prices (after corrections)
def build_monthly(series):
    """
    Returns sorted list of (year_month_str, date_str, price).
    year_month_str = 'YYYY-MM' for easy bucketing.
    """
    me_dates = sorted(month_end_dates(series))
    result = []
    for d in me_dates:
        ym = d[:7]
        result.append((ym, d, series[d]))
    return result

spy_mo = build_monthly(ibkr["SPY"])
rsp_mo = build_monthly(ibkr["RSP"])

# Align on common year-months
spy_by_ym = {ym: px for ym, _, px in spy_mo}
rsp_by_ym = {ym: px for ym, _, px in rsp_mo}
spy_date_by_ym = {ym: d for ym, d, _ in spy_mo}
rsp_date_by_ym = {ym: d for ym, d, _ in rsp_mo}

common_yms = sorted(set(spy_by_ym) & set(rsp_by_ym))

# Restrict to RSP live period (first RSP bar = 2003-05)
common_yms = [ym for ym in common_yms if ym >= "2003-05"]

print(f"  Monthly observations (RSP inception onward): {len(common_yms)}")
print(f"  First month: {common_yms[0]}  Last month: {common_yms[-1]}")
print()

# Cumulative total-return index (base=1.0 at first common month)
spy_px = [spy_by_ym[ym] for ym in common_yms]
rsp_px = [rsp_by_ym[ym] for ym in common_yms]

# Spread ratio = RSP_TR / SPY_TR (rebased so both start at 1.0)
spy_base = spy_px[0]; rsp_base = rsp_px[0]
spy_idx = [p / spy_base for p in spy_px]
rsp_idx = [p / rsp_base for p in rsp_px]
spread  = [r / s for r, s in zip(rsp_idx, spy_idx)]   # >1 = RSP outperformed

# Monthly RSP-minus-SPY total return (for rolling windows)
# ret[i] = return from month i-1 to month i
spy_mo_ret = [spy_px[i]/spy_px[i-1] - 1 for i in range(1, len(spy_px))]
rsp_mo_ret = [rsp_px[i]/rsp_px[i-1] - 1 for i in range(1, len(rsp_px))]
rel_ret    = [r - s for r, s in zip(rsp_mo_ret, spy_mo_ret)]   # positive = RSP led
# Indexed alongside common_yms: rel_ret[i] is the return for common_yms[i+1]
# i.e., rel_ret[i] covers common_yms[i] → common_yms[i+1]

# Rolling 36-month cumulative RSP-minus-SPY (the signal cited in research)
# roll36[i] = cumulative RSP/SPY relative return over the 36 months ending at common_yms[i]
ROLL_WINDOW = 36
roll36 = {}   # ym -> cumulative relative return over prior 36 months
for i in range(len(common_yms)):
    ym = common_yms[i]
    # We need months i-36 to i: prices at those indices
    start_i = i - ROLL_WINDOW
    if start_i < 0:
        continue
    r = rsp_px[i] / rsp_px[start_i]
    s = spy_px[i] / spy_px[start_i]
    roll36[ym] = r / s - 1   # positive = RSP outperformed over 36m

roll36_yms = sorted(roll36.keys())
roll36_vals = [roll36[ym] for ym in roll36_yms]

print(f"  Rolling 36m relative return: {len(roll36_yms)} months")
print(f"  Current ({roll36_yms[-1]}): {roll36_vals[-1]*100:+.2f}%")
print(f"  All-time range: {min(roll36_vals)*100:.2f}% to {max(roll36_vals)*100:.2f}%")
print()

# Print last 12 months of the signal
print("  Rolling 36m RSP-minus-SPY (recent 18 months):")
print(f"  {'Month':7}  {'RSP idx':>8}  {'SPY idx':>8}  "
      f"{'Spread':>8}  {'Roll36m':>9}")
for ym in roll36_yms[-18:]:
    i = common_yms.index(ym)
    print(f"  {ym}  {rsp_idx[i]:8.4f}  {spy_idx[i]:8.4f}  "
          f"{spread[i]:8.4f}  {roll36[ym]*100:+8.2f}%")
print()

# ── §3: Claim A — Descriptive extremity ──────────────────────────────────────
print("─" * 68)
print("§3: CLAIM A — DESCRIPTIVE EXTREMITY TABLE")
print("(Data: ETF era 2003-present; pre-2003 episodes not tested — honest gap)")
print()

current_ym   = roll36_yms[-1]
current_r36  = roll36[current_ym]
current_r36_pct = pct(current_r36, roll36_vals)

# Identify prior periods where roll36 was at or below current level
below_current = [ym for ym in roll36_yms if roll36[ym] <= current_r36]
print(f"  Signal: rolling 36m RSP-minus-SPY total return")
print(f"  Current reading ({current_ym}): {current_r36*100:+.2f}%")
print(f"  Percentile vs full ETF history: {current_r36_pct*100:.1f}th")
print(f"  Months at or below current level: {len(below_current)} of {len(roll36_yms)}")
print()

# Show historic local minima (separate episodes, not runs)
# Find all months where roll36 < -20% and is a local minimum in its 6m neighborhood
local_mins = []
for i, ym in enumerate(roll36_yms):
    v = roll36[ym]
    if v > -0.10:
        continue
    window = roll36_vals[max(0, i-6):i+7]
    if v == min(window):
        local_mins.append((ym, v))

print("  Notable cap-weight dominance episodes (ETF era, roll36 local minima < -10%):")
print(f"  {'Month':7}  {'Roll36m':>9}  {'Interpretation'}")
print(f"  {'-------':7}  {'-'*9}  {'-'*40}")
for ym, v in local_mins:
    if ym <= "2003-12":
        note = "Early RSP history (sparse)"
    elif ym <= "2004-12":
        note = "Post-dot-com recovery, cap-weight lagged briefly"
    elif "2006" <= ym <= "2010":
        note = "Financial crisis era"
    elif "2014" <= ym <= "2018":
        note = "Post-GFC cap-weight rebound"
    else:
        note = "2023-present Mag-7 dominance"
    print(f"  {ym}  {v*100:+8.2f}%  {note}")

print()
print("  CLAIM A VERDICT: ", end="")
if current_r36_pct > 0.95:
    print("SUPPORTED — current cap-weight dominance (rolling 36m) is above 95th "
          "percentile of ETF-era history.")
elif current_r36_pct > 0.85:
    print("SUPPORTED — above 85th percentile. Historically elevated but not quite 95th.")
else:
    print(f"WEAK — {current_r36_pct*100:.0f}th percentile only.")
print()
print("  NOTE: Pre-2003 concentration data not tested. Two most extreme")
print("  historical episodes (1973 Nifty-Fifty, 2000 dot-com peak) lie outside")
print("  the ETF window. This percentile is 'extreme vs 2003-present', not vs full history.")
print()

# ── §4.1: Naive Claim B — conditional forward returns ─────────────────────────
print("─" * 68)
print("§4.1: CLAIM B — NAIVE CONDITIONAL FORWARD RETURN TEST")
print()
print("Signal: rolling 36m RSP-minus-SPY in bottom decile of full history")
print("('extreme cap-weight dominance' months).")
print("Forward return: cumulative RSP-minus-SPY total return over 6/12/24/36m.")
print()

# Signal months: bottom decile of roll36 (most cap-weight-dominant)
decile_thresh = sorted(roll36_vals)[int(len(roll36_vals) * 0.10)]
signal_months = [ym for ym in roll36_yms if roll36[ym] <= decile_thresh]
nonsignal_months = [ym for ym in roll36_yms if roll36[ym] > decile_thresh]

print(f"  Signal threshold (10th pct): {decile_thresh*100:+.2f}%")
print(f"  Signal months (extreme): {len(signal_months)}")
print(f"  Non-signal months:       {len(nonsignal_months)}")
print()

# Forward return computation
# fwd_ret(ym, h) = cumulative RSP-minus-SPY from ym to ym+h months
def fwd_rel_return(signal_ym, h_months):
    """
    Cumulative RSP/SPY forward return over h_months starting AFTER signal_ym.
    Returns None if data unavailable.
    """
    i = common_yms.index(signal_ym)
    j = i + h_months
    if j >= len(common_yms):
        return None
    r = rsp_px[j] / rsp_px[i] - 1
    s = spy_px[j] / spy_px[i] - 1
    return r - s   # approximate spread; more precisely: (1+r)/(1+s)-1 but close at this scale

def fwd_rel_return_compound(signal_ym, h_months):
    i = common_yms.index(signal_ym)
    j = i + h_months
    if j >= len(common_yms):
        return None
    r = rsp_px[j] / rsp_px[i]
    s = spy_px[j] / spy_px[i]
    return r / s - 1

HORIZONS = [6, 12, 24, 36]

print(f"  {'Horizon':>8}  {'n_obs':>6}  {'n_indep':>7}  "
      f"{'mean':>7}  {'median':>7}  {'hit%':>6}  "
      f"{'min':>7}  {'max':>7}  {'p25':>7}  {'p75':>7}")
print(f"  {'-'*8}  {'-'*6}  {'-'*7}  "
      f"{'-'*7}  {'-'*7}  {'-'*6}  "
      f"{'-'*7}  {'-'*7}  {'-'*7}  {'-'*7}")

claim_b_rows = []
for h in HORIZONS:
    fwds = []
    sig_with_data = []
    for ym in signal_months:
        v = fwd_rel_return_compound(ym, h)
        if v is not None:
            fwds.append(v)
            sig_with_data.append(ym)

    if not fwds:
        print(f"  {h:>5}m  {'N/A':>6}")
        continue

    n_obs   = len(fwds)
    n_indep = max(1, n_obs // h)   # non-overlapping block count (floor)
    mean_v  = sum(fwds) / n_obs
    sorted_f = sorted(fwds)
    med_v   = sorted_f[n_obs // 2]
    hit_v   = sum(1 for v in fwds if v > 0) / n_obs
    min_v   = sorted_f[0]
    max_v   = sorted_f[-1]
    p25     = sorted_f[int(n_obs * 0.25)]
    p75     = sorted_f[int(n_obs * 0.75)]

    claim_b_rows.append({
        "h": h, "n_obs": n_obs, "n_indep": n_indep,
        "mean": mean_v, "median": med_v, "hit": hit_v,
        "min": min_v, "max": max_v, "p25": p25, "p75": p75,
        "months": sig_with_data, "fwds": fwds,
    })

    print(f"  {h:>5}m  {n_obs:>6}  {n_indep:>7}  "
          f"{mean_v*100:>+6.2f}%  {med_v*100:>+6.2f}%  {hit_v*100:>5.1f}%  "
          f"{min_v*100:>+6.2f}%  {max_v*100:>+6.2f}%  "
          f"{p25*100:>+6.2f}%  {p75*100:>+6.2f}%")

print()

# Same table for non-signal months (control group)
print("  CONTROL (non-signal months, same horizons):")
print(f"  {'Horizon':>8}  {'n_obs':>6}  {'mean':>7}  {'median':>7}  {'hit%':>6}")
print(f"  {'-'*8}  {'-'*6}  {'-'*7}  {'-'*7}  {'-'*6}")

for h in HORIZONS:
    fwds_ns = []
    for ym in nonsignal_months:
        v = fwd_rel_return_compound(ym, h)
        if v is not None:
            fwds_ns.append(v)
    if not fwds_ns:
        continue
    mean_ns = sum(fwds_ns) / len(fwds_ns)
    sorted_ns = sorted(fwds_ns)
    med_ns  = sorted_ns[len(fwds_ns)//2]
    hit_ns  = sum(1 for v in fwds_ns if v > 0) / len(fwds_ns)
    print(f"  {h:>5}m  {len(fwds_ns):>6}  "
          f"{mean_ns*100:>+6.2f}%  {med_ns*100:>+6.2f}%  {hit_ns*100:>5.1f}%")

print()

# Identify which signal months actually have independent observations
# Non-overlapping: greedy — take earliest signal month, skip next h-1 months
print("  INDEPENDENT EPISODES (non-overlapping, greedy earliest-first):")
for h in HORIZONS:
    row = next((r for r in claim_b_rows if r["h"] == h), None)
    if not row: continue
    indep = []
    last_used = None
    for ym in sorted(row["months"]):
        if last_used is None or ym > last_used:
            i = common_yms.index(ym)
            j = i + h
            if j < len(common_yms):
                fv = fwd_rel_return_compound(ym, h)
                if fv is not None:
                    indep.append((ym, fv))
                    last_used = common_yms[j]  # skip forward by h months
    if not indep:
        continue
    indep_mean = sum(v for _, v in indep) / len(indep)
    indep_hit  = sum(1 for _, v in indep if v > 0) / len(indep)
    episodes_str = ", ".join(ym for ym, _ in indep)
    print(f"\n  {h}m horizon: {len(indep)} independent episodes")
    print(f"  Mean forward RSP-SPY: {indep_mean*100:+.2f}%  "
          f"Hit rate: {indep_hit*100:.0f}%")
    print(f"  Episodes: {episodes_str}")
    rets_str = "  " + "  ".join(f"{v*100:+.1f}%" for _, v in indep)
    print(f"  Returns: {rets_str}")

print()

# Does 2000 episode drive results? (§4.2 preview — note it, full test next)
pre2003_note = ("NOTE: Dot-com unwind (2000-2002) is entirely OUTSIDE the ETF window "
                "(RSP inception 2003-05). The §4.2 2000-exclusion test therefore cannot "
                "be run directly on this series. Equivalent test: exclude the 2003-2004 "
                "period (which captures the tail end of the recovery). See §4.2.")
print(f"  {pre2003_note}")
print()

# ── §4.1 Verdict ─────────────────────────────────────────────────────────────
print("─" * 68)
print("§4.1 CLAIM B — NAIVE RESULT SUMMARY")
print()

r12 = next((r for r in claim_b_rows if r["h"] == 12), None)
r36 = next((r for r in claim_b_rows if r["h"] == 36), None)

if r12 and r36:
    print(f"  12m: mean={r12['mean']*100:+.2f}%  hit={r12['hit']*100:.0f}%  "
          f"n_obs={r12['n_obs']}  n_indep={r12['n_indep']}")
    print(f"  36m: mean={r36['mean']*100:+.2f}%  hit={r36['hit']*100:.0f}%  "
          f"n_obs={r36['n_obs']}  n_indep={r36['n_indep']}")
    print()

    # Interpret
    if r12["n_indep"] < 3:
        indep_warn = f"WARNING: only {r12['n_indep']} independent 12m observations. "
        indep_warn += "No statistical conclusion possible."
    else:
        indep_warn = ""

    if r12["mean"] > 0 and r12["hit"] > 0.55:
        naive_result = ("Naive test POSITIVE: mean forward RSP-minus-SPY is positive at "
                        f"12m ({r12['mean']*100:+.2f}%) and 36m ({r36['mean']*100:+.2f}%). "
                        "BUT: n_indep is small and the 2000 episode is outside the window. "
                        "§4.2 kill-test mandatory before any conclusion.")
    elif r12["mean"] < 0:
        naive_result = ("Naive test NEGATIVE: mean forward RSP-minus-SPY is negative at "
                        f"12m ({r12['mean']*100:+.2f}%). Claim B fails even the naive test.")
    else:
        naive_result = f"Naive test MIXED: 12m={r12['mean']*100:+.2f}%  36m={r36['mean']*100:+.2f}%."

    print(f"  {naive_result}")
    if indep_warn:
        print(f"  {indep_warn}")

print()
print("=" * 68)
print("STOP — §4.1 result delivered. Awaiting approval before §4.2+.")
print("=" * 68)
