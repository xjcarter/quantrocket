import schedutils
from datetime import datetime
#from quantrocket.realtime import get_prices 
#from quantrocket.blotter import place_order, download_executions
import asyncio
from posmgr import PosMgr, TradeSide, Trade
import calendar_calcs
from indicators import MondayAnchor, StDev
import os
import uuid

import logging
# Create a logger specific to __main__ module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s',
                    datefmt='%a %Y-%m-%d %H:%M:%S')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


# Connect to QuantRocket
# Make sure you have a running QuantRocket deployment
# and have configured the necessary credentials

# Set the account
IB_ACCOUNT_NAME = "YOUR_ACCOUNT_NAME"

YAHOO_DATA_DIRECTORY = os.environ.get('YAHOO_DATA_DIRECTORY', '/home/jcarter/work/trading/data/')

POS_MGR = PosMgr()

START_TIME = "09:20"
OPEN_TIME = "09:30"
EXIT_TIME = "15:55"
EOD_TIME = "16:30"

MAX_HOLD_PERIOD = 9


def time_until(date_string):
    now = datetime.now()
    return schedutils.seconds_until(now, date_string) 


def load_historical_data(symbol):
    ## load yahoo OHLC data
    try:
        stock_file = f'{YAHOO_DATA_DIRECTORY}/{symbol}.csv'
        stock_df = pandas.read_csv(stock_file)
        stock_df.set_index('Date', inplace=True)
        logger.info(f'{symbol} historical data loaded.')
    except Exception as e:
        raise e
    
    ## alter data for testing 
    stock_df = test_harness.alter_data_to_anchor(stock_df, alter_close=-0.03)

    return stock_df


def calc_metrics(stock_df):

    valid_entry = False

    daysback = 50
    holidays = calendar_calcs.load_holidays()
    anchor = MondayAnchor(derived_len=daysback)
    stdev = StDev(sample_size=daysback)

    ss = len(data)
    if ss < daysback:
        logger.error(f'Not enoungh data to calc metrics: len={ss}, daysback={daysback}')
        raise RuntimeError(f'Not enoungh data to calc metrics: len={ss}, daysback={daysback}')

    today = datetime.today().date()
    gg = stock_df[-days_back:]
    end_of_week = calendar_calcs.is_end_of_week(today, holidays)

    last_indicator_date = None
    last_close = None
    for i in range(gg.shape[0]):
        idate = gg.index[i]
        stock_bar = gg.loc[idate]
        cur_dt = datetime.strptime(idate,"%Y-%m-%d").date()
        anchor.push((cur_dt, stock_bar))
        stdev.push(stock_bar['Close'])
        last_indicator_date = cur_dt
        last_close = stock_bar['Close']

    ## make sure the signal is for the previous trading day
    if last_indicator_date != calendar_calcs.prev_trading_day(today, holidays):
        logger.error(f'incomplete data for indicators, last_indicator_date: {last_indicator_date}') 
        raise RuntimeError(f'incomplete data for indicators, last_indicator_date: {last_indicator_date}') 

    ldate = last_indicator_date.strftime("%Y%m%d %a")
    if anchor.count() > 0:
        anchor_bar, bkout = anchor.valueAt(0)
        ## show last indcator date, anchor bar and close
        logger.info(f'>>> {ldate}: A:{anchor_bar}, C:{last_close}')
        if bkout < 0 and end_of_week == False:
            valid_entry = True

    return valid_entry, stdev.valueAt(0) 



def check_exit(position_node, stdv):

    current_pos, entry_price = position_node.position, position_node.price
    duration = position_node.duration
    test_harness.price_skew = 0.10
    current_price = get_current_price(position_node.symbol)

    get_out = False
    alert = 'NO_EXIT'
    if current_pos > 0:
        if current_price > entry_price:
            alert = 'PNL'
            get_out = True
        elif duration > MAX_HOLD_PERIOD:
            alert = 'EXPIRY'
            get_out = True
        elif (entry_price - current_price) > stdv * 2: 
            alert = 'STOP ON CLOSE'
            get_out = True 

    logger.info('check_exit: exit= {get_out}, {position_node.symbol}, {current_pos}')
    logger.info('exit_details: {tag}  current_price= {current_price}, entry= {entry_price}, duration= {duration}')
    return get_out, current_pos
    

def create_order(side, amount, symbol, strategy_id):

    def _new_order_id(tag):
        # Generate a unique order ID with timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())
        return f"{tag}_{timestamp}_{unique_id}"

    # Create a market order to buy 100 shares of SPY

    order = {
        "account": "YOUR_ACCOUNT",
        "symbol": "SPY",
        "quantity": 100,
        "action": TradeSide.BUY,
        "order_type": "MKT"
    }

    logger.info('sending order.')

    # Place the order

    #legacy submission
    #ib_order_id = _new_order_id(strategy_id) 
    #ticket = OrderStatuses.submit_order(order, ib_order_id)

    #order_id = place_order(account, symbol, quantity, action, order_type)
    #order_id = place_order(**order)
    order_id = test_harness.place_order(**order)
    logger.info(f'order_id: {order_id} submitted.')
    logger.info(json.dumps(order, ensure_ascii=False, indent =4 ))

    return order_id 


def get_current_bid_ask(symbol):

    fields = ["Bid", "Ask"]
    #prices = get_prices([symbol], fields)
    prices = test_harness.get_prices([symbol], fields)

    # Extract the bid and ask prices for SPY
    bid_price = prices.loc[symbol, "Bid"]
    ask_price = prices.loc[symbol, "Ask"]
    logger.info(f'current bid/ask for {symbol}: bid:{bid_price}, ask:{ask_price}')

    return bid_price, ask_price

def get_current_price(symbol):
    bid, ask = get_current_bid_ask(symbol)
    avg_price = 0.5 * (bid + ask)
    logger.info(f'current avg_price for {symbol}: {avg_price}')
    return avg_price



def calc_trade_amount(symbol, trade_capital):
    bid, ask = get_current_bid_ask(symbol)
    spread = abs(bid - ask)

    ## we can get more creative with this by monitoring spread
    ## in realtime and using an average spread...
    return int( (trade_capital/(ask+spread)) )


async def handle_trade_fills(tag):

    logger.info(f'handle_fills_start: {tag}') 

    counter = 0 
    FETCH_WINDOW = 60  ## 30min

    while counter < FETCH_WINDOW:
        
        logger.info(f'Processing potential orders')

        counter += 1
        # Sleep for 20 seconds before checking for new filled orders
        await asyncio.sleep(20)

    logger.info(f'handle_fills_end {tag}') 


async def main(strategy_id, universe):

    logger.info('start main')
    start_time, secs_until_start = time_until(START_TIME)
    logger.info(f'sleeping until {start_time.strftime("%Y%m%d-%H:%M:%S")} START.')
    await asyncio.sleep(secs_until_start)
    logger.info(f'*** START ***')

    open_time, secs_until_open = time_until(OPEN_TIME)
    logger.info(f'sleeping until {open_time.strftime("%Y%m%d-%H:%M:%S")} OPEN.')
    await asyncio.sleep(secs_until_open)
    logger.info(f'*** SENDING TRADE ON OPEN ***')
    asyncio.create_task( handle_trade_fills('OPEN') )

    exit_time, secs_until_exit = time_until(EXIT_TIME)
    logger.info(f'sleeping until {exit_time.strftime("%Y%m%d-%H:%M:%S")} EXIT.')
    await asyncio.sleep(secs_until_exit)
    logger.info(f'*** EXIT -> CHECKING CLOSE ***')
    asyncio.create_task( handle_trade_fills('CLOSE') )

    eod_time, secs_until_eod = time_until(EOD_TIME)
    logger.info(f'sleeping until {eod_time.strftime("%Y%m%d-%H:%M:%S")} END OF DAY.')
    await asyncio.sleep(secs_until_eod)
    logger.info(f'*** END OF DAY ***')


if __name__ == "__main__":
    asyncio.run( main('12345', ['SPY']) )

