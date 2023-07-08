import schedutils
from datetime import datetime
from quantrocket.blotter import order_statuses, OrderStatuses
from quantrocket.realtime import collect_market_data
import asyncio
from posmgr import PosMgr, TradeSide
import calendar_calcs
from indicators import MondayAnchor
import os


# Connect to QuantRocket
# Make sure you have a running QuantRocket deployment
# and have configured the necessary credentials

# Set the account
account = "YOUR_ACCOUNT_NAME"

YAHOO_DATA_DIRECTORY = os.environment.get('YAHOO_DATA_DIRECTORY', '/home/jcarter/work/trading/data/')

START_TIME = "09:25"
OPEN_TIME = "09:30"
EXIT_TIME = "15:55"
EOD_TIME = "16:30"

def time_until(date_string):
    now = datetime.now()
    return schedutils.seconds_until(now, date_string) 

def load_historical_data(symbol):
    ## load yahoo OHLC data
    try:
        stock_file = f'{YAHOO_DATA_DIRECTORY}/{symbol}.csv'
        stock_df = pandas.read_csv(stock_file)
        stock_df.set_index('Date', inplace=True)
    except Exception as e:
        raise e 

def place_entry(symbol, data):

    execute_entry = False 

    daysback = 20
    holidays = calendar_calcs.load_holidays()
    anchor = MondayAnchor(derived_len=days_back)

    ss = len(data)
    if ss < daysback:
        raise RuntimeError(f'Not enoungh data points for {symbol}: len={ss}, daysback={daysback}')

    today = datetime.today().date()
    gg = stock_df[-days_back:]
    end_of_week = calendar_calcs.is_end_of_week(today, holidays)

    last_indicator_date = None
    for i in range(gg.shape[0]):
        idate = gg.index[i]
        stock_bar = gg.loc[idate]
        cur_dt = datetime.strptime(idate,"%Y-%m-%d").date()
        anchor.push((cur_dt, stock_bar))
        last_indicator_date = cur_dt

    ## get make sure the siganl is for the previous trading day
    if last_indicator_date != calendar_calcs.prev_trading_day(today, holidays):
        raise RuntimeError(f'incomplete data for indicators, last_indicator_date: {last_indicator_date}') 

    if anchor.count() > 0:
        anchor_bar, bkout = anchor.valueAt(0)
        if bkout < 0 and end_of_week == False:
            execute_entry = True

    return execute_entry 



def place_exit(current_price, entry_price, duration):
    
    execute_exit = False

    if ( current_price > entry_price ) or
       ( duration > MAX_HOLD_PERIOD )  or
       ( (entry_price - current_price) > stdv ): 
        execute_exit = True 

    return execute_exit
    

def create_order(side, amount, symbol):
    # Create a market order to buy 100 shares of SPY
    order = {
        "account": account,
        "contract": {
            "symbol": symbol.upper(),
            "exchange": "SMART",
            "currency": "USD",
            "secType": "STK"
        },
        "orderType": "MKT",
        "action": TradeSide.BUY,
        "quantity": int(amount) 
    }

    # Place the order
    ib_order_id = "YOUR_IB_ORDER_ID"  # Provide the IB order ID
    ticket = OrderStatuses.submit_order(order, ib_order_id)

    return ticket 


def get_current_price(symbol):
    ## get current realtime price

def calc_trade_amount(symbol, trade_capital, fudge_factor=1):
    ## FIX THIS 
    ## get current price 
    ## problem: how to do handle price moving away from current price before fill?
    ## currently using fudge factor <= 1 to handle problem
    current_price = get_current_price(symbol)
    return int( (trade_capital * fudge_factor)/current_price )

async def handle_trade_fills():
    ## handle fills and post all files through PosMgr object
    ## handle trade fills only stays up for 30 min

    counter = 0 
    FETCH_WINDOW = 1800 
    while counter < FETCH_WINDOW
        # Get the order statuses
        statuses = order_statuses(account=account)

        filled_orders = [status for status in statuses if status["status"] == "filled"]

        for order in filled_orders:
            # Capture the filled order details
            order_id = order["orderId"]
            symbol = order["symbol"]
            exchange = order["exchange"]
            side = order["action"]
            quantity = order["filled"]
            price = order["avgFillPrice"]
            commission = order["commission"]

            print("Order ID:", order_id)
            print("Symbol:", symbol)
            print("Exchange:", exchange)
            print("Side:", side)
            print("Quantity:", quantity)
            print("Price:", price)
            print("Commission:", commission)

        ## FIX 
        ## update positions 

        counter += 1
        # Sleep for 1 second before checking for new filled orders
        await asyncio.sleep(1)


async def main(strategy_id, universe):

    pmgr = PosMgr(strategy_id=strategy_id, universe=universe)
    pmgr.load_all()

    pp = pmgr.position_count()
    if pp == 0:
        raise RuntimeError(f'No targeted positions for universe: {universe}')
    if pp != 1:
        raise RuntimeError(f'Too many names: {pmgr.positions} - this a single name strategy')

    ## grab the only instrument in the universe
    symbol = universe[0]

    ## returns a PosNode object
    position_node = pmgr.get_position(symbol)
    current_pos = position_node.position

    data = load_historical_data(symbol)
    
    start_time, secs_until_start = time_until(START_TIME)
    await asyncio.sleep(secs_until_start)

    if current_pos == 0 and place_entry(symbol, data):
        trade_amt = calc_trade_amount(symbol, position_node.trade_capital)
        if trade_amt > 0:
            asyncio.create_task(handle_trade_fills)
            open_time, secs_until_open = time_until(OPEN_TIME)
            await asyncio.sleep(secs_until_open)
            entry_tkt = create_order(TradeSide.BUY, symbol, trade_amt)

    exit_time, secs_until_exit = time_until(EXIT_TIME)
    await asyncio.sleep(secs_until_exit)

    position_node = pmgr.get_position(symbol)
    current_pos, duration = position_node.position, position_node.duration
    current_price = get_current_price()
    if current_pos > 0 and place_exit(current_price, entry_price, duration)
        asyncio.create_task(handle_trade_fills)
        exit_tkt = create_order(TradeSide.SELL, symbol, current_pos)

    eod_time, secs_until_eod = time_until(EOD_TIME)
    await asyncio.sleep(secs_until_eod)


if __name__ == "__main__":
    asyncio.run( main(u.strategy_id, universe=universe) )

    
