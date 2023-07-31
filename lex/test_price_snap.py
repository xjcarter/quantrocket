
from price_scrapper import PriceSnapper
from clockutils import TripWire, time_from_str
import time
from datetime import datetime
import pandas

symbol = 'UPRO'
p = PriceSnapper(symbol)
constant_snap = TripWire(time_from_str("09:30"), interval_reset=60, stop_at=time_from_str("16:00"))
eod = TripWire(time_from_str("16:00"))

time_series = []
while True:
    with constant_snap as snap_prices:
        if snap_prices:
            bid, ask, mid = p.snap_prices()
            print(f'snap: {snap_prices.datetime}: {bid}, {ask}')
            nn = datetime.now()
            dt_snap = nn.strftime("%Y%m%d")
            time_snap = nn.strftime("%H%M%S")
            time_series.append([dt_snap, time_snap, symbol, mid])

    with eod as end_of_day:
        if end_of_day:
            print('end of day')
            break

    time.sleep(1)

df = pandas.DataFrame(columns=['Date','Time', 'Symbol', 'Price'], data=time_series)
df.set_index('Date', inplace=True)
today = datetime.now().strftime("%Y%m%d")
df.to_csv(f'{symbol}_snaps_{today}.py')
            
    
