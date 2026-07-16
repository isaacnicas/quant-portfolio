import json
import os
from datetime import date, datetime, timezone

import pandas as pd
import numpy as np
from signal_engine import generate_today_signal, CFG, equity_tickers, divers_tickers, UNIVERSE

# ── Tech3 cluster penalty (SHADOW MODE ONLY) ────────────────────────────────
# Selected via pre-registered calibration (docs/tech_cluster_penalty_prereg.md,
# docs/tech_cluster_penalty_results.md): Candidate B (Effective Number of
# Bets basis), F_B = 4.0 -- the only combination among 6 tested (2
# formulations x 3 thresholds) that both clears the 33%-relative
# tail-protection floor on the 10 known worst days (72.3% reduction in
# tech3's contribution to those days' total loss) AND has the smallest
# full-sample Trend Sharpe impact among floor-clearing candidates (+23.3%
# vs. baseline -- an improvement, not a degradation).
#
# TECH_CLUSTER_PENALTY_LIVE = False: the penalized weight is computed and
# logged to logs/tech_cluster_penalty_shadow.jsonl but NOT used for order
# sizing -- `raw` below stays unpenalized whenever this flag is False, so
# size_today_positions()'s return value, and everything downstream of it
# (order_engine.py's live order sizing), is genuinely unaffected. Mirrors
# portfolio_risk.py's ERC_LIVE_SIZING pattern. Going live is a separate,
# future, explicit decision -- not made in this commit.
TECH_CLUSTER_PENALTY_LIVE = False
TECH3           = ['QQQ', 'XLK', 'SMH']
OTHER4_EQUITY   = ['SPY', 'IWM', 'EEM', 'EWJ']
TECH_CLUSTER_F_B        = 4.0
TECH_CLUSTER_RAMP_WIDTH = 0.5
TECH_CLUSTER_SHADOW_LOG = 'tech_cluster_penalty_shadow.jsonl'


def compute_tech_cluster_penalty_scalar(raw_weights: pd.Series,
                                         F_B: float = TECH_CLUSTER_F_B,
                                         ramp_width: float = TECH_CLUSTER_RAMP_WIDTH) -> float:
    """
    Effective-Number-of-Bets cluster penalty (Candidate B, selected per
    docs/tech_cluster_penalty_results.md). N_eff = 1 / sum(w_i^2) across
    Trend's 7 equity instruments. If N_eff would drop below F_B due to
    tech3 (QQQ+XLK+SMH) concentration, returns a scalar in (0, 1] meant to
    be applied to TECH3 weights only (other instruments untouched) --
    smoothly ramped over +/- ramp_width around F_B so there is no
    discontinuity at the threshold. Full derivation and smoothness
    rationale: docs/tech_cluster_penalty_prereg.md.
    """
    ss_cluster = sum(raw_weights.get(t, 0.0) ** 2 for t in TECH3)
    ss_other   = sum(raw_weights.get(t, 0.0) ** 2 for t in OTHER4_EQUITY)
    ss_total   = ss_cluster + ss_other
    if ss_total <= 1e-14:
        return 1.0

    n_eff_raw = 1.0 / ss_total

    if ss_cluster <= 1e-14:
        s_full = 1.0
    else:
        val = (1.0 / F_B - ss_other) / ss_cluster
        s_full = min(1.0, float(np.sqrt(max(0.0, val))))

    if n_eff_raw >= F_B + ramp_width:
        return 1.0
    if n_eff_raw <= F_B - ramp_width:
        return s_full

    frac = ((F_B + ramp_width) - n_eff_raw) / (2 * ramp_width)
    return 1.0 + frac * (s_full - 1.0)


def _log_tech_cluster_shadow(log_dir, pre_penalty, post_penalty, scalar, n_eff_raw):
    """
    Append one shadow-mode observation record. Never raises -- a logging
    failure here must never affect order sizing.
    """
    try:
        record = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'date': date.today().isoformat(),
            'tech_cluster_penalty_live': TECH_CLUSTER_PENALTY_LIVE,
            'n_eff_raw': round(float(n_eff_raw), 4),
            'f_b_floor': TECH_CLUSTER_F_B,
            'penalty_scalar': round(float(scalar), 6),
            'weights_pre_penalty': {t: round(float(pre_penalty.get(t, 0.0)), 6) for t in TECH3},
            'weights_post_penalty': {t: round(float(post_penalty.get(t, 0.0)), 6) for t in TECH3},
            'note': ('SHADOW MODE: post-penalty weights logged for observation only; '
                     'order sizing uses pre-penalty (unpenalized) weights while '
                     'TECH_CLUSTER_PENALTY_LIVE is False.'),
        }
        os.makedirs(log_dir, exist_ok=True)
        path = os.path.join(log_dir, TECH_CLUSTER_SHADOW_LOG)
        with open(path, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(record) + '\n')
    except Exception:
        pass


def size_today_positions(signal_result, prev_weights=None, log_dir=None):
    """
    Converts today's signal into target portfolio weights.
    prev_weights: dict of {ticker: weight} from the last rebalance,
                  used for the tiered dead-band comparison. Pass None
                  on the very first run (no prior position to compare against).
    log_dir: directory for the tech-cluster-penalty shadow log. Defaults to
             ./logs/ relative to this file (same convention as other sleeves).
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

    # Asset volatility (same EWM method as the backtest)
    asset_vol = returns.ewm(span=CFG['vol_lookback']).std().iloc[-1] * np.sqrt(252)
    asset_vol = asset_vol.replace(0, np.nan)

    sig = combined_signal.fillna(0)

    # Vol-target sizing, long/flat only (matches backtest exactly)
    raw = (sig * (CFG['target_vol'] / asset_vol)).fillna(0).clip(lower=0)

    # Apply regime scalar
    raw = raw * regime_scalar

    # ── Tech3 cluster penalty: SHADOW MODE ONLY (see module-level constants
    # and docstring above). Computed here -- BEFORE the divers_gross_cap --
    # on the same raw weight basis the rest of the sizing pipeline uses, so
    # it operates on the same footing as everything downstream. Logged
    # regardless of TECH_CLUSTER_PENALTY_LIVE; only APPLIED to `raw` (and
    # therefore to live order sizing) when that flag is explicitly True. ──
    ss_cluster_now = sum(raw.get(t, 0.0) ** 2 for t in TECH3)
    ss_other_now   = sum(raw.get(t, 0.0) ** 2 for t in OTHER4_EQUITY)
    n_eff_raw_now  = (1.0 / (ss_cluster_now + ss_other_now)
                      if (ss_cluster_now + ss_other_now) > 1e-14 else float('inf'))
    tech_penalty_scalar = compute_tech_cluster_penalty_scalar(raw)
    raw_pre_penalty  = raw.copy()
    raw_post_penalty = raw.copy()
    for t in TECH3:
        raw_post_penalty[t] = raw[t] * tech_penalty_scalar

    _log_tech_cluster_shadow(
        log_dir if log_dir else os.path.join(os.path.dirname(__file__), 'logs'),
        raw_pre_penalty, raw_post_penalty, tech_penalty_scalar, n_eff_raw_now,
    )

    if TECH_CLUSTER_PENALTY_LIVE:
        raw = raw_post_penalty
    # else: raw remains unpenalized -- order sizing genuinely unaffected.

    # Equity gross floor / diversifier cap
    eq_gross  = raw[equity_tickers].sum()
    div_gross = raw[divers_tickers].sum()
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

    # Tiered dead-band vs previous weights
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
    signal_result = generate_today_signal()

    # On first run, no prior weights exist yet
    target_weights = size_today_positions(signal_result, prev_weights=None)

    print(f"\n=== Target Portfolio Weights for {signal_result['date'].date()} ===")
    print(target_weights.sort_values(ascending=False).round(4))
    print(f"\nGross exposure: {target_weights.abs().sum():.2%}")
    print(f"Equity exposure: {target_weights[equity_tickers].sum():.2%}")
    print(f"Diversifier exposure: {target_weights[divers_tickers].sum():.2%}")
