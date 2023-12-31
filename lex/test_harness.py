import pandas
import uuid
import json
import os
from datetime import datetime

from posmgr import OrderType
from price_simulator import SimulatedPriceGenerator, FirstLastPriceGenerator
import price_scraper

import logging
# Create a logger specific to __main__ module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
FORMAT = "%(asctime)s: %(levelname)8s [%(module)15s:%(lineno)3d - %(funcName)20s ] %(message)s"
#FORMAT = "%(asctime)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s"
formatter = logging.Formatter(FORMAT, datefmt='%a %Y-%m-%d %H:%M:%S')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


order_queue = list()
override_price_skew = 0
override_price = None
PRICE_MGR = SimulatedPriceGenerator(100.0, 0.50, 0.20)

YAHOO_DATA_DIRECTORY = os.environ.get('YAHOO_DATA_DIRECTORY', '/home/jcarter/work/trading/data/')

## reset price generator to post a first price and last price 
## as a price stream: ie  first_price, last_price, last_price...
def set_first_last_prices(starting_price, ending_price):
    global PRICE_MGR
    PRICE_MGR = FirstLastPriceGenerator(starting_price, ending_price)

## force yesterday's close to be above/below the current anchor
## use adjust_close to tweak the close relative to the current anchor
def alter_data_to_anchor(stock_df, adjust_close=0):
    #global override_price 

    from indicators import MondayAnchor
    
    anchor = MondayAnchor(50)
    gg = stock_df[-60:]

    last_index = None
    for i in range(gg.shape[0]):
        idate = gg.index[i]
        stock_bar = gg.loc[idate]
        cur_dt = datetime.strptime(idate,"%Y-%m-%d").date()
        anchor.push((cur_dt, stock_bar))
        last_index = idate

    anchor_bar, _ = anchor.valueAt(0)
    #override_price = anchor_bar['Low'] + adjust_close
    close_override = anchor_bar['Low'] + adjust_close
    stock_df.at[last_index,'Close'] = close_override

    logger.info(f'anchor_bar = {anchor_bar}, override_price = {override_price}')

    return stock_df 


def generate_ohlc():
    global PRICE_MGR

    ohlc = PRICE_MGR.generate_ohlc()
    logger.info(f'ohlc_bar: {ohlc}')
    return ohlc 

def get_test_price():
    global override_price
    global override_price_skew
    global PRICE_MGR 

    if override_price:
        return override_price + override_price_skew

    if PRICE_MGR.has_ohlc:
        return PRICE_MGR.current_ohlc.close
    else:
        ohlc = generate_ohlc()
        return ohlc.close

"""
prices = get_prices([symbol], ["Bid", "Ask"])
bid_price = prices.loc[symbol, "Bid"]
ask_price = prices.loc[symbol, "Ask"]
override_price_skew = a testing parameter that allows me to control the next 'print' relative to the last get_prices request
"""

def get_prices_OLD(symbol_list, fields):

    symbol = symbol_list[0]

    logger.info(f'fetching prices: {override_price}, skew = {override_price_skew}')
    test_price = get_test_price() 
    logger.info(f'new override_price = {override_price}')
    bid, ask = test_price - 0.02, test_price
    logger.info(f'bid: {bid}, ask: {ask}')
    df = pandas.DataFrame(columns=['symbol','Bid','Ask'],data=[[symbol, bid, ask]])
    df.set_index('symbol', inplace=True)

    return df


def get_prices_NEW(symbol_list, fields):

    symbol = symbol_list[0]
    bid, ask = price_scraper.get_bid_ask(symbol)
    logger.info(f'bid: {bid}, ask: {ask}')
    df = pandas.DataFrame(columns=['symbol','Bid','Ask'],data=[[symbol, bid, ask]])
    df.set_index('symbol', inplace=True)

    return df

def get_prices(symbol_list, fields):
    return get_prices_OLD(symbol_list, fields)


def get_current_price(symbol):
    prices = get_prices([symbol], ['Bid', 'Ask'])
    bid_price = prices.loc[symbol, "Bid"]
    ask_price = prices.loc[symbol, "Ask"]
    #return 0.5 * (bid_price + ask_price)
    return ask_price


#order_id = place_order(account, quantity, symbol, action, order_type)
def place_order(account, quantity, symbol, action, order_type):
    global order_queue
    global override_price

    # Generate a unique order ID with timestamp
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    unique_id = "ord_id-" + str(uuid.uuid4())

    order = dict()
    order = {
        "account": account,
        "symbol": symbol,
        "quantity": quantity,
        "action": action,
        "order_type": order_type,
        "order_id": unique_id,
        "timestamp": timestamp,
        "price": get_test_price(),
        #"price": get_current_price(symbol),
        "trade_id": None 
    }

    logger.info(f'order submitted: order_id = {unique_id}')
    logger.info(json.dumps(order, ensure_ascii=False, indent =4 ))
    order_queue.append(order)

    return unique_id


## creates and submits order
## order_notes is a field to hold any info that many help in auditting trades
def create_order(side, symbol, amount, order_type=OrderType.MKT, order_notes=None):

    order = {
        "account": 'TEST_ACCOUNT',
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
    order_id = place_order(**order)
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


#filled_orders = download_executions(start_date, end_date, accounts=IB_ACCOUNT_NAME)
def download_executions(start_date, end_date, accounts=None):
    global order_queue
    
    rq = list()
    for order in order_queue:
        exec_id = "exec_id-" + str(uuid.uuid4())
        logger.info(f"filled order_id: {order['order_id']}, exec_id= {exec_id}")
        order['trade_id'] = exec_id 
        rq.append(order)

    order_queue = []
    return rq


