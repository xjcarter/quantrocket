import schedutils
from datetime import datetime
#from quantrocket.realtime import get_prices 
#from quantrocket.blotter import place_order, download_executions
import test_harness
import asyncio
from posmgr import PosMgr, TradeSide, Trade, OrderType, OrderTicket
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
        logger.info(f'{symbol} historical data loaded.')
    except Exception as e:
        raise e
    
    ## alter data for testing 
    stock_df = test_harness.alter_data_to_anchor(stock_df, adjust_close=-0.03)

    return stock_df


def calc_metrics(stock_df):

    valid_entry = False

    daysback = 50
    holidays = calendar_calcs.load_holidays()
    anchor = MondayAnchor(derived_len=daysback)
    stdev = StDev(sample_size=daysback)

    ss = len(stock_df)
    if ss < daysback:
        logger.error(f'Not enoungh data to calc metrics: len={ss}, daysback={daysback}')
        raise RuntimeError(f'Not enoungh data to calc metrics: len={ss}, daysback={daysback}')

    today = datetime.today().date()
    gg = stock_df[-daysback:]
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


def check_exit(position_node, stdv):

    current_pos, entry_price = position_node.position, position_node.price
    duration = position_node.duration
    test_harness.price_skew = 0.10
    current_price = test_harness.get_current_price(position_node.name)
    #current_price = get_current_price(position_node.name)

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

    logger.info(f'check_exit: exit= {get_out}, {position_node.name}, {current_pos}')
    logger.info(f'exit_details: {position_node.name}, alert= {alert} current_price= {current_price}, entry= {entry_price}, duration= {duration}')
    return get_out, current_pos
    

## creates and submits order
## order_notes is a field to hold any info that many help in auditting trades
def create_order(side, amount, symbol, order_type=OrderType.MKT, order_notes=None):

    def _new_order_id(tag=None):
        # Generate a unique order ID with timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())
        if tag is not None:
            return f"{tag}-{unique_id}-{timestamp}"
        else:
            return f"{unique_id}-{timestamp}"

    # Create a market order to buy 100 shares of SPY

    order = {
        "account": IB_ACCOUNT_NAME,
        "symbol": symbol,
        "quantity": amount,
        "action": side.value,
        "order_type": order_type.value
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

    order_info = {
        'order_id': order_id,
        'symbol': order['symbol']
        'quantity': order['quantity']
        'side': order['action']
        'order_type': order['order_type']
        'info': order_notes
    }
    logger.info(json.dumps(order_info, ensure_ascii=False, indent =4 ))

    return order_info


def calc_trade_amount(symbol, trade_capital):
    bid, ask = get_current_bid_ask(symbol)
    spread = abs(bid - ask)

    ## we can get more creative with this by monitoring spread
    ## in realtime and using an average spread...
    return int( trade_capital/(ask+spread) )


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

    def _get_side(order):
        sides = { 'BUY': TradeSide.BUY, 'SELL': TradeSide.SELL }
        v = order.get('side', order.get('action'))
        if v is not None:
            return sides[v]
        else:
            raise RuntimeError(f'no BUY/SELL action indicated in order!\n order: {order}')

    ## map quantrocket order fill
    def _convert_quantrocket_order(order):
        trd = Trade( order['OrderRef'] )
        trd.asset = order["symbol"]
        trd.side = _get_side(order)
        trd.units = abs(order["quantity"])
        trd.price = order["price"]

        ## conditionals
        trd.timestamp = order.get("timestamp")
        if trd.timestamp is None: trd.stamp_timestamp()
        trd.commission = order.get("commission")
        trd.exchange = order.get("exchange")

        return trd


    counter = 0 
    FETCH_WINDOW = 1200   ## 20min


    logger.info('Fill capture coroutine started.')
    while counter < FETCH_WINDOW:

        #filled_orders = download_executions(orderid= orderid)
        filled_orders = test_harness.download_executions(orderid= orderid)

        for order in filled_orders:
            logger.info(f'Processing order_id: {order["OrderRef"]}')
            POS_MGR.update_trades( order, conversion_func=_convert_quantrocket_order )

        counter += 1
        # Sleep for 1 second before checking for new filled orders
        await asyncio.sleep(1)

    logger.info('Fill capture coroutine completed.')


async def main(strategy_id, universe):

    global POS_MGR

    logger.info(f'*** START ***')

    POS_MGR.initialize(strategy_id, set(universe))
    logger.info(f'pos mgr initialized.')

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
    logger.info(f'{symbol} current position = {current_pos}'

    data = load_historical_data(symbol)
    fire_entry, stdv = calc_metrics(data)

    logger.info(f'trading metrics calculated.')

    open_task = close_task = None
    
    if current_pos == 0:
        trade_amt = calc_trade_amount(symbol, position_node.trade_capital)
        if fire_entry and trade_amt > 0:
            open_time, secs_until_open = time_until(OPEN_TIME)
            logger.info(f'sleeping until {open_time.strftime("%Y%m%d-%H:%M:%S")} OPEN.')
            await asyncio.sleep(secs_until_open)
            logger.info(f'*** SENDING TRADE ON OPEN ***')

            test_harness.price_skew = 0
            open_price = get_current_price(position_node.name)

            logger.info(f'opening price: {open_price}')
            open_task = asyncio.create_task( handle_trade_fills() )
            order_info = create_order(TradeSide.BUY, symbol, trade_amt, order_notes=strategy_id)
            POS_MGR.register_order(order_info)
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
        close_task = asyncio.create_task( handle_trade_fills() )
        order_info = create_order(TradeSide.SELL, symbol, current_pos, order_notes=strategy_id)
        POS_MGR.register_order(order_info)

    eod_time, secs_until_eod = time_until(EOD_TIME)
    logger.info(f'sleeping until {eod_time.strftime("%Y%m%d-%H:%M:%S")} END OF DAY.')
    await asyncio.sleep(secs_until_eod)
    logger.info(f'*** END OF DAY ***')

    await asyncio.gather(open_task, close_task)


if __name__ == "__main__":
    asyncio.run( main(u.strategy_id, universe=universe) )

