import schedutils
from datetime import datetime
from quantrocket.blotter import order_statuses, OrderStatuses
from quantrocket.realtime import collect_market_data
import asyncio
from posmgr import PosMgr, TradeSide, Trade
import calendar_calcs
from indicators import MondayAnchor, StDev
import os
import uuid


# Connect to QuantRocket
# Make sure you have a running QuantRocket deployment
# and have configured the necessary credentials

# Set the account
account = "YOUR_ACCOUNT_NAME"

YAHOO_DATA_DIRECTORY = os.environment.get('YAHOO_DATA_DIRECTORY', '/home/jcarter/work/trading/data/')

POS_MGR = PosMgr()

START_TIME = "09:25"
OPEN_TIME = "09:30"
EXIT_TIME = "15:55"
EOD_TIME = "16:30"

MAX_HOLD_PERIOD = 9
EXECUTION_SPREAD = 0.01  ## average spread for the symbol traded


def time_until(date_string):
    now = datetime.now()
    return schedutils.seconds_until(now, date_string) 

def load_historical_data(symbol):
    ## load yahoo OHLC data
    try:
        stock_file = f'{YAHOO_DATA_DIRECTORY}/{symbol}.csv'
        stock_df = pandas.read_csv(stock_file)
        stock_df.set_index('Date', inplace=True)
        print(f'{symbol} historical data loaded.'}
    except Exception as e:
        raise e

    return stock_df


def calc_metrics(data):

    valid_entry = False

    daysback = 50
    holidays = calendar_calcs.load_holidays()
    anchor = MondayAnchor(derived_len=daysback)
    stdev = StDev(sample_size=daysback)

    ss = len(data)
    if ss < daysback:
        print(f'Not enoungh data to calc metrics: len={ss}, daysback={daysback}')
        raise RuntimeError(f'Not enoungh data to calc metrics: len={ss}, daysback={daysback}')

    today = datetime.today().date()
    gg = stock_df[-days_back:]
    end_of_week = calendar_calcs.is_end_of_week(today, holidays)

    last_indicator_date = None
    for i in range(gg.shape[0]):
        idate = gg.index[i]
        stock_bar = gg.loc[idate]
        cur_dt = datetime.strptime(idate,"%Y-%m-%d").date()
        anchor.push((cur_dt, stock_bar))a
        stdev.push(stock_bar['Close'])
        last_indicator_date = cur_dt

    ## get make sure the siganl is for the previous trading day
    if last_indicator_date != calendar_calcs.prev_trading_day(today, holidays):
        print(f'incomplete data for indicators, last_indicator_date: {last_indicator_date}') 
        raise RuntimeError(f'incomplete data for indicators, last_indicator_date: {last_indicator_date}') 

    if anchor.count() > 0:
        anchor_bar, bkout = anchor.valueAt(0)
        if bkout < 0 and end_of_week == False:
            valid_entry = True

    return valid_entry, stdev.valueAt(0) 



def check_exit(position_node, stdv):

    current_pos, entry_price = position_node.position, position_node.price
    duration = position_node.duration
    current_price = get_current_price(position_node.symbol)

    get_out = False
    if current_pos > 0:
        if ( current_price > entry_price ) or
           ( duration > MAX_HOLD_PERIOD )  or
           ( (entry_price - current_price) > stdv * 2 ): 
            get_out = True 

    print('check_exit: exit= {get_out}, {position_node.symbol}, {current_pos}')
    print('exit_details: current_price= {current_price}, entry= {entry_price}, duration= {duration}')
    return get_out, current_pos
    

def create_order(side, amount, symbol, strategy_id):

    def _new_order_id(tag):
        # Generate a unique order ID with timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())
        return f"{tag}_{timestamp}_{unique_id}"

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
        "quantity": amount 
    }

    print('sending order.')

    # Place the order
    ib_order_id = _new_order_id(strategy_id) 
    ticket = OrderStatuses.submit_order(order, ib_order_id)
    print(f'order {ib_order_id}: {ticket} submitted.')
    print(json.dumps(order, ensure_ascii=False, indent =4 ))

    return ticket 


def get_current_price(symbol):
    ## FIX THIS
    ## get current realtime price

def calc_trade_amount(symbol, trade_capital):
    current_price = get_current_price(symbol)
    return int( (trade_capital/(current_price + EXECUTION_SPREAD) )


async def handle_trade_fills():

    global POS_MGR

    ## handle fills and post all files through PosMgr object
    ## handle trade fills only stays up for 30 min

    ## map quantrocket order fill
    def _convert_quantrocket_order(order):
        trd = Trade( order['orderId'] )
        trd.asset = order["symbol"]
        trd.exchange = order["exchange"]
        trd.side = TradeSide.SELL if order["action"] == 'SELL' else TradeSide.BUY
        trd.units = abs(order["filled"])
        trd.price = order["avgFillPrice"]
        trd.commission = order["commission"]
        return trd

    counter = 0 
    FETCH_WINDOW = 1800   ## 30min

    while counter < FETCH_WINDOW
        statuses = order_statuses(account=account)

        filled_orders = [status for status in statuses if status["status"] == "filled"]

        for order in filled_orders:
            print(f'Processing order_id: {order["orderId"]')
            POS_MGR.update_trades( order, conversion_func=_convert_quantrocket_order )

        counter += 1
        # Sleep for 1 second before checking for new filled orders
        await asyncio.sleep(1)


async def main(strategy_id, universe):

    global POS_MGR

    POS_MGR.strategy_id = strategy_id
    POS_MGR.universe = set(universe)
    POS_MGR.load_all()

    pp = POS_MGR.position_count()
    if pp == 0:
        raise RuntimeError(f'No targeted positions for universe: {universe}')
    if pp != 1:
        raise RuntimeError(f'Too many names: {POS_MGR.positions} - this a single name strategy')

    ## grab the only instrument in the universe
    symbol = universe[0]

    ## returns a PosNode object
    position_node = POS_MGR.get_position(symbol)
    current_pos = position_node.position

    data = load_historical_data(symbol)
    fire_entry, stdv = calc_metrics(data)
    
    start_time, secs_until_start = time_until(START_TIME)
    print(f'sleeping until {start_time.strftime("%Y%m%d-%H:%M:%S")} START.')
    await asyncio.sleep(secs_until_start)
    print(f'*** START ***')

    if current_pos == 0 and fire_entry:
        trade_amt = calc_trade_amount(symbol, position_node.trade_capital)
        if trade_amt > 0:
            asyncio.create_task( handle_trade_fills() )
            open_time, secs_until_open = time_until(OPEN_TIME)
            print(f'sleeping until {open_time.strftime("%Y%m%d-%H:%M:%S")} OPEN.')
            await asyncio.sleep(secs_until_open)
            print(f'*** SENDING TRADE ON OPEN ***')
            entry_tkt = create_order(TradeSide.BUY, symbol, trade_amt, strategy_id)

    exit_time, secs_until_exit = time_until(EXIT_TIME)
    print(f'sleeping until {exit_time.strftime("%Y%m%d-%H:%M:%S")} CLOSE.')
    await asyncio.sleep(secs_until_exit)
    print(f'*** CHECKING CLOSE ***')

    position_node = POS_MGR.get_position(symbol)
    fire_exit, current_pos = check_exit(position_node, stdv)
    if fire_exit: 
        asyncio.create_task( handle_trade_fills() )
        exit_tkt = create_order(TradeSide.SELL, symbol, current_pos, strategy_id)

    eod_time, secs_until_eod = time_until(EOD_TIME)
    print(f'sleeping until {eod_time.strftime("%Y%m%d-%H:%M:%S")} END OF DAY.')
    await asyncio.sleep(secs_until_eod)
    print(f'*** END OF DAY ***')


if __name__ == "__main__":
    asyncio.run( main(u.strategy_id, universe=universe) )

    
