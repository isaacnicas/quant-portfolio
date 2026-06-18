import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import json
import os
import pandas as pd
from ib_insync import IB, Stock, Order
from position_sizer import size_today_positions
from signal_engine import generate_today_signal

# ── Safety settings ──────────────────────────────────────────────────────────
DRY_RUN       = True    # set to False only when ready to place real paper orders
MIN_TRADE_USD = 100     # skip trades smaller than $100 notional
CLIENT_ID     = 3
PORT          = 7497    # paper trading port — never change to 7496

DATA_DIR      = 'data'
POSITIONS_FILE = os.path.join(DATA_DIR, 'last_positions.json')


def load_last_positions():
    if not os.path.exists(POSITIONS_FILE):
        return None
    with open(POSITIONS_FILE) as f:
        return json.load(f)


def save_positions(weights_dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(POSITIONS_FILE, 'w') as f:
        json.dump(weights_dict, f, indent=2)


def get_account_nav(ib):
    for item in ib.accountSummary():
        if item.tag == 'NetLiquidation':
            return float(item.value)
    raise ValueError("Could not read NAV from account summary")


def get_current_positions(ib):
    return {p.contract.symbol: p.position for p in ib.positions()}


def get_current_prices(ib, tickers):
    """
    Read today's closing prices from local CSV.
    Avoids needing a live market data subscription.
    """
    df       = pd.read_csv('data/prices.csv', index_col='date', parse_dates=True)
    last_row = df.iloc[-1]
    prices   = {}
    for symbol in tickers:
        if symbol in last_row.index:
            prices[symbol] = float(last_row[symbol])
        else:
            print(f"  WARNING: {symbol} not found in prices.csv")
    return prices


def compute_orders(target_weights, current_positions, current_prices, nav):
    orders = []
    active_tickers = target_weights[target_weights > 0].index.tolist()
    all_tickers    = list(set(active_tickers) | set(current_positions.keys()))

    for symbol in all_tickers:
        target_weight  = float(target_weights.get(symbol, 0.0))
        price          = current_prices.get(symbol)

        if not price:
            print(f"  SKIPPED {symbol}: no price available")
            continue

        target_shares  = int((target_weight * nav) / price)
        current_shares = int(current_positions.get(symbol, 0))
        delta_shares   = target_shares - current_shares
        notional_usd   = abs(delta_shares) * price

        if abs(delta_shares) == 0:
            continue
        if notional_usd < MIN_TRADE_USD:
            print(f"  SKIPPED {symbol}: ${notional_usd:.0f} below "
                  f"${MIN_TRADE_USD} minimum")
            continue

        action = 'BUY' if delta_shares > 0 else 'SELL'
        orders.append((symbol, action, abs(delta_shares), notional_usd))

    return orders


def submit_orders(ib, orders):
    submitted = []
    for symbol, action, shares, notional in orders:
        contract = Stock(symbol, 'SMART', 'USD')
        ib.qualifyContracts(contract)

        order = Order(
            action=action,
            totalQuantity=shares,
            orderType='MKT',
            tif='DAY',
            transmit=True
        )

        if DRY_RUN:
            print(f"  [DRY RUN] {action} {shares} {symbol} MKT "
                  f"(~${notional:,.0f} notional)")
        else:
            trade = ib.placeOrder(contract, order)
            print(f"  SUBMITTED: {action} {shares} {symbol} MKT "
                  f"| orderId={trade.order.orderId} "
                  f"| ~${notional:,.0f} notional")
            submitted.append(trade)

    return submitted


if __name__ == '__main__':
    print("=" * 60)
    print(f"ORDER ENGINE  |  DRY_RUN={DRY_RUN}  |  PORT={PORT}")
    print("=" * 60)

    # Load previous weights for dead-band comparison
    prev_weights = load_last_positions()

    signal_result  = generate_today_signal()
    target_weights = size_today_positions(signal_result, prev_weights=prev_weights)
    print(f"\nGross exposure: {target_weights.abs().sum():.2%}")

    ib = IB()
    ib.connect('127.0.0.1', PORT, clientId=CLIENT_ID)
    print(f"Connected: {ib.isConnected()}")

    nav               = get_account_nav(ib)
    current_positions = get_current_positions(ib)
    print(f"Paper NAV: ${nav:,.2f}")
    print(f"Current positions: "
          f"{current_positions if current_positions else 'none'}")

    active_tickers = target_weights[target_weights > 0].index.tolist()
    print(f"\nFetching prices for {len(active_tickers)} tickers...")
    current_prices = get_current_prices(ib, active_tickers)
    for sym, price in current_prices.items():
        print(f"  {sym}: ${price:.2f}")

    orders = compute_orders(target_weights, current_positions,
                            current_prices, nav)
    print(f"\n{len(orders)} orders to place:")
    submit_orders(ib, orders)

    ib.disconnect()
    print("\nDone.")
