"""
vol_scalar_observer.py
=======================
OBSERVATION-ONLY. Purely additive: does NOT modify meta_allocator_v0.py's
tilt logic, does NOT feed order_engine.py, does NOT affect ERC_LIVE_SIZING,
and is not wired into any live or paper order path. It computes and logs
what a sleeve's weight WOULD have been after applying an additional
downward-only volatility scalar on top of the existing allocator's
proposed (tilted) weight — nothing here has live authority.

This mirrors the ERC observation-before-authority pattern already
established in portfolio_risk.py (ERC_LIVE_SIZING=False until C8
maturity): accumulate live observation data first, decide on authority
later, as a separate, deliberate decision.

Background: docs/endogenous_risk_empirical_check.md found the existing
allocator tilt (meta_allocator_v0.WeightProposer) has no path for
forecast_vol to influence sizing, and moved weight the WRONG direction
in 8 of 15 historical worst-drawdown episodes. This module is the
validated response — see docs/vol_scalar_design_and_validation.md for
the full empirical validation (Step 2: 8/8 wrong-direction episodes
corrected below ERC baseline; Step 3: false-positive rate at high
enough frequency that this is NOT yet recommended for live authority).

--- Formula ---

Two components, both downward-only (capped at 1.0), combined via min():

  1. EWMA-based (slow, structural):
       vol_scalar_ewma = min(1.0, vol_target / forecast_vol)
     forecast_vol  : the live EWMA(span=21) vol estimate already computed
                     daily by sleeve_forecast_mixin.py (reused, not
                     recomputed).
     vol_target    : the sleeve's own long-run mean forecast_vol,
                     computed from all available history in
                     {sleeve}_state.jsonl's vol_21d field.

  2. Fast-spike (fast-twitch supplement for sharp dislocations the EWMA
     is structurally too slow to catch — see the MeanReversion 2020-03-23
     COVID case in the validation doc, where forecast_vol lagged realized
     vol by +19.2 percentage points annualized):
       ratio = fast_vol_5d / forecast_vol
       vol_scalar_fast_spike = 1.0        if ratio <= FAST_SPIKE_THRESHOLD
                              = FAST_SPIKE_THRESHOLD / ratio   otherwise
     fast_vol_5d   : trailing 5-day annualized realized vol, computed from
                     a pnl_usd / (capital_alloc * NAV) return proxy (see
                     caveat below).
     FAST_SPIKE_THRESHOLD = 2.0, chosen empirically: the minimum of
     {1.5, 2.0, 2.5} tested that still triggers on the single fastest
     historical dislocation in the validation dataset without
     over-triggering the way 1.5x does (see design doc).

  final_scalar = min(vol_scalar_ewma, vol_scalar_fast_spike)
  weight_post_scalar_observation_only = weight_pre_scalar * final_scalar

Caveat (disclosed, same as the empirical check): fast_vol_5d uses
pnl_usd / (capital_alloc * NAV) as a return proxy, reading NAV from
portfolio_state.jsonl. This is scale-invariant and exact as long as
capital_alloc and NAV are roughly constant over the trailing 5 days;
not exact under live intra-week resizing.

Both components require sufficient history. When unavailable (thin
history — expected for this early-stage live system, whose state logs
currently hold single-digit record counts), the scalar defaults to 1.0
(no-op, matching the existing platform's thin-history convention in
SleeveForecastMixin) and a thin_history flag is set.
"""

import json
import math
import os
from datetime import date, datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

SLEEVE_NAMES = ["Trend", "MeanReversion", "VRP"]
FORECAST_LOG_NAME = "sleeve_forecasts.jsonl"
PROPOSAL_LOG_NAME = "proposed_weights.jsonl"
PORTFOLIO_STATE_LOG_NAME = "portfolio_state.jsonl"
OBSERVATION_LOG_NAME = "vol_scalar_observation.jsonl"

MIN_RECORDS_VOL_TARGET = 20   # matches MIN_RECORDS_CORR convention in sleeve_forecast_mixin.py
MIN_RECORDS_FAST_VOL = 5
FAST_SPIKE_THRESHOLD = 2.0    # see design doc for 1.5x / 2.0x / 2.5x comparison


def _load_state_records(sleeve: str, log_dir: str) -> list:
    """
    All available prior-day records from {sleeve}_state.jsonl (PIT: date <
    today), oldest-first. Unlike SleeveForecastMixin._load_recent_state,
    this does not truncate to a lookback window — vol_target needs the
    FULL available history, not just a recent slice.
    """
    log_path = os.path.join(log_dir, f"{sleeve.lower()}_state.jsonl")
    if not os.path.exists(log_path):
        return []
    records = []
    try:
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except IOError:
        return []
    today = date.today().isoformat()
    return [r for r in records if r.get("date", "") < today]


def compute_vol_target(sleeve: str, log_dir: str) -> tuple[Optional[float], bool]:
    """
    Sleeve's own long-run mean forecast_vol, estimated from all available
    vol_21d history in {sleeve}_state.jsonl. Returns (vol_target, thin_history).
    """
    records = _load_state_records(sleeve, log_dir)
    vols = [
        r["vol_21d"] for r in records
        if r.get("vol_21d") is not None
        and not math.isnan(r.get("vol_21d", float("nan")))
        and r.get("vol_21d", 0.0) > 0
    ]
    if len(vols) < MIN_RECORDS_VOL_TARGET:
        return None, True
    return round(float(np.mean(vols)), 6), False


def get_latest_nav(log_dir: str) -> Optional[float]:
    """Most recent portfolio NAV from portfolio_state.jsonl (read-only)."""
    path = os.path.join(log_dir, PORTFOLIO_STATE_LOG_NAME)
    if not os.path.exists(path):
        return None
    last = None
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        last = json.loads(line)
                    except json.JSONDecodeError:
                        continue
    except IOError:
        pass
    nav = last.get("nav") if last else None
    return float(nav) if nav else None


def compute_fast_vol_5d(sleeve: str, log_dir: str) -> tuple[Optional[float], bool]:
    """
    Trailing 5-day annualized realized vol from a
    pnl_usd / (capital_alloc * NAV) return proxy — dollar P&L divided by
    the actual dollar capital allocated to the sleeve that day, matching
    the units of vol_21d/forecast_vol (both computed on a plain daily
    return series). capital_alloc alone is a NAV *fraction* (e.g. 0.6),
    not a dollar amount, so it must be multiplied by NAV first; dividing
    pnl_usd by capital_alloc alone (an earlier version of this function)
    produced nonsensical six-figure "vol" values in the smoke test.
    Returns (fast_vol_5d, thin_history).
    """
    nav = get_latest_nav(log_dir)
    if not nav:
        return None, True
    records = _load_state_records(sleeve, log_dir)
    if len(records) < MIN_RECORDS_FAST_VOL:
        return None, True
    recent = records[-MIN_RECORDS_FAST_VOL:]
    proxy_returns = []
    for r in recent:
        cap = r.get("capital_alloc")
        pnl = r.get("pnl_usd")
        if cap and cap > 0 and pnl is not None:
            proxy_returns.append(pnl / (cap * nav))
    if len(proxy_returns) < MIN_RECORDS_FAST_VOL:
        return None, True
    std = float(np.std(proxy_returns, ddof=1))
    if std == 0.0:
        return None, True
    return round(std * math.sqrt(252), 6), False


def get_latest_forecast_vol(sleeve: str, log_dir: str) -> Optional[float]:
    """Most recent forecast_vol already computed live by SleeveForecastMixin."""
    path = os.path.join(log_dir, FORECAST_LOG_NAME)
    if not os.path.exists(path):
        return None
    latest = None
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if rec.get("sleeve") == sleeve:
                        latest = rec
                except json.JSONDecodeError:
                    continue
    except IOError:
        pass
    return latest.get("forecast_vol") if latest else None


def get_latest_proposed_weights(log_dir: str) -> dict:
    """Most recent proposed_weight per sleeve from proposed_weights.jsonl."""
    path = os.path.join(log_dir, PROPOSAL_LOG_NAME)
    if not os.path.exists(path):
        return {}
    last = None
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        last = json.loads(line)
                    except json.JSONDecodeError:
                        continue
    except IOError:
        pass
    if not last:
        return {}
    return {
        sleeve: data.get("proposed_weight")
        for sleeve, data in last.get("sleeves", {}).items()
    }


def compute_vol_scalar(sleeve: str, log_dir: str,
                        fast_spike_threshold: float = FAST_SPIKE_THRESHOLD) -> dict:
    """
    Compute the two-component vol scalar for one sleeve. Returns a dict of
    all intermediate and final values (for logging/inspection).
    """
    forecast_vol = get_latest_forecast_vol(sleeve, log_dir)
    vol_target, target_thin = compute_vol_target(sleeve, log_dir)
    fast_vol_5d, fast_thin = compute_fast_vol_5d(sleeve, log_dir)

    thin_history = target_thin or fast_thin or (forecast_vol is None)

    if forecast_vol is None or forecast_vol <= 0 or vol_target is None:
        scalar_ewma = 1.0
    else:
        scalar_ewma = float(min(1.0, vol_target / forecast_vol))

    if forecast_vol is None or forecast_vol <= 0 or fast_vol_5d is None:
        scalar_fast_spike = 1.0
    else:
        ratio = fast_vol_5d / forecast_vol
        scalar_fast_spike = 1.0 if ratio <= fast_spike_threshold else float(fast_spike_threshold / ratio)

    scalar_combined = min(scalar_ewma, scalar_fast_spike)

    return {
        "sleeve": sleeve,
        "forecast_vol": forecast_vol,
        "vol_target": vol_target,
        "fast_vol_5d": fast_vol_5d,
        "vol_scalar_ewma": round(scalar_ewma, 6),
        "vol_scalar_fast_spike": round(scalar_fast_spike, 6),
        "vol_scalar_combined": round(scalar_combined, 6),
        "thin_history": thin_history,
    }


def run_observation(log_dir: str = None) -> list:
    """
    Compute and log the vol-scalar-adjusted weight for all three sleeves,
    using the most recent proposed_weights.jsonl record as the pre-scalar
    (tilted) weight. Appends one record per sleeve to
    logs/vol_scalar_observation.jsonl. Returns the list of records.

    OBSERVATION ONLY: this does not write to, read from, or otherwise
    touch order_engine.py, ERC_LIVE_SIZING, or any live/paper order.
    proposed_weights.jsonl (the tilt input) is read-only here; nothing in
    meta_allocator_v0.py is modified or re-invoked with different logic.
    """
    if log_dir is None:
        log_dir = os.path.join(os.path.dirname(__file__), "logs")

    weights_pre_scalar = get_latest_proposed_weights(log_dir)
    timestamp = datetime.now(timezone.utc).isoformat()
    today = date.today().isoformat()

    records = []
    for sleeve in SLEEVE_NAMES:
        scalar_data = compute_vol_scalar(sleeve, log_dir)
        weight_pre = weights_pre_scalar.get(sleeve)
        weight_post = (
            round(weight_pre * scalar_data["vol_scalar_combined"], 6)
            if weight_pre is not None else None
        )
        record = {
            "timestamp": timestamp,
            "date": today,
            "sleeve": sleeve,
            "weight_pre_scalar": weight_pre,
            "vol_scalar_ewma": scalar_data["vol_scalar_ewma"],
            "vol_scalar_fast_spike": scalar_data["vol_scalar_fast_spike"],
            "vol_scalar_combined": scalar_data["vol_scalar_combined"],
            "weight_post_scalar_observation_only": weight_post,
            "forecast_vol": scalar_data["forecast_vol"],
            "vol_target": scalar_data["vol_target"],
            "fast_vol_5d": scalar_data["fast_vol_5d"],
            "thin_history": scalar_data["thin_history"],
            "observation_only": True,
            "note": "Logged only. Does not feed order_engine.py or ERC_LIVE_SIZING.",
        }
        records.append(record)

    out_path = os.path.join(log_dir, OBSERVATION_LOG_NAME)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "a", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, default=str) + "\n")

    return records


def print_observation(records: list):
    """Human-readable summary, mirroring WeightProposer.print_proposal's style."""
    W = 78
    print("=" * W)
    print(f"  VOL SCALAR OBSERVATION (log-only, no live authority)  {records[0]['date'] if records else ''}")
    print("=" * W)
    hdr = (f"  {'Sleeve':<16} {'Pre-Scalar':>11} {'EWMA':>7} {'Fast':>7} "
           f"{'Combined':>9} {'Post-Scalar':>12} {'Thin?':>6}")
    print(hdr)
    print("  " + "-" * (W - 2))
    for r in records:
        pre = f"{r['weight_pre_scalar']:.4f}" if r["weight_pre_scalar"] is not None else "  N/A"
        post = f"{r['weight_post_scalar_observation_only']:.4f}" if r["weight_post_scalar_observation_only"] is not None else "  N/A"
        print(
            f"  {r['sleeve']:<16} {pre:>11} {r['vol_scalar_ewma']:>7.3f} "
            f"{r['vol_scalar_fast_spike']:>7.3f} {r['vol_scalar_combined']:>9.3f} "
            f"{post:>12} {str(r['thin_history']):>6}"
        )
    print("  " + "-" * (W - 2))
    print("=" * W)


if __name__ == "__main__":
    records = run_observation()
    print_observation(records)
