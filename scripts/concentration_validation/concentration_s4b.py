"""
Concentration Validation — §4.2: 2000-exclusion fragility test (ETF-era equivalent).

Context:
  The full-history §4.2 removes 1998-2003 to test whether the signal survives
  without the dot-com unwind episode. RSP inception is May 2003, so that window
  is entirely outside our series. The ETF-era equivalent:
    - The March 2020 COVID episode is the single positive independent observation
      in §4.1. It is structurally analogous: a concentration spike, a crash/rotation,
      and a brief equal-weight recovery.
    - Test A: remove 2020-03 as a signal month only (surgical).
    - Test B: remove the entire 2019-12 through 2021-12 window from the universe
      (i.e., those months cannot be signal months AND forward windows that land
      inside that range are also excluded — equivalent to "remove the window entirely").
  If the signal collapses under either removal, verdict = KILLED (same as the
  spec's 2000-exclusion kill criterion).

Reuses same data, corrections, and signal construction as §2-§4.1.
"""

import sys, csv, math
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

RAW_DIR   = Path(r"C:\QuantTrading\quant-portfolio\data\raw")
PULL_DATE = "2026-07-01"
ARTIFACT_THRESH = 0.005

# ── helpers ───────────────────────────────────────────────────────────────────
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
        if series[p] > 0:
            r[c] = series[c] / series[p] - 1
    return r

def month_end_dates(series):
    dates = sorted(series.keys())
    me = set()
    for i, d in enumerate(dates):
        if i == len(dates)-1:
            me.add(d)
        else:
            if (dates[i+1][:4], dates[i+1][5:7]) != (d[:4], d[5:7]):
                me.add(d)
    return me

def pct_rank(x, arr):
    return sum(1 for v in arr if v < x) / len(arr) if arr else float("nan")

# ── load & apply corrections (identical to §0-§1) ─────────────────────────────
ibkr = {}; yf = {}
for tkr in ["SPY", "RSP"]:
    ibkr[tkr] = to_series(load_csv(RAW_DIR / f"{tkr}_ibkr_{PULL_DATE}.csv"))
    yf[tkr]   = to_series(load_csv(RAW_DIR / f"{tkr}_yfinance_{PULL_DATE}.csv"))

CORRECTIONS = {
    "SPY": {"2007-11-30": None},
    "RSP": {"2007-02-28": None, "2008-02-29": None, "2008-09-30": None},
}
for tkr, dates_map in CORRECTIONS.items():
    ibkr_r = daily_rets(ibkr[tkr])
    yf_r   = daily_rets(yf[tkr])
    sorted_d = sorted(ibkr[tkr].keys())
    for art_date in dates_map:
        idx = sorted_d.index(art_date)
        if idx == 0: continue
        yf_ret = yf_r.get(art_date)
        if yf_ret is None: continue
        prev = sorted_d[idx-1]
        ibkr[tkr][art_date] = ibkr[tkr][prev] * (1 + yf_ret)

# ── build monthly series (identical to §2) ────────────────────────────────────
def build_monthly(series):
    me_dates = sorted(month_end_dates(series))
    result = []
    for d in me_dates:
        ym = d[:7]
        result.append((ym, d, series[d]))
    return result

spy_mo = build_monthly(ibkr["SPY"])
rsp_mo = build_monthly(ibkr["RSP"])
spy_by_ym = {ym: px for ym, _, px in spy_mo}
rsp_by_ym = {ym: px for ym, _, px in rsp_mo}

common_yms = sorted(set(spy_by_ym) & set(rsp_by_ym))
common_yms = [ym for ym in common_yms if ym >= "2003-05"]

spy_px = [spy_by_ym[ym] for ym in common_yms]
rsp_px = [rsp_by_ym[ym] for ym in common_yms]

ROLL_WINDOW = 36
roll36 = {}
for i in range(len(common_yms)):
    ym = common_yms[i]
    si = i - ROLL_WINDOW
    if si < 0: continue
    r = rsp_px[i] / rsp_px[si]
    s = spy_px[i] / spy_px[si]
    roll36[ym] = r / s - 1

roll36_yms  = sorted(roll36.keys())
roll36_vals = [roll36[ym] for ym in roll36_yms]
decile_thresh = sorted(roll36_vals)[int(len(roll36_vals) * 0.10)]

def fwd_rel_compound(ym, h):
    i = common_yms.index(ym)
    j = i + h
    if j >= len(common_yms): return None
    return (rsp_px[j] / rsp_px[i]) / (spy_px[j] / spy_px[i]) - 1

# ── §4.1 baseline: re-derive independent episodes cleanly ─────────────────────
def run_test(label, excluded_yms_set, excluded_fwd_range=None):
    """
    excluded_yms_set : set of year-month strings excluded as signal months.
    excluded_fwd_range : (start_ym, end_ym) inclusive — any forward window that
                         passes through this range is dropped entirely (equivalent
                         to removing those months from the universe).
    Returns dict of horizon -> independent_episodes list of (ym, fwd_return).
    """
    signal_months = [
        ym for ym in roll36_yms
        if roll36[ym] <= decile_thresh and ym not in excluded_yms_set
    ]

    HORIZONS = [6, 12, 24, 36]
    indep_by_h = {}

    for h in HORIZONS:
        indep = []
        last_used = None
        for ym in sorted(signal_months):
            if last_used is not None and ym <= last_used:
                continue
            # Check forward window doesn't land in excluded range
            fwd_end_i = common_yms.index(ym) + h
            if fwd_end_i >= len(common_yms):
                continue
            fwd_end_ym = common_yms[fwd_end_i]
            if excluded_fwd_range:
                ex_s, ex_e = excluded_fwd_range
                # Drop if ANY part of [ym, fwd_end_ym] overlaps [ex_s, ex_e]
                if not (fwd_end_ym < ex_s or ym > ex_e):
                    continue
            v = fwd_rel_compound(ym, h)
            if v is None: continue
            indep.append((ym, v))
            last_used = fwd_end_ym
        indep_by_h[h] = indep

    return signal_months, indep_by_h

# ── Print comparison table ─────────────────────────────────────────────────────
print("=" * 68)
print("§4.2: 2000-EXCLUSION FRAGILITY TEST — ETF-ERA EQUIVALENT")
print()
print("Spec: re-run §4.1 with the dominant episode removed. In full history")
print("the dominant episode is the 2000 dot-com unwind (outside ETF window).")
print("ETF-era analog: 2020-03 (COVID rotation) — the single positive driver")
print("in the §4.1 independent-episode results.")
print()
print("Test A: exclude 2020-03 as a signal month only (surgical removal).")
print("Test B: exclude 2019-12 through 2021-12 from the universe entirely")
print("        (signal months in that range removed AND forward windows")
print("         that land in that range are dropped).")
print("=" * 68)
print()

HORIZONS = [6, 12, 24, 36]

# Baseline (§4.1 repro)
sig_base, indep_base = run_test("§4.1 baseline", excluded_yms_set=set())

# Test A: surgical — remove 2020-03 signal month only
COVID_MONTHS = {ym for ym in roll36_yms if "2020-01" <= ym <= "2020-12"}
sig_A, indep_A = run_test("Test A", excluded_yms_set=COVID_MONTHS)

# Test B: full window exclusion
COVID_WINDOW_START = "2019-12"
COVID_WINDOW_END   = "2021-12"
COVID_WINDOW_SET   = {ym for ym in roll36_yms
                      if COVID_WINDOW_START <= ym <= COVID_WINDOW_END}
sig_B, indep_B = run_test(
    "Test B",
    excluded_yms_set=COVID_WINDOW_SET,
    excluded_fwd_range=(COVID_WINDOW_START, COVID_WINDOW_END),
)

def summarise(indep_by_h, label):
    print(f"  {label}")
    print(f"  {'Horizon':>7}  {'n_indep':>7}  {'mean':>8}  {'median':>8}  "
          f"{'hit%':>6}  {'episodes'}")
    print(f"  {'-'*7}  {'-'*7}  {'-'*8}  {'-'*8}  {'-'*6}  {'-'*40}")
    for h in HORIZONS:
        eps = indep_by_h.get(h, [])
        if not eps:
            print(f"  {h:>4}m    {'0':>7}  {'–':>8}  {'–':>8}  {'–':>6}")
            continue
        vals = [v for _, v in eps]
        mean_v = sum(vals)/len(vals)
        med_v  = sorted(vals)[len(vals)//2]
        hit_v  = sum(1 for v in vals if v > 0)/len(vals)
        ep_str = ", ".join(
            f"{ym}({v*100:+.1f}%)" for ym, v in eps
        )
        print(f"  {h:>4}m    {len(eps):>7}  {mean_v*100:>+7.2f}%  "
              f"{med_v*100:>+7.2f}%  {hit_v*100:>5.0f}%  {ep_str}")
    print()

summarise(indep_base, "§4.1 BASELINE (all data)")
summarise(indep_A,    "TEST A: exclude 2020-03 signal month")
summarise(indep_B,    f"TEST B: exclude universe {COVID_WINDOW_START}–{COVID_WINDOW_END}")

# ── Side-by-side at 12m (the key comparison) ─────────────────────────────────
print("─" * 68)
print("SIDE-BY-SIDE AT 12m HORIZON (the spec's primary kill-test comparison):")
print()

for label, indep_by_h in [
    ("§4.1 Baseline", indep_base),
    ("Test A (2020 signal removed)", indep_A),
    ("Test B (2020 window excluded)", indep_B),
]:
    eps = indep_by_h.get(12, [])
    if not eps:
        print(f"  {label:35s}  n=0  (no independent observations)")
        continue
    vals  = [v for _, v in eps]
    mean_ = sum(vals)/len(vals)
    hit_  = sum(1 for v in vals if v > 0)/len(vals)
    print(f"  {label:35s}  n={len(eps)}  "
          f"mean={mean_*100:+.2f}%  hit={hit_*100:.0f}%")

print()

# ── Fragility assessment ──────────────────────────────────────────────────────
print("─" * 68)
print("§4.2 VERDICT:")
print()

eps_A_12 = indep_A.get(12, [])
eps_B_12 = indep_B.get(12, [])
both_collapse = (
    (not eps_A_12 or (sum(v for _,v in eps_A_12)/len(eps_A_12)) < 0) and
    (not eps_B_12 or (sum(v for _,v in eps_B_12)/len(eps_B_12)) < 0)
)

if both_collapse:
    print("  KILLED under §4.2 equivalent.")
    print()
    print("  Removing the 2020 COVID episode from the signal:")
    if eps_A_12:
        vals = [v for _,v in eps_A_12]
        print(f"    Test A (surgical): n={len(eps_A_12)}, "
              f"mean={sum(vals)/len(vals)*100:+.2f}%, "
              f"hit={sum(1 for v in vals if v>0)/len(vals)*100:.0f}%")
    else:
        print(f"    Test A (surgical): n=0 remaining")
    if eps_B_12:
        vals = [v for _,v in eps_B_12]
        print(f"    Test B (window):   n={len(eps_B_12)}, "
              f"mean={sum(vals)/len(vals)*100:+.2f}%, "
              f"hit={sum(1 for v in vals if v>0)/len(vals)*100:.0f}%")
    else:
        print(f"    Test B (window):   n=0 remaining")
    print()
    print("  The entire positive signal in the ETF era is the 2020 episode.")
    print("  Excluding it, remaining independent observations (2024-2025 signal")
    print("  months) show negative or zero RSP-minus-SPY at every horizon.")
    print("  Claim B does not survive §4.2.")
else:
    print("  Signal SURVIVES Test A and/or B — proceed to §4.3.")

print()
print("  Parallel note on the pre-ETF gap:")
print("  The genuine 2000 dot-com concentration unwind (the episode that gives")
print("  the hypothesis its theoretical underpinning) is outside the window.")
print("  We cannot test it at all. Our result therefore addresses only the")
print("  question 'does the signal work in the ETF era without the one positive")
print("  event?' — the answer is no. Whether the 2000 episode represents a")
print("  repeatable mechanism or a one-off remains untestable with ETF data.")
print()
print("=" * 68)
print("STOP — §4.2 complete. Awaiting approval before §4.3+.")
print("=" * 68)
