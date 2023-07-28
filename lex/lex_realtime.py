from clockutils import TripWire, time_from_str
from datetime import datetime
#from quantrocket.realtime import get_prices 
#from quantrocket.blotter import place_order, download_executions
import test_harness as TESTER 
import time, pandas 
from posmgr import PosMgr, TradeSide, Trade, OrderType
import calendar_calcs
from indicators import MondayAnchor, StDev
import os, sys, json
import uuid

import logging
# Create a logger specific to __main__ module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
FORMAT = "%(asctime)s: %(levelname)8s [%(module)15s:%(lineno)3d - %(funcName)20s ] %(message)s"
#FORMAT = "%(asctime)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s"
formatter = logging.Formatter(FORMAT, datefmt='%a %Y-%m-%d %H:%M:%S')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


# Connect to QuantRocket
# Make sure you have a running QuantRocket deployment
# and have configured the necessary credentials

# Set the account
IB_ACCOUNT_NAME = "YOUR_ACCOUNT_NAME"

YAHOO_DATA_DIRECTORY = os.environ.get('YAHOO_DATA_DIRECTORY', '/home/jcarter/work/trading/data/')
INTRA_PRICES_DIRECTORY = os.environ.get('INTRA_PRICES_DIRECTORY', '/home/jcarter/junk/')

POS_MGR = PosMgr()

ANCHOR_ADJUST = 0 
MAX_HOLD_PERIOD = 9


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
    stock_df = TESTER.alter_data_to_anchor(stock_df, adjust_close=ANCHOR_ADJUST)

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
        if bkout < 0 and end_of_week == False:
            valid_entry = True
        x = "<-" if valid_entry else ""
        logger.info(f'{ldate}: A:{anchor_bar}, C: {last_close} {x}')

    return valid_entry, stdev.valueAt(0) 


def get_current_bid_ask(symbol):

    fields = ["Bid", "Ask"]
    #prices = get_prices([symbol], fields)
    prices = TESTER.get_prices([symbol], fields)

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

def fetch_prices(symbol):
    bar = TESTER.generate_ohlc()
    now = datetime.now().strftime("%Y%m%d-%H:%M:%S")
    logger.info(f'new bar: {now}, {bar}')
    return [now, bar.open, bar.high, bar.low, bar.close] 


def check_exit(position_node, stdv):

    current_pos, entry_price = position_node.position, position_node.price
    duration = position_node.duration

    current_price = get_current_price(position_node.name)

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
            logger.warning('stop on close triggered! current_price= {current_price}')
            get_out = True 

    logger.info(f'check_exit: exit= {get_out}, {position_node.name}, {current_pos}')
    logger.info(f'exit_details: {position_node.name}, alert= {alert} current_price= {current_price}, entry= {entry_price}, duration= {duration}')
    return get_out, current_pos
    

## creates and submits order
## order_notes is a field to hold any info that many help in auditting trades
def create_order(side, symbol, amount, order_type=OrderType.MKT, order_notes=None):

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
        "quantity": amount,
        "symbol": symbol,
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
    order_id = TESTER.place_order(**order)
    logger.info(f'order_id: {order_id} submitted.')

    order_info = {
        'order_id': order_id,
        'symbol': order['symbol'],
        'quantity': order['quantity'],
        'side': order['action'],
        'order_type': order['order_type'],
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


def check_for_fills():

    global POS_MGR

    ## handle fills and post all files through PosMgr object

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

    FIX THIS: you have to adjust _convert_quantrocket_fill 
    """

    def _get_side(fill):
        sides = { 'BUY': TradeSide.BUY, 'SELL': TradeSide.SELL }
        v = fill.get('side', fill.get('action'))
        if v is not None:
            return sides[v]
        else:
            raise RuntimeError(f'no BUY/SELL action indicated in order!\n order: {order}')

    ## map quantrocket order fill
    def _convert_quantrocket_fill(fill):
        trd = Trade( fill['order_id'] )
        trd.asset = fill["symbol"]
        trd.side = _get_side(fill)
        trd.units = abs(int(fill["quantity"]))
        trd.price = fill["price"]

        ## conditionals
        trd.timestamp = fill.get("timestamp")
        if trd.timestamp is None: trd.stamp_timestamp()
        trd.commission = fill.get("commission")
        trd.exchange = fill.get("exchange")

        return trd


    logger.info('checking for fills.')

    #filled_orders = download_executions()
    start_date = end_date = datetime.today().date()
    filled_orders = TESTER.download_executions(start_date, end_date, accounts=[IB_ACCOUNT_NAME])

    for fill in filled_orders:
        logger.info(f'Processing trade_id: {fill["trade_id"]}')
        POS_MGR.update_trades( fill, conversion_func=_convert_quantrocket_fill )

def create_directory(directory_path):
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

def dump_intraday_prices(data, filepath):
    df = pandas.DataFrame(columns=['Date','Open','High','Low','Close'], data=data)
    try:
        df.to_csv(filepath)
    except:
        logger.error(f"couldn't write intraday data: {filepath}")
        raise RuntimeError(f"couldn't write intraday data: {filepath}")


def main(strategy_id, universe):

    global POS_MGR
    global ANCHOR_ADJUST 

    set_fixed = False
    ANCHOR_ADJUST = -1.50 
    OPEN_TIME = "22:50"
    CLOSE_TIME = "23:57"
    EOD_TIME = "23:55"
    TEST_STOPPER = "23:15"

    ## set fixed price generation from simulator
    ## otherwise run standard price stream simulator
    if set_fixed:
        p_start, p_end = 100.00, 99.00
        TESTER.set_first_last_prices(starting_price=p_start, ending_price=p_end)

    logger.info(f'starting strategy.')

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
    logger.info(f'{symbol} current position = {current_pos}')

    data = load_historical_data(symbol)

    logger.info(f'calculating trading metrics.')
    fire_entry, stdv = calc_metrics(data)
    logger.info(f'trading metrics calculated.')

    logger.info(f'trading loop initiated.')

    ## trading operations schedule
    at_open = TripWire(time_from_str(OPEN_TIME))
    at_close = TripWire(time_from_str(CLOSE_TIME))
    at_end_of_day = TripWire(time_from_str(EOD_TIME))
    fetch_intra_prices = TripWire(time_from_str(OPEN_TIME), interval_reset=60, stop_at=time_from_str(EOD_TIME))  

    intra_prices = list()


    test_stop = TripWire(time_from_str(TEST_STOPPER))
    while True:
        
        with fetch_intra_prices as fetch_intra:
            if fetch_intra:
               intra_prices.append( fetch_prices(symbol) )

        with at_open as opening:
            if opening:

                if current_pos == 0:
                    trade_amt = calc_trade_amount(symbol, POS_MGR.trade_capital)
                    if fire_entry and trade_amt > 0:
                        logger.info(f'entry triggered.')

                        open_price = get_current_price(position_node.name)

                        logger.info(f'opening price: {open_price}')
                        order_info = create_order(TradeSide.BUY, symbol, trade_amt, order_notes=strategy_id)
                        POS_MGR.register_order(order_info)
                    elif fire_entry:
                        logger.warning('entry triggered but trade_amt == 0!')
                else:
                    logger.info(f'no trade: working open position: {symbol} {current_pos}')


        with at_close as closing:
            if closing:

                position_node = POS_MGR.get_position(symbol)
                fire_exit, current_pos = check_exit(position_node, stdv)
                if fire_exit: 
                    order_info = create_order(TradeSide.SELL, symbol, current_pos, order_notes=strategy_id)
                    POS_MGR.register_order(order_info)

        check_for_fills()

        with at_end_of_day as end_of_day:
            if end_of_day:
                today = datetime.today().strftime("%Y%m%d")
                create_directory(f'{INTRA_PRICES_DIRECTORY}/intraday_data/{strategy_id}/')
                intra_file = f'{INTRA_PRICES_DIRECTORY}/intraday_data/{strategy_id}/{symbol}.{today}.csv'
                dump_intraday_prices(intra_prices, intra_file) 
                logger.info('end of day completed.')
                break

        with test_stop as stopper:
            if stopper:
                today = datetime.today().strftime("%Y%m%d")
                create_directory(f'{INTRA_PRICES_DIRECTORY}/intraday_data/{strategy_id}/')
                intra_file = f'{INTRA_PRICES_DIRECTORY}/intraday_data/{strategy_id}/{symbol}.{today}.csv'
                dump_intraday_prices(intra_prices, intra_file) 
                logger.info('end of day completed.')
                break

        time.sleep(1)


if __name__ == "__main__":
    main(strategy_id="Strategy2", universe=["SPY"])
    #main(u.strategy_id, universe=u.universe)

