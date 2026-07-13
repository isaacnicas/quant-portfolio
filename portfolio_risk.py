"""
portfolio_risk.py
-----------------
Portfolio-level volatility targeting and equal risk contribution (ERC) weighting.

Architecture rationale (from counsel 1 and 3):
  Counsel 3 was explicit: volatility scaling contributes more incremental
  Sharpe than signal refinement. This module is infrastructure, not alpha.
  It must be operational before the second strategy is deployed.

  Two core functions:
    1. ERC sleeve weighting — true Equal Risk Contribution: weights are
       solved so each sleeve contributes equally to total portfolio
       volatility, accounting for cross-sleeve covariance.
       ERC weights computed via Riskfolio-Lib risk-parity optimizer
       (MV, equal budgets). Prior IV approximation replaced 2026-07-13
       following peer-review finding (max delta 11.75pp vs true ERC,
       MR negative MRC under IV).
    2. Portfolio vol targeting — scale all positions so the combined
       portfolio targets 10-12% annualized volatility.

Usage
-----
    from portfolio_risk import PortfolioRiskManager

    risk_mgr = PortfolioRiskManager(target_portfolio_vol=0.11)

    # After getting signals from each strategy:
    sleeve_returns = {
        "Trend":         trend_daily_returns,      # pd.Series
        "MeanReversion": mr_daily_returns,
        "VRP":           vrp_daily_returns,
    }
    active_sleeves = ["Trend", "MeanReversion", "VRP"]

    weights = risk_mgr.compute_erc_weights(sleeve_returns, active_sleeves)
    scalar  = risk_mgr.portfolio_vol_scalar(sleeve_returns, weights)

    # weights * scalar gives the final risk-adjusted allocation per sleeve
"""

import json
import os
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd


TRADING_DAYS_PER_YEAR = 252

# ── Observation-mode flag ──────────────────────────────────────────────────────
# Observation mode. ERC computes and logs weights but does NOT size orders.
# order_engine.py uses its own sizing (MR 10%, Trend vol-target).
# Flip to True only after logged ERC weights prove stable/sane over a defined
# period, as a deliberate Phase-E decision reviewed against criteria.
ERC_LIVE_SIZING = False


class PortfolioRiskManager:
    """
    Computes ERC sleeve weights and portfolio volatility scaling factor.

    Parameters
    ----------
    target_portfolio_vol : float
        Target annualized portfolio volatility (default 0.11 = 11%).
        Counsel specified 10-12%; 11% is the midpoint.
    target_sleeve_vol    : float
        Target annualized volatility contribution per sleeve (default 0.10).
        Counsel 1: "10% volatility target per active sleeve".
    lookback_days        : int
        Rolling window for realized volatility estimation (default 21 trading days).
    min_vol_floor        : float
        Minimum annualized vol estimate to prevent division-by-zero or
        absurdly large position scaling (default 0.05 = 5%).
    """

    def __init__(self,
                 target_portfolio_vol: float = 0.11,
                 target_sleeve_vol: float = 0.10,
                 lookback_days: int = 21,
                 min_vol_floor: float = 0.05,
                 log_dir: str = None):

        self.target_portfolio_vol = target_portfolio_vol
        self.target_sleeve_vol    = target_sleeve_vol
        self.lookback_days        = lookback_days
        self.min_vol_floor        = min_vol_floor

        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(__file__), "logs")
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)

    # ── ERC sleeve weights ──────────────────────────────────────────────────

    def compute_erc_weights(self,
                            sleeve_returns: dict[str, pd.Series],
                            active_sleeves: list[str]) -> dict[str, float]:
        """
        Compute Equal Risk Contribution (ERC) weights for active sleeves
        using Riskfolio-Lib's risk-parity optimizer (MV risk measure,
        equal risk budgets).

        True ERC: weights are set so each sleeve contributes equally to
        total portfolio volatility, accounting for cross-sleeve covariance.

        Replaces the prior inverse-volatility approximation (which ignored
        covariance and produced unequal marginal risk contributions —
        confirmed by peer review 2026-07-13, commit 0260b69).

        Falls back to equal weights when observation history is below the
        minimum threshold (MIN_HISTORY_DAYS). Fallback is logged as a warning.

        Parameters
        ----------
        sleeve_returns : dict mapping sleeve name → daily return pd.Series
        active_sleeves : list of sleeve names that are currently active
                         (not gated out by governance_gates.py)

        Returns
        -------
        dict mapping sleeve name → capital weight (sums to 1.0 across active sleeves)
        """
        if not active_sleeves:
            return {}

        MIN_HISTORY_DAYS = self.lookback_days  # matches C8 maturity threshold

        def _equal_fallback(obs: int) -> dict[str, float]:
            n = len(active_sleeves)
            self._last_erc_fallback = True
            self._last_erc_obs = obs
            return {s: 1.0 / n for s in active_sleeves}

        # Build aligned return DataFrame from active sleeves only.
        # Inner join — only dates where all active sleeves have returns.
        # (Sleeves with no returns history at all, e.g. a brand-new sleeve
        # with no state log yet, are excluded here rather than raising —
        # preserves the prior method's tolerance for a missing sleeve.)
        available = [s for s in active_sleeves if s in sleeve_returns]
        if len(available) < len(active_sleeves):
            missing = set(active_sleeves) - set(available)
            print(f"[ERC] WARNING: no return history for {missing} — "
                  f"falling back to equal weights")
            return _equal_fallback(0)

        returns_df = pd.DataFrame({s: sleeve_returns[s] for s in available}).dropna()

        # Thin history fallback — equal weights, flagged
        if len(returns_df) < MIN_HISTORY_DAYS:
            print(f"[ERC] WARNING: only {len(returns_df)} aligned observations "
                  f"(< {MIN_HISTORY_DAYS} required) — falling back to equal weights")
            return _equal_fallback(len(returns_df))

        # Riskfolio-Lib RP optimization.
        # Risk measure: MV (standard deviation).
        # Risk budget: equal across all active sleeves — b=None makes
        # Riskfolio-Lib default internally to rb = ones((N,1))/N, i.e.
        # exactly equal risk budgets. (If an explicit non-equal budget
        # vector is ever needed, it must be a plain 2D numpy array of
        # shape (n,1) — a pandas Series/DataFrame breaks the library's
        # internal `rb.T @ log_w` cvxpy matmul.)
        try:
            import riskfolio as rp
            port = rp.Portfolio(returns=returns_df)
            port.assets_stats(method_mu="hist", method_cov="hist")
            w = port.rp_optimization(model="Classic", rm="MV", rf=0, b=None, hist=True)
            weights = w["weights"].to_dict()
            total = sum(weights.values())
            if total <= 0 or any(v != v for v in weights.values()):  # NaN check
                raise ValueError(f"invalid weight total: {total}")
            weights = {s: weights[s] / total for s in active_sleeves}
        except Exception as exc:
            print(f"[ERC] WARNING: Riskfolio-Lib RP optimization failed ({exc}) "
                  f"— falling back to equal weights")
            return _equal_fallback(len(returns_df))

        self._last_erc_fallback = False
        self._last_erc_obs = len(returns_df)
        return weights

    # ── Portfolio vol scalar ────────────────────────────────────────────────

    def portfolio_vol_scalar(self,
                             sleeve_returns: dict[str, pd.Series],
                             sleeve_weights: dict[str, float]) -> float:
        """
        Compute a multiplicative scalar that brings the blended portfolio
        to the target portfolio volatility.

        Applied uniformly across all active sleeves AFTER ERC weights are set.
        When the portfolio is running hot, scalar < 1. When running cold, scalar > 1.
        Scalar is capped at 2.0 to prevent extreme leverage.

        Parameters
        ----------
        sleeve_returns : dict mapping sleeve name → daily return pd.Series
        sleeve_weights : output of compute_erc_weights()

        Returns
        -------
        float : multiplicative scalar (typically 0.5 to 2.0)
        """
        if not sleeve_weights:
            return 1.0

        # Build blended return series from shared date index
        all_series = []
        for sleeve, weight in sleeve_weights.items():
            if sleeve in sleeve_returns and len(sleeve_returns[sleeve]) >= self.lookback_days:
                all_series.append(sleeve_returns[sleeve].tail(self.lookback_days) * weight)

        if not all_series:
            return 1.0

        # Align on common dates and sum
        blended = pd.concat(all_series, axis=1).sum(axis=1)
        portfolio_vol = self._annualize(blended.std())

        if portfolio_vol < self.min_vol_floor:
            return 1.0

        scalar = self.target_portfolio_vol / portfolio_vol
        scalar = min(scalar, 2.0)   # hard cap at 2x leverage
        return round(scalar, 4)

    # ── Per-sleeve metrics ──────────────────────────────────────────────────

    def compute_sleeve_metrics(self,
                               returns: pd.Series,
                               risk_free_daily: float = 0.0) -> dict:
        """
        Compute all daily tracking metrics for a single sleeve.
        Output fed into strategy_base.log_daily_state().

        Parameters
        ----------
        returns          : daily return pd.Series for this sleeve
        risk_free_daily  : daily risk-free rate (default 0.0)

        Returns
        -------
        dict with keys: vol_21d, sharpe_21d, max_dd_21d, hit_rate_21d
        """
        recent = returns.tail(self.lookback_days)
        if len(recent) < 5:
            return {"vol_21d": None, "sharpe_21d": None,
                    "max_dd_21d": None, "hit_rate_21d": None}

        vol     = self._annualize(recent.std())
        excess  = recent - risk_free_daily
        sharpe  = (excess.mean() / recent.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
                   if recent.std() > 0 else 0.0)
        cum     = (1 + recent).cumprod()
        max_dd  = float((cum / cum.cummax() - 1).min())
        hit_rate = float((recent > 0).mean())

        return {
            "vol_21d":     round(vol, 4),
            "sharpe_21d":  round(sharpe, 4),
            "max_dd_21d":  round(max_dd, 4),
            "hit_rate_21d": round(hit_rate, 4),
        }

    def compute_cross_sleeve_correlations(self,
                                          sleeve_returns: dict[str, pd.Series]
                                          ) -> dict:
        """
        Compute rolling 21-day pairwise correlations between all sleeves.
        Stored daily for the future ML meta-layer.

        Returns
        -------
        dict of {f"{sleeve_a}_vs_{sleeve_b}": correlation_float}
        """
        if len(sleeve_returns) < 2:
            return {}

        df = pd.DataFrame(sleeve_returns).tail(self.lookback_days)
        corr_matrix = df.corr()
        result = {}
        cols = list(corr_matrix.columns)
        for i, a in enumerate(cols):
            for b in cols[i+1:]:
                key = f"{a}_vs_{b}"
                val = corr_matrix.loc[a, b]
                if not np.isnan(val):
                    result[key] = round(float(val), 4)
        return result

    # ── Sleeve redundancy detection ─────────────────────────────────────────

    def check_sleeve_redundancy(
            self,
            sleeve_returns: dict[str, pd.Series],
            sharpe_by_sleeve: dict[str, float],
            correlation_threshold: float = 0.85,
    ) -> dict:
        """
        Flag sleeve pairs with excessive correlation.
        When two sleeves are highly correlated, the lower-Sharpe one is
        redundant — reduce its risk budget.

        Adapted from R&D-Agent-Quant IC deduplication (threshold 0.99 for
        factor mining; 0.85 for portfolio sleeves is more conservative and
        appropriate for our multi-strategy context).

        Returns dict: {
            sleeve_name: {
                "action": "reduce" | "monitor" | "ok",
                "correlated_with": sleeve_name | None,
                "correlation": float,
                "reason": str
            }
        }
        """
        correlations = self.compute_cross_sleeve_correlations(sleeve_returns)

        flags = {}
        for sleeve in sleeve_returns:
            flags[sleeve] = {
                "action": "ok",
                "correlated_with": None,
                "correlation": 0.0,
                "reason": "independent",
            }

        for pair_key, corr in correlations.items():
            if abs(corr) >= correlation_threshold:
                sleeve_a, _, sleeve_b = pair_key.partition("_vs_")
                sharpe_a = sharpe_by_sleeve.get(sleeve_a, 0)
                sharpe_b = sharpe_by_sleeve.get(sleeve_b, 0)

                weaker   = sleeve_a if sharpe_a <= sharpe_b else sleeve_b
                stronger = sleeve_b if weaker == sleeve_a  else sleeve_a

                flags[weaker] = {
                    "action": "reduce",
                    "correlated_with": stronger,
                    "correlation": round(corr, 3),
                    "reason": (
                        f"Corr {corr:.3f} >= {correlation_threshold}"
                        f" with {stronger} (higher Sharpe)"
                    ),
                }
                flags[stronger] = {
                    "action": "monitor",
                    "correlated_with": weaker,
                    "correlation": round(corr, 3),
                    "reason": "Higher-Sharpe sleeve in correlated pair",
                }

        return flags

    # ── Daily portfolio state logging ───────────────────────────────────────

    def log_portfolio_state(self,
                            sleeve_returns: dict[str, pd.Series],
                            sleeve_weights: dict[str, float],
                            gate_state: dict,
                            nav: float = None,
                            insufficient_history: dict = None):
        """
        Write combined portfolio-level tracking record to portfolio_state.jsonl.

        Extended fields vs original:
          portfolio_vol_ex_ante  : realized blended portfolio vol (annualized);
                                   None when history is too thin to estimate.
          risk_contributions     : per-sleeve share of total risk budget
                                   (weight_i × vol_i normalized to sum 1.0).
          insufficient_history   : per-sleeve bool flag — True when fewer than
                                   lookback_days data points are available.
          erc_live_sizing        : always mirrors the module ERC_LIVE_SIZING
                                   constant so each record is self-documenting.
        """
        from datetime import datetime as _dt
        vol_scalar   = self.portfolio_vol_scalar(sleeve_returns, sleeve_weights)
        correlations = self.compute_cross_sleeve_correlations(sleeve_returns)

        sleeve_metrics = {}
        for sleeve, returns in sleeve_returns.items():
            sleeve_metrics[sleeve] = self.compute_sleeve_metrics(returns)

        sleeve_sharpes = {
            sleeve: (metrics.get("sharpe_21d") or 0.0)
            for sleeve, metrics in sleeve_metrics.items()
        }
        redundancy_flags = self.check_sleeve_redundancy(
            sleeve_returns, sleeve_sharpes
        )

        # Portfolio ex-ante vol: blended return series vol over lookback window.
        # Returns None when there is insufficient history (< lookback_days data points).
        portfolio_vol_ex_ante = None
        blended_series = []
        for sleeve, weight in sleeve_weights.items():
            if sleeve in sleeve_returns and len(sleeve_returns[sleeve]) >= self.lookback_days:
                blended_series.append(sleeve_returns[sleeve].tail(self.lookback_days) * weight)
        if blended_series:
            blended = pd.concat(blended_series, axis=1).sum(axis=1)
            p_vol   = self._annualize(blended.std())
            if p_vol >= self.min_vol_floor:
                portfolio_vol_ex_ante = round(p_vol, 4)

        # Risk contributions: weight_i × vol_i, normalized so they sum to 1.0.
        # Uses min_vol_floor when a sleeve's realized vol is unavailable (thin history).
        raw_rc = {}
        for sleeve, w in sleeve_weights.items():
            m   = sleeve_metrics.get(sleeve, {})
            vol = m.get("vol_21d") if m else None
            raw_rc[sleeve] = w * (vol if vol else self.min_vol_floor)
        total_rc = sum(raw_rc.values()) or 1.0
        risk_contributions = {s: round(rc / total_rc, 4) for s, rc in raw_rc.items()}

        record = {
            "timestamp":            _dt.now().isoformat(),
            "date":                 date.today().isoformat(),
            "nav":                  nav,
            "vol_scalar":           vol_scalar,
            "portfolio_vol_ex_ante": portfolio_vol_ex_ante,
            "sleeve_weights":       {k: round(v, 4) for k, v in sleeve_weights.items()},
            "risk_contributions":   risk_contributions,
            "insufficient_history": insufficient_history or {},
            "sleeve_metrics":       sleeve_metrics,
            "correlations":         correlations,
            "redundancy_flags":     redundancy_flags,
            "gate_summary": {
                "any_gate_active": gate_state.get("any_gate_active", False),
                "macro_regime":    gate_state.get("macro_regime", "unknown"),
            },
            "erc_live_sizing":      ERC_LIVE_SIZING,
            "erc_method":           ("equal_fallback" if getattr(self, "_last_erc_fallback", None)
                                     else "riskfolio_rp"),
            "erc_obs_count":        getattr(self, "_last_erc_obs", None),
        }

        for sleeve, flag in redundancy_flags.items():
            if flag["action"] == "reduce":
                print(f"[RISK] Sleeve redundancy detected: "
                      f"{sleeve} corr={flag['correlation']:.3f} "
                      f"with {flag['correlated_with']} — "
                      f"consider reducing risk budget")

        log_path = os.path.join(self.log_dir, "portfolio_state.jsonl")
        with open(log_path, "a") as f:
            f.write(json.dumps(record) + "\n")

        return record

    # ── Private helpers ─────────────────────────────────────────────────────

    def _realized_vol(self, returns: pd.Series) -> float:
        """Annualized realized volatility over the lookback window."""
        recent = returns.tail(self.lookback_days)
        if len(recent) < 5 or recent.std() == 0:
            return self.min_vol_floor
        return max(self._annualize(recent.std()), self.min_vol_floor)

    @staticmethod
    def _annualize(daily_std: float) -> float:
        return daily_std * np.sqrt(TRADING_DAYS_PER_YEAR)

    # ── Diagnostic report ───────────────────────────────────────────────────

    def print_risk_report(self,
                          sleeve_returns: dict[str, pd.Series],
                          active_sleeves: list[str]):
        """Print a concise risk allocation report to console."""
        weights = self.compute_erc_weights(sleeve_returns, active_sleeves)
        scalar  = self.portfolio_vol_scalar(sleeve_returns, weights)
        corrs   = self.compute_cross_sleeve_correlations(sleeve_returns)

        print("\n" + "=" * 65)
        print("PORTFOLIO RISK REPORT")
        print("=" * 65)
        print(f"Target portfolio vol:  {self.target_portfolio_vol:.0%}")
        print(f"Vol scalar (today):    {scalar:.3f}x")
        print()
        print(f"{'Sleeve':<20} {'ERC Weight':>10} {'Vol 21d':>10} {'Sharpe 21d':>12}")
        print("-" * 55)
        for sleeve in active_sleeves:
            w = weights.get(sleeve, 0)
            if sleeve in sleeve_returns:
                m = self.compute_sleeve_metrics(sleeve_returns[sleeve])
                v = f"{m['vol_21d']:.1%}" if m['vol_21d'] else "—"
                s = f"{m['sharpe_21d']:.2f}" if m['sharpe_21d'] else "—"
            else:
                v, s = "—", "—"
            print(f"  {sleeve:<18} {w:>10.1%} {v:>10} {s:>12}")
        print()
        print("Cross-sleeve correlations (21d):")
        for pair, corr in corrs.items():
            flag = " ⚠" if abs(corr) > 0.5 else ""
            print(f"  {pair:<35} {corr:>+.3f}{flag}")
        print("=" * 65 + "\n")


# ── Step 6 entry point ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    Daily ERC computation — runs as Step 6 of daily_routine_v2.bat.

    OBSERVATION MODE (ERC_LIVE_SIZING=False):
      Computes ERC weights and vol-scalar, writes portfolio_state.jsonl.
      Does NOT affect order sizing. order_engine.py is unchanged.
      MR stays at 10%, Trend stays at vol-target. Orders byte-identical.
    """
    import sys
    from datetime import datetime as _dt
    from pathlib import Path

    BASE     = Path(__file__).parent
    LOG_DIR  = BASE / "logs"
    DATA_DIR = BASE / "data"

    print(f"\n[ERC] Step 6 — portfolio_risk.py  {_dt.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"[ERC] ERC_LIVE_SIZING = {ERC_LIVE_SIZING}  (observation mode — orders unchanged)")

    # ── 1. Load NAV ────────────────────────────────────────────────────────────
    nav      = None
    nav_date = "unknown"
    dash_json = DATA_DIR / "dashboard_data.json"
    if dash_json.exists():
        try:
            raw = json.load(dash_json.open())
            nav = raw.get("nav")
            nav_date = (raw.get("last_updated") or raw.get("nav_history", [{}])[-1].get("date", "?"))[:10]
            if nav:
                age = (date.today() - _dt.fromisoformat(nav_date).date()).days
                print(f"[ERC] NAV = ${nav:,.0f}  (from dashboard_data.json, {age}d old)")
                if age > 3:
                    print(f"[ERC] NOTE: NAV is {age} days stale — "
                          f"vol estimates will use min_vol_floor in thin history anyway")
        except Exception as e:
            print(f"[ERC] WARNING: could not read dashboard_data.json ({e}) — using nav=None")

    if not nav:
        print("[ERC] WARNING: NAV unavailable — cannot convert pnl_usd to returns; "
              "ERC will use equal weights (min_vol_floor for all sleeves)")
        nav = 0.0

    # ── 2. Load sleeve returns from state logs (point-in-time) ────────────────
    # Each state log is append-only; take the LAST record per calendar date so
    # multiple same-day runs (e.g. signal + health-check reruns) don't double-count.
    SLEEVE_LOGS = {
        "MeanReversion": LOG_DIR / "meanreversion_state.jsonl",
        "VRP":           LOG_DIR / "vrp_state.jsonl",
    }
    sleeve_returns    : dict[str, pd.Series] = {}
    insufficient_history: dict[str, bool]   = {}

    for sleeve, path in SLEEVE_LOGS.items():
        if not path.exists():
            print(f"[ERC] {sleeve}: state log not found -> insufficient_history=True")
            insufficient_history[sleeve] = True
            continue

        records_by_date: dict[str, dict] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                records_by_date[r["date"]] = r  # last record per date wins
            except Exception:
                continue

        n_dates = len(records_by_date)
        if nav > 0 and n_dates > 0:
            ret_data: dict[str, float] = {}
            for date_str, r in sorted(records_by_date.items()):
                pnl   = r.get("pnl_usd")
                alloc = r.get("capital_alloc", 0.0)
                if pnl is not None and alloc > 0:
                    ret_data[date_str] = pnl / (alloc * nav)
            if ret_data:
                s = pd.Series(ret_data)
                s.index = pd.to_datetime(s.index)
                sleeve_returns[sleeve] = s
                n = len(s)
                insuff = n < 21
                insufficient_history[sleeve] = insuff
                suffix = " (INSUFFICIENT — need >= 21 for full window)" if insuff else ""
                print(f"[ERC] {sleeve}: {n} unique date(s) loaded{suffix}")
            else:
                print(f"[ERC] {sleeve}: {n_dates} records but no valid pnl/alloc -> insufficient")
                insufficient_history[sleeve] = True
        else:
            print(f"[ERC] {sleeve}: {n_dates} record(s) found, NAV=0 -> cannot compute returns")
            insufficient_history[sleeve] = True

    # Trend: no trend_state.jsonl yet (Phase-C Gap #3)
    insufficient_history["Trend"] = True
    print(f"[ERC] Trend: no trend_state.jsonl (Gap #3) -> insufficient_history=True")

    # ── 3. Load gate state (most recent entry) ────────────────────────────────
    gate_state: dict = {}
    gate_log = LOG_DIR / "gate_state.jsonl"
    if gate_log.exists():
        lines = [l.strip() for l in gate_log.read_text(encoding="utf-8").splitlines() if l.strip()]
        if lines:
            gate_state = json.loads(lines[-1])
            print(f"[ERC] Gate state: date={gate_state.get('date')}, "
                  f"any_gate_active={gate_state.get('any_gate_active')}, "
                  f"macro={gate_state.get('macro_regime')}")

    # Determine active sleeves: all known sleeves that are not suspended today
    KNOWN_SLEEVES  = ["Trend", "MeanReversion", "VRP"]
    sleeve_actions = gate_state.get("sleeve_actions", {})
    active_sleeves = [s for s in KNOWN_SLEEVES
                      if sleeve_actions.get(s, "active") != "suspend"]
    print(f"[ERC] Active sleeves (not suspended by gates): {active_sleeves}")

    # ── 4. Compute ERC weights ────────────────────────────────────────────────
    risk_mgr = PortfolioRiskManager(
        target_portfolio_vol = 0.11,
        target_sleeve_vol    = 0.10,
        lookback_days        = 21,
        log_dir              = str(LOG_DIR),
    )

    erc_weights = risk_mgr.compute_erc_weights(sleeve_returns, active_sleeves)
    print(f"[ERC] ERC weights: { {k: f'{v:.1%}' for k,v in erc_weights.items()} }")

    # ── 5. Write portfolio_state.jsonl (observation record) ───────────────────
    record = risk_mgr.log_portfolio_state(
        sleeve_returns      = sleeve_returns,
        sleeve_weights      = erc_weights,
        gate_state          = gate_state,
        nav                 = nav if nav else None,
        insufficient_history= insufficient_history,
    )

    # ── 6. Print ERC report ───────────────────────────────────────────────────
    risk_mgr.print_risk_report(sleeve_returns, active_sleeves)

    print("OBSERVATION MODE SUMMARY")
    print(f"  ERC_LIVE_SIZING = {ERC_LIVE_SIZING}  (orders unchanged — logged for monitoring only)")
    print(f"  {'Sleeve':<18} {'ERC Weight':>10} {'Risk Contrib':>13} {'Insuff History':>15}")
    print(f"  {'-'*58}")
    rc = record.get("risk_contributions", {})
    for sleeve in KNOWN_SLEEVES:
        w  = erc_weights.get(sleeve, 0.0)
        r_ = rc.get(sleeve, 0.0)
        ih = insufficient_history.get(sleeve, False)
        print(f"  {sleeve:<18} {w:>10.1%} {r_:>13.1%} {str(ih):>15}")
    pv = record.get("portfolio_vol_ex_ante")
    pv_str = f"{pv:.1%}" if pv else "N/A (insufficient history)"
    print(f"\n  Portfolio vol ex-ante:  {pv_str}")
    print(f"  Vol scalar:             {record['vol_scalar']:.4f}x")
    print(f"\n[ERC] portfolio_state.jsonl written -> {LOG_DIR / 'portfolio_state.jsonl'}")
    print(f"[ERC] Step 6 complete.")
