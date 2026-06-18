import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from ib_insync import IB, Stock, Index
import pandas as pd
import os

# ── Config ───────────────────────────────────────────────────────────────────
PORT      = 7497   # paper trading port — never change to 7496
CLIENT_ID = 2
DATA_DIR  = 'data'
os.makedirs(DATA_DIR, exist_ok=True)

TICKERS = ['SPY', 'QQQ', 'IWM', 'XLK', 'SMH', 'EEM', 'EWJ',
           'TLT', 'IEF', 'GLD', 'FXE', 'FXY']

ib = IB()
ib.connect('127.0.0.1', PORT, clientId=CLIENT_ID)

all_closes = {}

for symbol in TICKERS:
    contract = Stock(symbol, 'SMART', 'USD')
    ib.qualifyContracts(contract)

    bars = ib.reqHistoricalData(
        contract,
        endDateTime='',
        durationStr='3 Y',
        barSizeSetting='1 day',
        whatToShow='ADJUSTED_LAST',
        useRTH=True,
        formatDate=1
    )

    df = pd.DataFrame([{'date': b.date, 'close': b.close} for b in bars])
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    all_closes[symbol] = df['close']
    print(f"{symbol}: {len(df)} bars, {df.index[0].date()} to {df.index[-1].date()}")

# VIX is an index, not a stock
vix_contract = Index('VIX', 'CBOE', 'USD')
ib.qualifyContracts(vix_contract)
vix_bars = ib.reqHistoricalData(
    vix_contract,
    endDateTime='',
    durationStr='3 Y',
    barSizeSetting='1 day',
    whatToShow='TRADES',
    useRTH=True,
    formatDate=1
)
vix_df = pd.DataFrame([{'date': b.date, 'close': b.close} for b in vix_bars])
vix_df['date'] = pd.to_datetime(vix_df['date'])
vix_df.set_index('date', inplace=True)
all_closes['VIX'] = vix_df['close']
print(f"VIX: {len(vix_df)} bars, {vix_df.index[0].date()} to {vix_df.index[-1].date()}")

ib.disconnect()

prices_df = pd.DataFrame(all_closes)
prices_df.to_csv(os.path.join(DATA_DIR, 'prices.csv'))
print(f"\nSaved to {DATA_DIR}/prices.csv  |  Shape: {prices_df.shape}")
print(prices_df.tail())
