"""
IBKR historical data pull — Python 3.14 / SelectorEventLoop fix.
Pulls SPY and RSP daily ADJUSTED_LAST bars; cross-checks vs yfinance CSVs.
"""
import asyncio
asyncio.set_event_loop(asyncio.SelectorEventLoop())   # must be before ib_insync import

import sys, csv, math, time, socket
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

from ib_insync import IB, Stock

PULL_DATE     = datetime.now().strftime("%Y-%m-%d")
RAW_DIR       = Path(r"C:\QuantTrading\quant-portfolio\data\raw")
RSP_INCEPTION = "2003-04-24"
RECON_REF_END = "2026-06-30"

def port_open(p):
    s = socket.socket(); s.settimeout(2)
    try:    return s.connect_ex(("127.0.0.1", p)) == 0
    finally: s.close()

def to_dict(rows):
    return {r["date"]: float(r["close"]) for r in rows}

def nearest_on_or_after(d, t):
    for k in sorted(d):
        if k >= t: return k, d[k]
    return None, None

def nearest_on_or_before(d, t):
    result = None
    for k in sorted(d):
        if k <= t: result = (k, d[k])
    return result if result else (None, None)

def cagr(sv, ev, sd, ed):
    d0 = datetime.strptime(sd, "%Y-%m-%d")
    d1 = datetime.strptime(ed, "%Y-%m-%d")
    yrs = (d1 - d0).days / 365.25
    return (ev / sv) ** (1 / yrs) - 1 if yrs > 0 and sv > 0 else float("nan")

def read_yf_csv(ticker):
    path = RAW_DIR / f"{ticker}_yfinance_{PULL_DATE}.csv"
    if not path.exists():
        return {}
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"): continue
            rows.append(line)
    return {r["date"]: float(r["close"]) for r in csv.DictReader(rows)}

def write_csv(path, header_lines, fieldnames, rows):
    if path.exists():
        print(f"  [SKIP] {path.name} already exists (immutable)")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        for h in header_lines: f.write(f"# {h}\n")
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader(); w.writerows(rows)
    print(f"  [SAVED] {path.name} ({len(rows)} rows)")

def pull_one(ib, ticker):
    contract = Stock(ticker, "SMART", "USD")
    ib.qualifyContracts(contract)
    for what in ["ADJUSTED_LAST", "TRADES"]:
        try:
            print(f"  {ticker}: requesting 24Y daily bars ({what}) ...")
            bars = ib.reqHistoricalData(
                contract, endDateTime="", durationStr="24 Y",
                barSizeSetting="1 day", whatToShow=what,
                useRTH=True, formatDate=1, keepUpToDate=False,
            )
            if bars:
                print(f"  {ticker}: {len(bars)} bars ({what})")
                return bars, what
            print(f"  {ticker}: {what} returned 0 bars")
        except Exception as e:
            print(f"  {ticker}: {what} error: {e}")
            time.sleep(3)
    return [], "NONE"

def main():
    print("=" * 68)
    print("IBKR PULL (SelectorEventLoop fix) + §1.5 RECONCILIATION")
    print(f"Pull date: {PULL_DATE}")
    print("=" * 68)

    port = next((p for p in [4002, 7497] if port_open(p)), None)
    if not port:
        print("No IBKR port available. Cannot pull from IBKR.")
        return
    src_label = "TWS" if port == 7497 else "Gateway"
    print(f"Port {port} ({src_label}) open")
    if port == 7497:
        print("  Note: spec calls for Gateway/4002; using TWS/7497 (same API)")
    print()

    ib = IB()
    ib.connect("127.0.0.1", port, clientId=22)
    print(f"Connected to IBKR {src_label} on port {port}")
    print()

    ibkr_data = {}
    for ticker in ["SPY", "RSP"]:
        print(f"--- {ticker} ---")
        bars, what = pull_one(ib, ticker)
        ibkr_data[ticker] = {"bars": bars, "what": what}
        if bars:
            rows = [{"date": str(b.date), "open": b.open, "high": b.high,
                     "low": b.low, "close": b.close, "volume": b.volume}
                    for b in bars]
            path = RAW_DIR / f"{ticker}_ibkr_{PULL_DATE}.csv"
            write_csv(path,
                [f"IMMUTABLE RAW PULL — DO NOT MODIFY",
                 f"Instrument: {ticker}",
                 f"Source: IBKR {src_label} port {port}",
                 f"whatToShow: {what}",
                 f"barSizeSetting: 1 day, useRTH: True",
                 f"Pull date: {PULL_DATE}",
                 f"Rows: {len(rows)}"],
                ["date","open","high","low","close","volume"], rows)
        if ticker == "SPY":
            print("  Pacing: 12s sleep ...")
            time.sleep(12)

    ib.disconnect()
    print("\nDisconnected from IBKR")

    # §1.5 Reconciliation
    print()
    print("=" * 68)
    print(f"§1.5 RECONCILIATION: IBKR vs yfinance  [{RSP_INCEPTION} → {RECON_REF_END}]")
    print()
    print(f"  {'Ticker':4}  {'Source':5}  {'Start':10}  {'Start px':>10}  "
          f"{'End':10}  {'End px':>10}  {'CAGR':>8}  {'N bars':>7}")
    sep = f"  {'-'*4}  {'-'*5}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*8}  {'-'*7}"
    print(sep)

    all_cagrs = {}
    for ticker in ["SPY", "RSP"]:
        bars      = ibkr_data[ticker]["bars"]
        ibkr_d    = {str(b.date): b.close for b in bars} if bars else {}
        yf_d      = read_yf_csv(ticker)

        for label, d in [("IBKR", ibkr_d), ("YF", yf_d)]:
            if not d:
                print(f"  {ticker:4}  {label:5}  NO DATA")
                all_cagrs.setdefault(ticker, {})[label] = None
                continue
            sd, sp = nearest_on_or_after(d, RSP_INCEPTION)
            ed, ep = nearest_on_or_before(d, RECON_REF_END)
            if not sd:
                print(f"  {ticker:4}  {label:5}  DATE NOT FOUND")
                all_cagrs.setdefault(ticker, {})[label] = None
                continue
            c = cagr(sp, ep, sd, ed) * 100
            all_cagrs.setdefault(ticker, {})[label] = c
            print(f"  {ticker:4}  {label:5}  {sd:10}  {sp:10.4f}  "
                  f"{ed:10}  {ep:10.4f}  {c:7.3f}%  {len(d):>7}")

    print()
    print("  DELTA CHECK (threshold ±0.30pp):")
    gate_ok = True
    for ticker in ["SPY", "RSP"]:
        ic = all_cagrs.get(ticker, {}).get("IBKR")
        yc = all_cagrs.get(ticker, {}).get("YF")
        if ic is None or yc is None:
            status = "GAP — cannot cross-check"
            gate_ok = False
        else:
            delta = abs(ic - yc)
            ok    = delta <= 0.30
            if not ok: gate_ok = False
            status = f"IBKR={ic:.3f}%  YF={yc:.3f}%  delta={delta:.3f}pp  {'PASS' if ok else 'FAIL'}"
        print(f"  {ticker}: {status}")

    print()
    print(f"§1.5 GATE: {'PASS' if gate_ok else 'FAIL or PARTIAL'}")
    print("=" * 68)
    if gate_ok:
        print("STOP — reconciliation confirmed. Awaiting user approval before §2+.")

if __name__ == "__main__":
    main()
