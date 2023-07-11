import schedutils
from datetime import datetime
from quantrocket.realtime import get_prices 
from quantrocket.blotter import place_order, download_executions
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

YAHOO_DATA_DIRECTORY = os.environment.get('YAHOO_DATA_DIRECTORY', '/home/jcarter/work/trading/data/')

POS_MGR = PosMgr()

START_TIME = "09:25"
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
        logger.info(f'{symbol} historical data loaded.'}
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
    order_id = place_order(**order)
    logger.info(f'order_id: {order_id} submitted.')
    logger.info(json.dumps(order, ensure_ascii=False, indent =4 ))

    return order_id 


def get_current_bid_ask(symbol):

    fields = ["Bid", "Ask"]
    prices = get_prices([symbol], fields)

    # Extract the bid and ask prices for SPY
    bid_price = prices.loc[symbol, "Bid"]
    ask_price = prices.loc[symbol, "Ask"]
    logger.info(f'current bid/ask for {symbol}: bid:{bid_price}, ask:{ask_price}')

    return bid_price, ask_price

def get_current_price(symbol):
    bid, ask = get_current_bid_ask(symbol)
    return 0.5 * (bid + ask)


def calc_trade_amount(symbol, trade_capital):
    bid, ask = get_current_bid_ask(symbol)
    spread = abs(bid - ask)

    ## we can get more creative with this by monitoring spread
    ## in realtime and using an average spread...
    return int( (trade_capital/(ask+spread)) )


async def handle_trade_fills():

    global POS_MGR

    ## handle fills and post all files through PosMgr object
    ## handle trade fills only stays up for 30 min

    """
    Here are some common fields that you may typically find in the executions DataFrame:

    OrderRef: The reference or ID of the order associated with the execution.
    Symbol: The symbol or ticker of the instrument being traded.
    Exchange: The exchange where the execution occurred.
    Quantity: The quantity of the executed order.
    Side: The side of the executed order (Buy or Sell).
    Price: The execution price.
    Currency: The currency of the traded instrument.
    ExecutionTime: The timestamp of the execution.
    Account: The account associated with the execution.
    Strategy: The strategy or algorithm associated with the execution.

    """

    ## map quantrocket order fill
    def _convert_quantrocket_order(order):
        trd = Trade( order['OrderRef'] )
        trd.asset = order["Symbol"]
        trd.exchange = order["Exchange"]
        trd.side = TradeSide.SELL if order["Side"] == 'SELL' else TradeSide.BUY
        trd.units = abs(order["Quantity"])
        trd.price = order["Price"]
        #trd.commission = order["commission"]
        trd.timestamp = order["ExecutionTime"]
        return trd

    counter = 0 
    FETCH_WINDOW = 1800   ## 30min

    start_date = end_date = datetime.today.date()

    while counter < FETCH_WINDOW

        filled_orders = download_executions(start_date, end_date, accounts=IB_ACCOUNT_NAME)

        for order in filled_orders:
            logger.info(f'Processing order_id: {order["OrderRef"]}')
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
    logger.info(f'sleeping until {start_time.strftime("%Y%m%d-%H:%M:%S")} START.')
    await asyncio.sleep(secs_until_start)
    logger.info(f'*** START ***')

    if current_pos == 0:
        trade_amt = calc_trade_amount(symbol, position_node.trade_capital)
        if fire_entry and trade_amt > 0:
            open_time, secs_until_open = time_until(OPEN_TIME)
            logger.info(f'sleeping until {open_time.strftime("%Y%m%d-%H:%M:%S")} OPEN.')
            await asyncio.sleep(secs_until_open)
            logger.info(f'*** SENDING TRADE ON OPEN ***')
            asyncio.create_task( handle_trade_fills() )
            entry_tkt = create_order(TradeSide.BUY, symbol, trade_amt, strategy_id)
        else:
            logger.warning('entry triggered but trade_amt == 0!')
    else:
        logger.info(f'no trade: working open position: {symbol} {current_pos}')

    exit_time, secs_until_exit = time_until(EXIT_TIME)
    logger.info(f'sleeping until {exit_time.strftime("%Y%m%d-%H:%M:%S")} CLOSE.')
    await asyncio.sleep(secs_until_exit)
    logger.info(f'*** CHECKING CLOSE ***')

    position_node = POS_MGR.get_position(symbol)
    fire_exit, current_pos = check_exit(position_node, stdv)
    if fire_exit: 
        asyncio.create_task( handle_trade_fills() )
        exit_tkt = create_order(TradeSide.SELL, symbol, current_pos, strategy_id)

    eod_time, secs_until_eod = time_until(EOD_TIME)
    logger.info(f'sleeping until {eod_time.strftime("%Y%m%d-%H:%M:%S")} END OF DAY.')
    await asyncio.sleep(secs_until_eod)
    logger.info(f'*** END OF DAY ***')


if __name__ == "__main__":
    asyncio.run( main(u.strategy_id, universe=universe) )

    
