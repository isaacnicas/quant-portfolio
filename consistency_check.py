"""
consistency_check.py
Daily automated consistency guard. Read-only -never writes to the order path.
Runs as the penultimate step in daily_routine_v2.bat (after git push, before "Routine complete")
so that C6 can verify today's push result.

CARDINAL RULE: can never halt or disrupt the daily routine.
  Each check is independently crash-wrapped.
  The whole script is crash-wrapped.
  Exits 0 always.

Output:
  logs/consistency_check.jsonl  -machine-readable daily record (append-only)
  stdout                        -captured to routine.log by the bat
  Email alert                   -on any unexpected FAIL via existing send_alert()
"""

import json
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE      = Path(r'C:\QuantTrading\TrendFollowing')
DASH_JSON = Path(r'C:\QuantTrading\quant-portfolio\data\dashboard_data.json')
DASH_HTML = Path(r'C:\QuantTrading\quant-portfolio\live-dashboard.html')
LOG_OUT   = BASE / 'logs' / 'consistency_check.jsonl'

# ── Import send_alert -fall back to stderr print so nothing can crash ─────────
try:
    sys.path.insert(0, str(BASE))
    from preflight_check import send_alert
except Exception as _import_err:
    def send_alert(subject, body):  # type: ignore[misc]
        print(f"[ALERT -email unavailable: {_import_err}]\n{subject}\n{body}",
              file=sys.stderr)


# ── Utilities ─────────────────────────────────────────────────────────────────

def _expected_date() -> date:
    """Most recent weekday -the date all routine outputs should carry."""
    d  = date.today()
    wd = d.weekday()
    if wd == 5: return d - timedelta(days=1)   # Sat → Fri
    if wd == 6: return d - timedelta(days=2)   # Sun → Fri
    return d


def _fresh(path: Path, days: int = 1) -> bool:
    """True if path was modified within `days` calendar days of the expected date."""
    if not path.exists():
        return False
    cutoff = _expected_date() - timedelta(days=days - 1)
    return datetime.fromtimestamp(path.stat().st_mtime).date() >= cutoff


def _mdate(path: Path) -> str:
    if not path.exists():
        return 'MISSING'
    return str(datetime.fromtimestamp(path.stat().st_mtime).date())


def _r(cid: str, name: str, status: str, detail: str) -> dict:
    return {'check': cid, 'name': name, 'status': status, 'detail': detail}


def _safe(cid: str, name: str, fn) -> dict:
    try:
        return fn()
    except Exception as exc:
        return _r(cid, name, 'FAIL', f'Check itself raised unexpectedly: {exc}')


# ── Check 1: Port Consistency ─────────────────────────────────────────────────

def check_1_ports() -> dict:
    """All IBKR-connecting scripts must auto-detect port via _port_open()."""
    HARDCODE_PATS = [
        re.compile(r"\bib\.connect\('127\.0\.0\.1',\s*(4002|7497)"),
        re.compile(r'\bPORT\s*=\s*(4002|7497)\b'),
    ]
    SKIP_MARKERS = ('_port_open', 'gateway_up')

    violations = []
    for pyfile in sorted(BASE.glob('*.py')):
        try:
            for lno, line in enumerate(pyfile.read_text(errors='replace').splitlines(), 1):
                if line.strip().startswith('#'):
                    continue
                if any(m in line for m in SKIP_MARKERS):
                    continue
                for pat in HARDCODE_PATS:
                    if pat.search(line):
                        violations.append(f'{pyfile.name}:{lno}')
                        break
        except Exception as e:
            violations.append(f'{pyfile.name}: unreadable ({e})')

    if violations:
        return _r('C1', 'Port Consistency', 'FAIL',
                  'Hardcoded port(s) found: ' + ', '.join(violations))
    return _r('C1', 'Port Consistency', 'PASS',
              'All IBKR-connecting scripts use _port_open() auto-detect')


# ── Check 2: Order Path Freshness ─────────────────────────────────────────────

def check_2_order_path() -> dict:
    """
    Staging (pending_orders.json) and submission (premarket.log) both healthy.
    Extends staging_check.py (which runs immediately at Step 7b) with a
    comprehensive end-of-day view that also covers the submission side.
    """
    ed     = _expected_date()
    issues = []
    n_orders = 0

    # ── Staging ───────────────────────────────────────────────────────────────
    pending = BASE / 'logs' / 'pending_orders.json'
    if not pending.exists():
        issues.append('pending_orders.json MISSING')
    else:
        mod = datetime.fromtimestamp(pending.stat().st_mtime).date()
        if mod < ed:
            issues.append(f'pending_orders.json stale mod-date {mod} (expected {ed})')
        else:
            try:
                orders = json.loads(pending.read_text())
                n_orders = len(orders)
                if orders:
                    sig_dates = {o.get('signal_date', '') for o in orders}
                    if not any(d >= ed.isoformat() for d in sig_dates):
                        issues.append(f'pending_orders.json signal_date {sig_dates} older than expected {ed}')
            except Exception as pe:
                issues.append(f'pending_orders.json parse error: {pe}')

    # ── Submission ─────────────────────────────────────────────────────────────
    premarket_log = BASE / 'logs' / 'premarket.log'
    if not premarket_log.exists():
        issues.append('premarket.log MISSING -submission has never run')
    else:
        mod = datetime.fromtimestamp(premarket_log.stat().st_mtime).date()
        if mod < ed:
            issues.append(f'premarket.log stale ({mod}) -submission may not have run')
        else:
            recent = premarket_log.read_text(errors='replace').splitlines()[-50:]
            if any('Traceback' in l for l in recent):
                issues.append('Traceback in recent premarket.log -submission script crashed')

    if issues:
        return _r('C2', 'Order Path Freshness', 'FAIL', '; '.join(issues))
    return _r('C2', 'Order Path Freshness', 'PASS',
              f'staging OK ({n_orders} orders, signal_date={ed}), submission OK (no crash)')


# ── Check 3: Routine Step Liveness ────────────────────────────────────────────

def check_3_step_liveness() -> dict:
    """Each routine step's expected output file must be fresh today."""
    # days=1: must be fresh today. days=7: weekly file, fresh within last 7 days.
    STEPS = [
        ('Step 1   prices.csv',             BASE / 'data' / 'prices.csv',                  1),
        ('Step 2b  trend_state.jsonl',      BASE / 'logs' / 'trend_state.jsonl',           1),
        ('Step 3   mr_positions.json',      BASE / 'logs' / 'mean_reversion_positions.json', 14),
        ('Step 3   mr_state.jsonl',         BASE / 'logs' / 'meanreversion_state.jsonl',   1),
        ('Step 4   vrp_state.jsonl',        BASE / 'logs' / 'vrp_state.jsonl',             1),
        ('Step 5   gate_state.jsonl',       BASE / 'logs' / 'gate_state.jsonl',            1),
        ('Step 6   portfolio_state.jsonl',  BASE / 'logs' / 'portfolio_state.jsonl',       1),
        ('Step 7   pending_orders.json',    BASE / 'logs' / 'pending_orders.json',         1),
        ('Step 8/9 dashboard_data.json',    DASH_JSON,                                     1),
    ]
    stale = []
    for label, path, days in STEPS:
        if not _fresh(path, days=days):
            stale.append(f'{label} [{_mdate(path)}]')

    if stale:
        return _r('C3', 'Step Liveness', 'FAIL',
                  'Missing/stale: ' + '; '.join(stale))
    return _r('C3', 'Step Liveness', 'PASS',
              f'All {len(STEPS)} expected step outputs fresh '
              f'(mr_positions.json uses 14-day window)')


# ── Check 4: Sleeve Invariants ────────────────────────────────────────────────

def check_4_sleeve_invariants() -> dict:
    """
    Per-sleeve state files must be fresh.
    VRP signals-but-no-order-path = KNOWN-GAP (gap #2).
    Trend state log absent = KNOWN-GAP (gap #3).
    Unexpected mismatch on any other sleeve = FAIL.
    """
    issues = []
    gaps   = []

    # MR state: must be fresh today. positions: weekly file, fresh within 14 days.
    if not _fresh(BASE / 'logs' / 'meanreversion_state.jsonl', days=1):
        issues.append(f'MR meanreversion_state.jsonl not fresh [{_mdate(BASE / "logs" / "meanreversion_state.jsonl")}]')
    if not _fresh(BASE / 'logs' / 'mean_reversion_positions.json', days=14):
        issues.append(f'MR mean_reversion_positions.json not fresh [{_mdate(BASE / "logs" / "mean_reversion_positions.json")}]')

    # VRP: state must be fresh. Order path live as of Phase C-2
    # (compute_vrp_order_list in order_engine.py; SVXY staged in pending_orders.json).
    vrp_state = BASE / 'logs' / 'vrp_state.jsonl'
    if not _fresh(vrp_state):
        issues.append(f'VRP vrp_state.jsonl not fresh [{_mdate(vrp_state)}]')

    # Trend: state log is now written by Step 2b (trend_following_strategy.py).
    # Check freshness exactly like MR/VRP.
    if not _fresh(BASE / 'logs' / 'trend_state.jsonl', days=1):
        issues.append(f'Trend trend_state.jsonl not fresh [{_mdate(BASE / "logs" / "trend_state.jsonl")}]')

    if issues:
        detail = '; '.join(issues)
        if gaps:
            detail += ' | KNOWN-GAPS: ' + '; '.join(gaps)
        return _r('C4', 'Sleeve Invariants', 'FAIL', detail)

    if gaps:
        return _r('C4', 'Sleeve Invariants', 'KNOWN-GAP',
                  'MR/VRP state fresh; documented gaps: ' + ' | '.join(gaps))

    return _r('C4', 'Sleeve Invariants', 'PASS',
              'All sleeve state files fresh, no unexpected mismatches')


# ── Check 5: Weight Consistency ───────────────────────────────────────────────

def check_5_weights() -> dict:
    """
    Configuration drift guard:
      MR_SLEEVE_FRACTION must be 0.10 in order_engine.py (intentional locked choice).
      Trend target_vol must be 0.15 in signal_engine.py.
      VRP must have 0 SVXY orders in pending_orders.json (no order path yet).
    """
    issues = []

    # MR fraction -appears at two sites in order_engine.py; both must be 0.10
    oe_text = (BASE / 'order_engine.py').read_text()
    mr_matches = re.findall(r'MR_SLEEVE_FRACTION\s*=\s*([\d.]+)', oe_text)
    if not mr_matches:
        issues.append('MR_SLEEVE_FRACTION not found in order_engine.py')
    else:
        drifted = [v for v in mr_matches if abs(float(v) - 0.10) > 1e-6]
        if drifted:
            issues.append(f'MR_SLEEVE_FRACTION drifted: {drifted} (expected [0.10, 0.10])')

    # Trend target_vol
    se_text = (BASE / 'signal_engine.py').read_text()
    tv = re.search(r"'target_vol'\s*:\s*([\d.]+)", se_text)
    if not tv:
        issues.append("target_vol not found in signal_engine.py CFG")
    elif abs(float(tv.group(1)) - 0.15) > 1e-6:
        issues.append(f"target_vol drifted: {tv.group(1)} (expected 0.15)")

    if issues:
        return _r('C5', 'Weight Consistency', 'FAIL', '; '.join(issues))
    return _r('C5', 'Weight Consistency', 'PASS',
              'MR_SLEEVE_FRACTION=0.10, Trend target_vol=0.15')


# ── Check 6: Dashboard Pipeline Health ────────────────────────────────────────

def check_6_dashboard() -> dict:
    """
    dashboard_data.json fresh, last git push succeeded,
    cache-bust (Date.now()) present in live-dashboard.html.
    """
    issues = []

    # JSON freshness
    if not _fresh(DASH_JSON):
        issues.append(f'dashboard_data.json {_mdate(DASH_JSON)} -not fresh')

    # Git push result -check repo state directly rather than parsing log text.
    # This catches manual pushes and routine pushes equally.
    portfolio_dir = DASH_JSON.parent.parent  # C:\QuantTrading\quant-portfolio
    try:
        gs = subprocess.run(
            ['git', '-C', str(portfolio_dir), 'status', '--porcelain', '-b'],
            capture_output=True, text=True, timeout=5
        )
        branch_line = gs.stdout.split('\n')[0] if gs.stdout else ''
        if 'ahead' in branch_line and 'behind' in branch_line:
            issues.append('quant-portfolio is DIVERGED from origin/main')
        elif 'ahead' in branch_line:
            n = re.search(r'ahead (\d+)', branch_line)
            count = n.group(1) if n else '?'
            issues.append(f'quant-portfolio has {count} unpushed commit(s)')
        # 'behind' = remote ahead, unusual but not a push failure
        # clean (no ahead/behind) = last push succeeded
    except Exception as ge:
        issues.append(f'git status check failed: {ge}')

    # Cache-bust presence
    if not DASH_HTML.exists():
        issues.append('live-dashboard.html not found in quant-portfolio')
    elif 'Date.now()' not in DASH_HTML.read_text(errors='replace'):
        issues.append('live-dashboard.html: cache-bust (Date.now()) missing from fetch call')

    if issues:
        return _r('C6', 'Dashboard Health', 'FAIL', '; '.join(issues))
    return _r('C6', 'Dashboard Health', 'PASS',
              'dashboard_data.json fresh, push succeeded, cache-bust present')


# ── Check 7: Known Gap Register ───────────────────────────────────────────────
#
# Resolved gaps (removed from register — no longer tracked):
#   Gap #2  VRP no order path        — Phase C-2: compute_vrp_order_list +
#                                       submit_vrp_orders added to order_engine.py;
#                                       SVXY staged in pending_orders.json
#   Gap #6  PIT date-guard           — Phase C-4: _load_recent_state() now filters
#                                       date < today structurally in both own-sleeve
#                                       and cross-sleeve reads
#
# Gap #3 (Trend forecast interface) resolved in Phase C-3: Step 2b added to
# daily_routine_v2.bat; trend_state.jsonl written daily.


def check_7_known_gaps() -> dict:
    """
    Phase-C architectural gaps — expected-broken, tracked daily.
    FAIL if a gap unexpectedly resolves (Phase-C work done without updating this register).
    Only Gap #5 remains: ERC in observation mode (deliberate, resolves in Phase E).
    """
    GAPS = [
        ('Gap #5 ERC observation mode',
         lambda: 'ERC_LIVE_SIZING = False' in (BASE / 'portfolio_risk.py').read_text(errors='replace'),
         'ERC in observation mode (ERC_LIVE_SIZING=False) - computes and logs weights but does '
         'not size orders; MR uses hardcoded 10% in order_engine.py, not ERC weights. '
         'Resolves in Phase E after logged weights prove stable/sane over defined period.'),
    ]

    confirmed = []
    resolved  = []
    for label, still_broken, desc in GAPS:
        try:
            if still_broken():
                confirmed.append(f'{label}: {desc}')
            else:
                resolved.append(f'{label} may be resolved -update SYSTEM_ARCHITECTURE.md and this register')
        except Exception as e:
            confirmed.append(f'{label}: verification raised ({e}) -treating as still open')

    if resolved:
        return _r('C7', 'Known Gap Register', 'FAIL',
                  'Gap state changed unexpectedly: ' + '; '.join(resolved))
    return _r('C7', 'Known Gap Register', 'KNOWN-GAP',
              f'{len(confirmed)} Phase-C gaps tracked: ' + ' | '.join(confirmed))


# ── Check 8: ERC Maturity Status ──────────────────────────────────────────────

def check_8_erc_maturity() -> dict:
    """
    ERC observation-mode maturity check — STATUS only, never an unexpected FAIL.

    Tracks how many unique trading dates each sleeve has accumulated toward
    the 21-day minimum for full-window ERC estimation. Three states:
      IMMATURE : no sleeve has ≥ 21 days  — weights are placeholders, do not act on them
      MATURING : some sleeves have ≥ 21 days, some don't — partially real, still not decision-ready
      MATURE   : all active sleeves ≥ 21 days AND portfolio_vol_ex_ante computed
                 → weights are real; Phase-E decision can be reviewed

    IMMATURE / MATURING → KNOWN-GAP (expected, not an alert).
    MATURE → PASS (transition is the signal to review ERC for Phase-E authority).

    Threshold = 21 days (matches PortfolioRiskManager.lookback_days).
    History count = unique calendar dates in each sleeve's state log
    (multiple same-day writes are deduplicated, so this is true trading-day count).
    """
    ERC_LOOKBACK = 21   # must match PortfolioRiskManager.lookback_days

    SLEEVE_LOGS = {
        "Trend":         BASE / "logs" / "trend_state.jsonl",
        "MeanReversion": BASE / "logs" / "meanreversion_state.jsonl",
        "VRP":           BASE / "logs" / "vrp_state.jsonl",
    }

    counts: dict[str, int] = {}
    for sleeve, path in SLEEVE_LOGS.items():
        if not path.exists():
            counts[sleeve] = 0
            continue
        dates: set[str] = set()
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line).get("date", "")
                    if d:
                        dates.add(d)
                except json.JSONDecodeError:
                    continue
        except IOError:
            pass
        counts[sleeve] = len(dates)

    # Read latest portfolio_state.jsonl for portfolio_vol_ex_ante
    pv_ex_ante = None
    ps_path = BASE / "logs" / "portfolio_state.jsonl"
    if ps_path.exists():
        try:
            lines = [l.strip() for l in
                     ps_path.read_text(encoding="utf-8").splitlines() if l.strip()]
            if lines:
                pv_ex_ante = json.loads(lines[-1]).get("portfolio_vol_ex_ante")
        except Exception:
            pass

    sleeves    = list(SLEEVE_LOGS.keys())
    all_mature = all(counts[s] >= ERC_LOOKBACK for s in sleeves)
    any_mature = any(counts[s] >= ERC_LOOKBACK for s in sleeves)

    if all_mature and pv_ex_ante is not None:
        maturity = "MATURE"
    elif any_mature:
        maturity = "MATURING"
    else:
        maturity = "IMMATURE"

    per_sleeve = ", ".join(f"{s}={counts[s]}/{ERC_LOOKBACK}d"
                           for s in sleeves)
    pv_str     = f"{pv_ex_ante:.1%}" if pv_ex_ante else "N/A"

    if maturity == "MATURE":
        note = "All sleeves at full history — ERC weights trustworthy; review for Phase-E authority."
    elif maturity == "MATURING":
        note = "Some sleeves still thin — ERC weights partially real; continue accumulating."
    else:
        note = "ERC weights are placeholders; observation period in progress (expected)."

    detail = (f"maturity={maturity}  threshold={ERC_LOOKBACK}d  "
              f"portfolio_vol_ex_ante={pv_str}  "
              f"per-sleeve: [{per_sleeve}].  {note}")

    if maturity == "MATURE":
        return _r("C8", "ERC Maturity", "PASS", detail)
    return _r("C8", "ERC Maturity", "KNOWN-GAP", detail)


# ── Check 9: Regime Health ────────────────────────────────────────────────────

def check_9_regime_health() -> dict:
    """
    Two-part regime computation sanity guard:

    Part 1 — field validation: dashboard_data.json must contain all four
    regime fields (regime_scalar, raw_bull_score, leverage_scalar,
    fast_exit_triggered) with values in expected ranges. Missing or
    out-of-range values indicate monitor.py failed mid-run or the JSON
    schema drifted.

    Part 2 — prices.csv last-row date: the CONTENT of prices.csv must be
    current (last data row matches today's expected trading date), not just
    the file's modification timestamp. This specifically catches the scenario
    where prices.csv was NOT updated because IB Gateway was offline, but
    monitor.py still ran against prior-day price data — producing a stale
    regime value with no visible signal in C3's file-mtime check alone.

    FAIL conditions: missing/out-of-range regime fields, or prices.csv last
    date older than expected trading date.
    Not a KNOWN-GAP: once the pipeline is running there is no reason for
    regime data to ever legitimately be missing or stale.
    """
    ed     = _expected_date()
    issues = []

    # ── Part 1: regime field validation ───────────────────────────────────────
    if not DASH_JSON.exists():
        return _r('C9', 'Regime Health', 'FAIL', 'dashboard_data.json missing')

    try:
        regime = json.loads(DASH_JSON.read_text()).get('regime', {})

        rs  = regime.get('regime_scalar')
        rbs = regime.get('raw_bull_score')
        lev = regime.get('leverage_scalar')
        fxt = regime.get('fast_exit_triggered')

        if rs is None:
            issues.append('regime_scalar missing from dashboard_data.json')
        elif not (0.60 <= float(rs) <= 1.0):
            issues.append(f'regime_scalar={rs} out of range [0.60, 1.0]')

        if rbs is None:
            issues.append('raw_bull_score missing from dashboard_data.json')
        elif not (0.0 <= float(rbs) <= 1.0):
            issues.append(f'raw_bull_score={rbs} out of range [0, 1]')

        if lev is None:
            issues.append('leverage_scalar missing from dashboard_data.json')
        elif not (0.5 <= float(lev) <= 2.0):
            issues.append(f'leverage_scalar={lev} out of expected range [0.5, 2.0]')

        if fxt is None:
            issues.append('fast_exit_triggered missing from dashboard_data.json')
        elif not isinstance(fxt, bool):
            issues.append(f'fast_exit_triggered is not boolean: {type(fxt).__name__}')

    except Exception as e:
        issues.append(f'dashboard_data.json regime parse error: {e}')

    # ── Part 2: prices.csv last-row date check ────────────────────────────────
    prices_csv = BASE / 'data' / 'prices.csv'
    if not prices_csv.exists():
        issues.append('prices.csv missing')
    else:
        try:
            with open(prices_csv, 'rb') as fh:
                fh.seek(0, 2)
                fh.seek(max(0, fh.tell() - 256), 0)
                tail = fh.read().decode('utf-8', errors='replace')
            last_line = [ln.strip() for ln in tail.splitlines() if ln.strip()][-1]
            last_date_str = last_line.split(',')[0]
            last_date = date.fromisoformat(last_date_str)
            if last_date < ed:
                issues.append(
                    f'prices.csv last row date={last_date} but expected={ed} '
                    f'— regime was computed from stale prices (IB offline scenario)'
                )
        except Exception as e:
            issues.append(f'prices.csv last-row date check failed: {e}')

    if issues:
        return _r('C9', 'Regime Health', 'FAIL', '; '.join(issues))

    rs_v  = round(float(regime.get('regime_scalar', 0)), 3)
    rbs_v = round(float(regime.get('raw_bull_score', 0)), 3)
    lev_v = round(float(regime.get('leverage_scalar', 0)), 1)
    return _r('C9', 'Regime Health', 'PASS',
              f'regime_scalar={rs_v}, raw_bull_score={rbs_v}, '
              f'leverage_scalar={lev_v}x, prices.csv date={ed}')


# ── Check 10: Rebase Stuck State ──────────────────────────────────────────────

def check_10_rebase_stuck() -> dict:
    """
    Detects whether quant-portfolio is currently mid-rebase (presence of
    .git/rebase-merge or .git/rebase-apply).

    A stuck rebase -- e.g. from a git pull --rebase conflict during Step 10
    of daily_routine_v2.bat, most often triggered by a manual GitHub web
    upload touching the same file the automated routine has pending changes
    for -- blocks all future dashboard pushes until a human manually resolves
    it. This is a distinct, actionable alert rather than something to infer
    from a generic "dashboard not fresh" (C6) failure.

    The git rebase --abort fix (commit 5ce7887) returns the repo to a clean
    state immediately after a failed rebase, so this should not persist past
    the same day the conflict occurred. This check still adds value for the
    same-day window between the failed rebase and the next routine run
    clearing it.
    """
    portfolio_dir = DASH_JSON.parent.parent  # C:\QuantTrading\quant-portfolio
    git_dir       = portfolio_dir / '.git'
    rebase_merge  = git_dir / 'rebase-merge'
    rebase_apply  = git_dir / 'rebase-apply'

    stuck = rebase_merge if rebase_merge.exists() else (
             rebase_apply if rebase_apply.exists() else None)

    if stuck is not None:
        return _r('C10', 'Rebase Stuck State', 'FAIL',
                  f'Repo stuck mid-rebase ({stuck.name}) -- manual intervention '
                  f'required: git rebase --abort then resolve conflict manually.')
    return _r('C10', 'Rebase Stuck State', 'PASS',
              'quant-portfolio not mid-rebase')


# ── Main ──────────────────────────────────────────────────────────────────────

CHECKS = [
    ('C1', 'Port Consistency',     check_1_ports),
    ('C2', 'Order Path Freshness', check_2_order_path),
    ('C3', 'Step Liveness',        check_3_step_liveness),
    ('C4', 'Sleeve Invariants',    check_4_sleeve_invariants),
    ('C5', 'Weight Consistency',   check_5_weights),
    ('C6', 'Dashboard Health',     check_6_dashboard),
    ('C7', 'Known Gap Register',   check_7_known_gaps),
    ('C8', 'ERC Maturity',         check_8_erc_maturity),
    ('C9', 'Regime Health',        check_9_regime_health),
    ('C10', 'Rebase Stuck State',  check_10_rebase_stuck),
]


def main():
    now = datetime.now()
    print(f"\n{'=' * 60}")
    print(f"CONSISTENCY CHECK  |  {now.strftime('%Y-%m-%d %H:%M')}  |  {_expected_date()} signals")
    print('=' * 60)

    results = []
    for cid, name, fn in CHECKS:
        result = _safe(cid, name, fn)
        results.append(result)
        status = result['status']
        icon   = {'PASS': '+', 'FAIL': '!', 'KNOWN-GAP': '~'}.get(status, '?')
        print(f"  [{icon}] {cid}  {name:<25}  {status}")
        if status != 'PASS':
            # Truncate long detail for the log -full detail is in the JSONL
            brief = result['detail']
            print(f"       {brief[:140]}{'...' if len(brief) > 140 else ''}")

    fails      = [r for r in results if r['status'] == 'FAIL']
    known_gaps = [r for r in results if r['status'] == 'KNOWN-GAP']
    n_pass     = len(results) - len(fails) - len(known_gaps)

    summary_line = (
        f"ALL CHECKS PASS ({len(known_gaps)} known gap{'s' if len(known_gaps) != 1 else ''} tracked)"
        if not fails else
        f"{len(fails)} FAIL{'s' if len(fails) != 1 else ''}, {len(known_gaps)} known gap{'s' if len(known_gaps) != 1 else ''}"
    )
    print(f"\n[CONSISTENCY CHECK] {summary_line} - {now.strftime('%Y-%m-%d %H:%M')}")

    # ── Write JSONL record ────────────────────────────────────────────────────
    record = {
        'timestamp'    : now.isoformat(),
        'expected_date': _expected_date().isoformat(),
        'checks'       : {r['check']: {'status': r['status'], 'detail': r['detail']}
                          for r in results},
        'summary'      : {
            'overall'         : 'FAIL' if fails else ('KNOWN-GAP' if known_gaps else 'PASS'),
            'pass'            : n_pass,
            'fail'            : len(fails),
            'known_gap'       : len(known_gaps),
            'unexpected_fails': len(fails),
            'label'           : summary_line,
        },
    }
    LOG_OUT.parent.mkdir(parents=True, exist_ok=True)
    with LOG_OUT.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(record) + '\n')

    # ── Email on any unexpected FAIL ──────────────────────────────────────────
    if fails:
        subject = (f"[QuantTrading] CONSISTENCY CHECK -{len(fails)} FAIL(s) "
                   f"on {now.date().isoformat()}")
        body = f"Daily consistency check found {len(fails)} unexpected failure(s):\n\n"
        for r in fails:
            body += f"[{r['check']}] {r['name']}\n  {r['detail']}\n\n"
        body += f"Full log: {LOG_OUT}\nRoutine log: {BASE / 'logs' / 'routine.log'}\n"
        body += "\nKnown gaps (these are NOT alerts):\n"
        for r in known_gaps:
            body += f"  [{r['check']}] {r['detail'][:120]}\n"
        send_alert(subject, body)
        print(f"[CONSISTENCY CHECK] Alert email sent ({len(fails)} fail(s))")


if __name__ == '__main__':
    try:
        main()
    except Exception as _top_err:
        print(f"[CONSISTENCY CHECK] CRITICAL: script itself crashed ({_top_err}) -guard down",
              file=sys.stderr)
        try:
            record = {
                'timestamp'    : datetime.now().isoformat(),
                'expected_date': _expected_date().isoformat(),
                'checks'       : {'CRASH': {'status': 'FAIL', 'detail': str(_top_err)}},
                'summary'      : {'overall': 'FAIL', 'pass': 0, 'fail': 1,
                                  'known_gap': 0, 'unexpected_fails': 1,
                                  'label': f'Script crashed: {_top_err}'},
            }
            LOG_OUT.parent.mkdir(parents=True, exist_ok=True)
            with LOG_OUT.open('a', encoding='utf-8') as fh:
                fh.write(json.dumps(record) + '\n')
        except Exception:
            pass
    sys.exit(0)  # never halt the bat
