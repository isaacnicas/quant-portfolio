import pandas as pd
import numpy as np
from signal_engine import generate_today_signal, CFG, equity_tickers, divers_tickers, UNIVERSE


def size_today_positions(signal_result, prev_weights=None):
    """
    Converts today's signal into target portfolio weights.

    prev_weights: dict of {ticker: weight} from the last rebalance,
                  used for the tiered dead-band filter.
                  Pass None on the very first run.
    """
    combined_signal = signal_result['combined_signal']
    regime_scalar   = signal_result['regime_scalar']
    leverage_scalar = signal_result['leverage_scalar']
    returns         = signal_result['returns']

    tickers = combined_signal.index.tolist()

    if prev_weights is None:
        prev_weights = pd.Series(0.0, index=tickers)
    else:
        prev_weights = pd.Series(prev_weights).reindex(tickers).fillna(0.0)

    # Asset volatility — same EWM method as the backtest
    asset_vol = returns.ewm(span=CFG['vol_lookback']).std().iloc[-1] * np.sqrt(252)
    asset_vol = asset_vol.replace(0, np.nan)

    sig = combined_signal.fillna(0)

    # Vol-target sizing, long/flat only
    raw = (sig * (CFG['target_vol'] / asset_vol)).fillna(0).clip(lower=0)

    # Apply regime scalar
    raw = raw * regime_scalar

    # Diversifier cap: keep diversifiers at or below 30% of gross exposure
    eq_gross    = raw[equity_tickers].sum()
    div_gross   = raw[divers_tickers].sum()
    total_gross = eq_gross + div_gross
    if total_gross > 0 and div_gross / (total_gross + 1e-10) > CFG['divers_gross_cap']:
        scale_div = (CFG['divers_gross_cap'] * total_gross) / (div_gross + 1e-10)
        for t in divers_tickers:
            if t in raw.index:
                raw[t] *= scale_div

    # Portfolio leverage cap
    gross = raw.abs().sum()
    effective_cap = min(leverage_scalar, CFG['max_leverage'])
    if gross > effective_cap:
        raw = raw * (effective_cap / gross)

    # Tiered dead-band: only trade if the change exceeds the asset-class threshold
    final = prev_weights.copy()
    for t in tickers:
        if t in CFG['lev_etfs']:
            threshold = CFG['dead_band_lev']
        elif UNIVERSE.get(t, 'equity') == 'equity':
            threshold = CFG['dead_band_equity']
        else:
            threshold = CFG['dead_band_macro']
        if abs(raw[t] - prev_weights.get(t, 0.0)) > threshold:
            final[t] = raw[t]

    return final


if __name__ == '__main__':
    signal_result  = generate_today_signal()
    target_weights = size_today_positions(signal_result, prev_weights=None)

    print(f"\n=== Target Portfolio Weights for {signal_result['date'].date()} ===")
    print(target_weights.sort_values(ascending=False).round(4))
    print(f"\nGross exposure:       {target_weights.abs().sum():.2%}")
    print(f"Equity exposure:      {target_weights[equity_tickers].sum():.2%}")
    print(f"Diversifier exposure: {target_weights[divers_tickers].sum():.2%}")
