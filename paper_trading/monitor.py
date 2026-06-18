import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import json
import os
import pandas as pd
from datetime import datetime
from ib_insync import IB
from signal_engine import generate_today_signal
from position_sizer import size_today_positions

PORT      = 7497
CLIENT_ID = 4
DATA_DIR  = 'data'
os.makedirs(DATA_DIR, exist_ok=True)

POSITIONS_FILE   = os.path.join(DATA_DIR, 'last_positions.json')
PERFORMANCE_FILE = os.path.join(DATA_DIR, 'live_performance.csv')


def save_positions(weights_dict):
    with open(POSITIONS_FILE, 'w') as f:
        json.dump(weights_dict, f, indent=2)
    print(f"Positions saved to {POSITIONS_FILE}")


def get_nav(ib):
    for item in ib.accountSummary():
        if item.tag == 'NetLiquidation':
            return float(item.value)
    return None


def get_portfolio(ib):
    result = {}
    for item in ib.portfolio():
        symbol = item.contract.symbol
        result[symbol] = {
            'shares'        : item.position,
            'avg_cost'      : item.averageCost,
            'market_value'  : item.marketValue,
            'unrealized_pnl': item.unrealizedPNL,
        }
    return result


def log_performance(date, nav, unrealized_pnl, n_positions):
    row    = {'date': date, 'nav': nav,
              'unrealized_pnl': unrealized_pnl, 'n_positions': n_positions}
    df_new = pd.DataFrame([row])

    if os.path.exists(PERFORMANCE_FILE):
        df_out = pd.concat([pd.read_csv(PERFORMANCE_FILE), df_new],
                           ignore_index=True)
    else:
        df_out = df_new

    df_out.to_csv(PERFORMANCE_FILE, index=False)
    print(f"Performance logged to {PERFORMANCE_FILE}")


if __name__ == '__main__':
    print("=" * 60)
    print(f"DAILY MONITOR  |  {datetime.today().date()}  |  PORT={PORT}")
    print("=" * 60)

    ib = IB()
    ib.connect('127.0.0.1', PORT, clientId=CLIENT_ID)

    nav       = get_nav(ib)
    portfolio = get_portfolio(ib)

    print(f"\nNAV: ${nav:,.2f}")
    print(f"\nCurrent positions:")

    total_unrealized = 0
    current_weights  = {}
    for sym, p in portfolio.items():
        print(f"  {sym:6s}  {int(p['shares']):>5} shares  "
              f"MktVal=${p['market_value']:>10,.0f}  "
              f"UnrealPnL=${p['unrealized_pnl']:>+8,.0f}")
        total_unrealized += p['unrealized_pnl']
        if nav and nav > 0:
            current_weights[sym] = p['market_value'] / nav

    print(f"\nTotal unrealized P&L: ${total_unrealized:+,.0f}")

    # Save weights for next rebalance dead-band comparison
    save_positions(current_weights)

    # Log to performance CSV
    log_performance(
        date            = str(datetime.today().date()),
        nav             = nav,
        unrealized_pnl  = total_unrealized,
        n_positions     = len([p for p in portfolio.values()
                               if p['shares'] != 0])
    )

    # Show current signal state and next rebalance targets
    print("\n--- Current signal state ---")
    signal_result  = generate_today_signal()
    target_weights = size_today_positions(signal_result,
                                          prev_weights=current_weights)

    print(f"\nTarget weights at next rebalance:")
    active = target_weights[target_weights > 0].sort_values(ascending=False)
    print(active.round(4))
    print(f"Gross exposure: {target_weights.abs().sum():.2%}")

    ib.disconnect()
    print("\nMonitor complete.")
