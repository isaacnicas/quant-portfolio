"""
Verify whether IBKR ADJUSTED_LAST is true total-return or price/split-adjusted only.

Two independent checks:
  1. CAGR-basis: if IBKR is price-only, it should run ~1-2pp/yr below yfinance auto_adjust=True.
  2. Ex-dividend spot-check: on known ex-div dates, a price-only series drops by ~dividend;
     a total-return series is smooth (historical prices already adjusted backward).

We find ex-div dates by looking for the largest IBKR-vs-YF daily-return divergences:
if both series are total return, divergences should be near-zero every day.
If IBKR is price-only, divergences spike on ex-div dates by roughly the dividend amount.
"""

import sys, csv, math
from pathlib import Path
from datetime import datetime, timedelta

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

RAW_DIR   = Path(r"C:\QuantTrading\quant-portfolio\data\raw")
PULL_DATE = "2026-07-01"

# ── Load helpers ───────────────────────────────────────────────────────────────
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
    return d

def daily_returns(series):
    dates = sorted(series)
    ret = {}
    for i in range(1, len(dates)):
        prev, cur = dates[i-1], dates[i]
        if series[prev] > 0:
            ret[cur] = series[cur] / series[prev] - 1
    return ret

def cagr(sv, ev, sd, ed):
    d0 = datetime.strptime(sd, "%Y-%m-%d")
    d1 = datetime.strptime(ed, "%Y-%m-%d")
    yrs = (d1 - d0).days / 365.25
    return (ev / sv) ** (1 / yrs) - 1 if yrs > 0 and sv > 0 else float("nan")

def nearest_on_or_after(d, t):
    for k in sorted(d):
        if k >= t: return k, d[k]
    return None, None

def nearest_on_or_before(d, t):
    res = None
    for k in sorted(d):
        if k <= t: res = (k, d[k])
    return res if res else (None, None)

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("=" * 68)
    print("IBKR ADJUSTED_LAST — TOTAL RETURN vs PRICE-RETURN VERIFICATION")
    print("=" * 68)
    print()

    # Load all four series
    data = {}
    for src in ["ibkr", "yfinance"]:
        for tkr in ["SPY", "RSP"]:
            path = RAW_DIR / f"{tkr}_{src}_{PULL_DATE}.csv"
            if not path.exists():
                print(f"MISSING: {path.name}")
                continue
            rows = load_csv(path)
            key = f"{tkr}_{src}"
            data[key] = to_series(rows)
            print(f"Loaded {path.name}: {len(data[key])} bars")
    print()

    RSP_INCEP = "2003-05-01"   # first IBKR bar
    WINDOW_END = "2026-06-30"

    # ── CHECK 1: CAGR-basis comparison ────────────────────────────────────────
    print("─" * 68)
    print("CHECK 1: CAGR-BASIS COMPARISON")
    print()
    print("Logic: RSP dividend yield ≈ 1.3–1.7%/yr. Over 23 years, a price-only")
    print("series would run ~1.3–1.7pp/yr below yfinance (which is total return).")
    print("If IBKR matches yfinance within 0.1pp, IBKR is also total return.")
    print()

    for tkr in ["SPY", "RSP"]:
        ibkr_d = data.get(f"{tkr}_ibkr", {})
        yf_d   = data.get(f"{tkr}_yfinance", {})
        if not ibkr_d or not yf_d:
            print(f"{tkr}: missing data"); continue

        sd_i, sp_i = nearest_on_or_after(ibkr_d, RSP_INCEP)
        ed_i, ep_i = nearest_on_or_before(ibkr_d, WINDOW_END)
        sd_y, sp_y = nearest_on_or_after(yf_d,   RSP_INCEP)
        ed_y, ep_y = nearest_on_or_before(yf_d,   WINDOW_END)

        c_i = cagr(sp_i, ep_i, sd_i, ed_i) * 100
        c_y = cagr(sp_y, ep_y, sd_y, ed_y) * 100
        gap = c_y - c_i  # positive means YF higher than IBKR

        print(f"  {tkr}:")
        print(f"    IBKR ADJUSTED_LAST: {sd_i} @ {sp_i:.4f}  →  "
              f"{ed_i} @ {ep_i:.4f}   CAGR = {c_i:.3f}%")
        print(f"    yfinance auto_adj:  {sd_y} @ {sp_y:.4f}  →  "
              f"{ed_y} @ {ep_y:.4f}   CAGR = {c_y:.3f}%")
        print(f"    YF minus IBKR gap:  {gap:+.3f}pp/yr")
        if abs(gap) < 0.15:
            verdict = "TOTAL RETURN — gap < 0.15pp, matches total-return benchmark"
        elif abs(gap) < 0.30:
            verdict = "LIKELY TOTAL RETURN — gap < 0.30pp (some methodology difference)"
        elif gap > 1.0:
            verdict = "PRICE RETURN ONLY — gap > 1pp indicates missing dividend ~1.5%/yr"
        else:
            verdict = f"AMBIGUOUS — gap {gap:+.3f}pp; inspect ex-div spot-check"
        print(f"    Verdict: {verdict}")
        print()

    # ── CHECK 2: Ex-dividend spot-check (daily-return divergence) ─────────────
    print("─" * 68)
    print("CHECK 2: EX-DIVIDEND SPOT-CHECK — DAILY RETURN DIVERGENCE")
    print()
    print("Logic: if IBKR is price-return only, it shows a negative spike on")
    print("ex-div dates equal to ~dividend/price (0.3–0.5% quarterly for RSP/SPY).")
    print("If both series are total return, daily returns track nearly identically.")
    print()

    for tkr in ["RSP", "SPY"]:
        ibkr_d = data.get(f"{tkr}_ibkr", {})
        yf_d   = data.get(f"{tkr}_yfinance", {})
        if not ibkr_d or not yf_d:
            print(f"{tkr}: missing data"); continue

        ibkr_ret = daily_returns(ibkr_d)
        yf_ret   = daily_returns(yf_d)

        # Common dates only, restrict to post-RSP-inception
        common = sorted(
            d for d in set(ibkr_ret) & set(yf_ret)
            if d >= RSP_INCEP and d <= WINDOW_END
        )

        diffs = [(d, ibkr_ret[d] - yf_ret[d]) for d in common]
        diffs_sorted = sorted(diffs, key=lambda x: x[1])  # most-negative first

        abs_diffs = [abs(v) for _, v in diffs]
        rmsd = math.sqrt(sum(x**2 for x in abs_diffs) / len(abs_diffs))
        max_abs = max(abs_diffs)

        print(f"  {tkr}  (n={len(common)} common trading days):")
        print(f"    RMSD of daily-return divergence: {rmsd*100:.4f}%")
        print(f"    Max absolute divergence:         {max_abs*100:.4f}%")
        print()

        # Print the 10 most negative divergences (likely ex-div events if price-only)
        print(f"  Top-10 most-negative IBKR-minus-YF daily returns (candidate ex-div dates):")
        print(f"  {'Date':12}  {'IBKR ret':>10}  {'YF ret':>10}  {'Diff (IBKR-YF)':>16}")
        print(f"  {'-'*12}  {'-'*10}  {'-'*10}  {'-'*16}")
        for d, diff in diffs_sorted[:10]:
            ib  = ibkr_ret[d]
            yf  = yf_ret[d]
            print(f"  {d:12}  {ib*100:>9.4f}%  {yf*100:>9.4f}%  {diff*100:>15.4f}%")

        # Also top-10 most-positive divergences
        print()
        print(f"  Top-10 most-positive IBKR-minus-YF daily returns:")
        print(f"  {'Date':12}  {'IBKR ret':>10}  {'YF ret':>10}  {'Diff (IBKR-YF)':>16}")
        print(f"  {'-'*12}  {'-'*10}  {'-'*10}  {'-'*16}")
        for d, diff in reversed(diffs_sorted[-10:]):
            ib  = ibkr_ret[d]
            yf  = yf_ret[d]
            print(f"  {d:12}  {ib*100:>9.4f}%  {yf*100:>9.4f}%  {diff*100:>15.4f}%")

        print()
        # Interpret
        n_large = sum(1 for _, diff in diffs if diff < -0.25/100)
        if rmsd * 100 < 0.02 and max_abs * 100 < 0.10:
            basis = "TOTAL RETURN — near-zero divergence across all dates"
        elif n_large >= 4:
            basis = f"PRICE RETURN LIKELY — {n_large} dates with IBKR < YF by >0.25%; consistent with ex-div drops"
        else:
            basis = f"AMBIGUOUS — RMSD={rmsd*100:.4f}%, max={max_abs*100:.4f}%; inspect table above"
        print(f"  {tkr} ex-div check: {basis}")
        print()

    # ── Summary + Provenance Declaration ──────────────────────────────────────
    print("=" * 68)
    print("PROVENANCE DECLARATION FOR §2+ SIGNAL WORK")
    print()
    print("Series to use for spread construction:")
    print("  Long leg:  RSP_ibkr_2026-07-01.csv  (IBKR ADJUSTED_LAST)")
    print("  Short leg: SPY_ibkr_2026-07-01.csv  (IBKR ADJUSTED_LAST)")
    print("  Both legs: same source, same field, same pull date.")
    print()
    print("yfinance CSVs: used for §1.5 gate ONLY — must not enter spread.")
    print()
    print("Adjustment basis: see CHECK 1 + CHECK 2 above. If TOTAL RETURN,")
    print("the spread RSP/SPY is a true total-return spread and the ~0.3-0.5pp/yr")
    print("dividend-yield advantage of RSP over SPY is captured.")
    print("If PRICE RETURN, the spread understates equal-weight by ~0.3-0.5pp/yr")
    print("(conservative bias — against finding Claim B).")
    print("=" * 68)

if __name__ == "__main__":
    main()
