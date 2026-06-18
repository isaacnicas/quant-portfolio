import pandas as pd
import numpy as np
from scipy.stats import rankdata

# ── Config — mirrors the backtest notebook exactly ───────────────────────────
UNIVERSE = {
    'SPY': 'equity', 'QQQ': 'equity', 'IWM': 'equity',
    'XLK': 'equity', 'SMH': 'equity',
    'EEM': 'equity', 'EWJ': 'equity',
    'TLT': 'bond',   'IEF': 'bond',
    'GLD': 'commodity',
    'FXE': 'fx',     'FXY': 'fx',
}

CFG = {
    'trend_horizons'      : [21, 63, 126, 252],
    'vol_lookback'        : 63,
    'target_vol'          : 0.15,
    'equity_gross_cap'    : 0.70,
    'divers_gross_cap'    : 0.30,
    'max_leverage'        : 2.0,
    'vix_short'           : 63,
    'vix_long'            : 252,
    'equity_ma'           : 200,
    'dead_band_macro'     : 0.01,
    'dead_band_equity'    : 0.02,
    'dead_band_lev'       : 0.04,
    'lev_etfs'            : {'TQQQ', 'UPRO', 'SQQQ', 'SPXU'},
    'regime_floor'        : 0.60,
    'bull_leverage'       : 1.5,
    'bear_leverage'       : 0.8,
    'bull_lev_thresh'     : 0.55,
    'w_tsmom'             : 0.44,
    'w_cs'                : 0.56,
    'fast_exit_lookback'  : 10,
    'fast_exit_threshold' : -0.05,
    'fast_exit_floor'     : 0.60,
    'reentry_spy_days'    : 5,
}

equity_tickers = [t for t, c in UNIVERSE.items() if c == 'equity']
divers_tickers = [t for t, c in UNIVERSE.items() if c != 'equity']


def tsmom_signals(prices, horizons, vol_lookback=63):
    daily_ret = prices.pct_change()
    ewm_vol   = daily_ret.ewm(span=vol_lookback).std() * np.sqrt(252)
    ewm_vol   = ewm_vol.replace(0, np.nan).ffill()
    signal_list = []
    for h in horizons:
        ret_h = prices.pct_change(h).shift(5)
        signal_list.append(ret_h / ewm_vol)
    ensemble = sum(signal_list) / len(signal_list)
    return ensemble.clip(-2, 2) / 2


def cs_momentum_signals(prices, lookback=126):
    ret_h = prices.pct_change(lookback).shift(5)
    def rank_row(row):
        valid = row.dropna()
        if len(valid) < 2:
            return pd.Series(np.nan, index=row.index)
        ranks = pd.Series(rankdata(valid), index=valid.index)
        return (2*(ranks-1)/(len(valid)-1)-1).reindex(row.index)
    return ret_h.apply(rank_row, axis=1)


def build_regime(vix, equity_price, vix_short=63, vix_long=252, ma_window=200,
                 floor=0.60, bull_lev=1.5, bear_lev=0.8, bull_thresh=0.55):
    vix_al       = vix.reindex(equity_price.index).ffill()
    ma           = equity_price.rolling(ma_window).mean()
    price_bull   = (equity_price > ma).astype(float)
    vix_short_ma = vix_al.rolling(vix_short).mean()
    vix_long_ma  = vix_al.rolling(vix_long).mean()
    vol_calm     = (vix_short_ma < vix_long_ma).astype(float)
    raw_bull_score  = (0.6 * price_bull + 0.4 * vol_calm).rolling(10).mean()
    regime_scalar   = (floor + (1.0 - floor) * raw_bull_score).clip(floor, 1.0)
    lev_values      = raw_bull_score.apply(
        lambda x: bull_lev if x > bull_thresh else bear_lev)
    leverage_scalar = lev_values.rolling(5).mean()
    return regime_scalar, leverage_scalar, raw_bull_score


def check_fast_exit(returns, spy_col='SPY', lookback=10, threshold=-0.05):
    spy_roll = (1 + returns[spy_col]).rolling(lookback).apply(np.prod, raw=True) - 1
    spy_roll = spy_roll.fillna(0).rolling(2).mean()
    return bool(spy_roll.iloc[-1] < threshold)


def check_reentry_signal(returns, combined_signal, spy_col='SPY', spy_days=5):
    spy_roll  = (1 + returns[spy_col]).rolling(spy_days).apply(np.prod, raw=True) - 1
    spy_trend = combined_signal[spy_col].iloc[-1]
    return bool(spy_roll.iloc[-1] > 0 and spy_trend > 0)


def generate_today_signal():
    prices = pd.read_csv('data/prices.csv', index_col='date', parse_dates=True)
    vix    = prices['VIX']
    prices = prices.drop(columns=['VIX'])
    returns = prices.pct_change()

    sig_tsmom = tsmom_signals(prices, CFG['trend_horizons'],
                               CFG['vol_lookback']).fillna(0)
    sig_cs    = cs_momentum_signals(prices).fillna(0)
    combined_signal = CFG['w_tsmom'] * sig_tsmom + CFG['w_cs'] * sig_cs

    regime_scalar, leverage_scalar, raw_bull_score = build_regime(
        vix, prices['SPY'],
        CFG['vix_short'], CFG['vix_long'], CFG['equity_ma'],
        CFG['regime_floor'], CFG['bull_leverage'],
        CFG['bear_leverage'], CFG['bull_lev_thresh']
    )

    fast_exit_triggered = check_fast_exit(
        returns, lookback=CFG['fast_exit_lookback'],
        threshold=CFG['fast_exit_threshold'])

    reentry_signal = check_reentry_signal(
        returns, combined_signal, spy_days=CFG['reentry_spy_days'])

    today = prices.index[-1]
    print(f"\n=== Signal for {today.date()} ===")
    print(f"Raw bull score:    {raw_bull_score.iloc[-1]:.3f}")
    print(f"Regime scalar:     {regime_scalar.iloc[-1]:.3f}")
    print(f"Leverage scalar:   {leverage_scalar.iloc[-1]:.3f}x")
    print(f"Fast-exit triggered today: {fast_exit_triggered}")
    print(f"Re-entry signal active:    {reentry_signal}")
    print(f"\nCombined signal by asset (today):")
    print(combined_signal.iloc[-1].sort_values(ascending=False).round(3))

    return {
        'date'               : today,
        'combined_signal'    : combined_signal.iloc[-1],
        'regime_scalar'      : regime_scalar.iloc[-1],
        'leverage_scalar'    : leverage_scalar.iloc[-1],
        'fast_exit_triggered': fast_exit_triggered,
        'reentry_signal'     : reentry_signal,
        'returns'            : returns,
    }


if __name__ == '__main__':
    generate_today_signal()
