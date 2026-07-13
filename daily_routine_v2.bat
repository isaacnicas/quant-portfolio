@echo off
SET PYTHONIOENCODING=utf-8
REM ============================================================
REM daily_routine.bat  -  Multi-Strategy Pipeline
REM Runs Mon-Fri at 4:15 PM ET via Task Scheduler
REM Account: DUP447680  |  Port: auto-detect (Gateway 4002 preferred, TWS 7497 fallback)
REM ============================================================
REM
REM PHASE 1 ADDITIONS:
REM   Step 5 - governance_gates.py   VIX gate check
REM   Step 6 - portfolio_risk.py     ERC weights + vol target
REM   Step 9 - multi_strategy_monitor.py  blended dashboard
REM
REM IMPORTANT: Steps 5 and 6 must run BEFORE order_engine.py
REM so gate state is available to all strategies at execution time.
REM ============================================================

SET PYTHON=py -3.14
SET BASE=C:\QuantTrading\TrendFollowing
SET LOG=%BASE%\logs

REM Create log dir if it doesn't exist
if not exist "%LOG%" mkdir "%LOG%"

echo [%DATE% %TIME%] Starting multi-strategy daily routine >> "%LOG%\routine.log"

REM -- Step 0: Pre-flight connection check --
echo [Step 0] Pre-flight connection check...
%PYTHON% "%BASE%\preflight_check.py" >> "%LOG%\routine.log" 2>&1
if errorlevel 1 (
    echo [CRITICAL] Pre-flight check failed - IBKR unreachable, halting >> "%LOG%\routine.log"
    echo [CRITICAL] Pre-flight check failed - IBKR unreachable, halting
    goto :end
)

REM -- Step 1: Price data --
echo [Step 1] Fetching price data...
%PYTHON% "%BASE%\data_feed.py" >> "%LOG%\routine.log" 2>&1
if errorlevel 1 (
    echo [WARN] data_feed.py reported an error >> "%LOG%\routine.log"
)

REM -- Step 2: Trend signals --
echo [Step 2] Computing trend signals...
%PYTHON% "%BASE%\signal_engine.py" >> "%LOG%\routine.log" 2>&1

REM -- Step 2b: Trend forecast interface + state log (additive, crash-safe) --
REM Delegates to the same generate_today_signal() used by signal_engine.py and
REM order_engine.py — signals byte-identical. Writes trend_state.jsonl and
REM sleeve_forecasts.jsonl. A failure here logs a warning and never halts.
echo [Step 2b] Emitting Trend forecast and state log...
%PYTHON% "%BASE%\trend_following_strategy.py" >> "%LOG%\routine.log" 2>&1

REM -- Step 3: Mean reversion signals --
echo [Step 3] Computing mean reversion signals...
%PYTHON% "%BASE%\mean_reversion_strategy.py" >> "%LOG%\routine.log" 2>&1

REM -- Step 4: VRP signals --
echo [Step 4] Computing VRP signals...
%PYTHON% "%BASE%\vrp_strategy.py" --signal >> "%LOG%\routine.log" 2>&1

REM -- Step 5: Governance gate check --
REM Pass ISM PMI manually if known; omit flag to skip macro overlay
REM Example with macro data: --ism 52.1 --credit 320 --yc 0.45
echo [Step 5] Running governance gate check...
%PYTHON% "%BASE%\governance_gates.py" >> "%LOG%\routine.log" 2>&1
if errorlevel 1 (
    echo [CRITICAL] Governance gate check failed >> "%LOG%\routine.log"
    echo [CRITICAL] Halting routine - investigate before proceeding
    goto :end
)

REM -- Step 6: Portfolio risk weights --
echo [Step 6] Computing ERC weights and vol scalar...
%PYTHON% "%BASE%\portfolio_risk.py" >> "%LOG%\routine.log" 2>&1

REM -- Step 7: Stage orders (signals-only) --
REM Orders submitted at 7:00 AM by premarket_submit.bat via Task Scheduler
echo [Step 7] Staging orders (signals-only, no submission)...
%PYTHON% "%BASE%\order_engine.py" --signals-only >> "%LOG%\routine.log" 2>&1

REM -- Step 7b: Validate order staging freshness --
REM Alerts if pending_orders.json wasn't updated today (signals staging failure).
REM Crash-safe: exits 0 on internal error so it cannot halt the routine.
echo [Step 7b] Validating order staging freshness...
%PYTHON% "%BASE%\staging_check.py" >> "%LOG%\routine.log" 2>&1

REM -- Step 8: NAV monitor --
echo [Step 8] Updating NAV and positions...
%PYTHON% "%BASE%\monitor.py" >> "%LOG%\routine.log" 2>&1

REM -- Step 9: Multi-strategy dashboard --
echo [Step 9] Writing multi-strategy dashboard block...
%PYTHON% "%BASE%\multi_strategy_monitor.py" >> "%LOG%\routine.log" 2>&1

REM -- Step 10: Push to GitHub --
echo [Step 10] Pushing dashboard data to GitHub...
cd /d "C:\QuantTrading\quant-portfolio"
git add data/dashboard_data.json data/last_positions.json data/live_performance.csv >> "%LOG%\routine.log" 2>&1
git commit -m "daily update %DATE%" >> "%LOG%\routine.log" 2>&1

SET PUSH_STATUS=OK
git pull --rebase origin main >> "%LOG%\routine.log" 2>&1
if errorlevel 1 (
    echo [WARN] git pull --rebase failed - manual conflict resolution needed, push skipped >> "%LOG%\routine.log" 2>&1
    REM Without this abort, the repo is left mid-rebase and every subsequent
    REM day's git add/commit runs against a broken, conflicted state -- the
    REM push stays blocked indefinitely instead of just for today.
    git rebase --abort >> "%LOG%\routine.log" 2>&1
    SET PUSH_STATUS=REBASE_FAILED
)

if "%PUSH_STATUS%"=="OK" (
    git push origin main >> "%LOG%\routine.log" 2>&1
    if errorlevel 1 (
        SET PUSH_STATUS=PUSH_FAILED
    )
)

if "%PUSH_STATUS%"=="OK" (
    echo [Step 10] Dashboard pushed to GitHub Pages >> "%LOG%\routine.log" 2>&1
) else if "%PUSH_STATUS%"=="PUSH_FAILED" (
    echo [WARN] git push failed - origin may be ahead, pull manually >> "%LOG%\routine.log" 2>&1
)

REM -- Step 10b: Daily consistency check --
REM Runs AFTER git push so C6 can verify today's push result in routine.log.
REM Crash-safe: always exits 0, never halts the routine.
echo [Step 10b] Running daily consistency check...
cd /d "%BASE%"
%PYTHON% "%BASE%\consistency_check.py" >> "%LOG%\routine.log" 2>&1

echo [%DATE% %TIME%] Routine complete >> "%LOG%\routine.log"
echo All steps complete.

:end
