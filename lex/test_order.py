import test_harness
from indicators import MondayAnchor, StDev
from datetime import datetime
import uuid
import json

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s',
                    datefmt='%a %Y-%m-%d %H:%M:%S')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

from posmgr import PosMgr, TradeSide, Trade

POS_MGR = PosMgr()

IB_ACCOUNT_NAME = 'YOUR_ACCOUNT_NAME'


def create_order(side, amount, symbol, strategy_id):

    def _new_order_id(tag=None):
        # Generate a unique order ID with timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())
        if tag is not None:
            return f"{tag}-{unique_id}-{timestamp}"
        else:
            return f"{unique_id}-{timestamp}"

    # Create a market order to buy 100 shares of SPY

    test_new_order_id = _new_order_id()
    tag_new_order_id = _new_order_id('tiger')

    order = {
        "account": strategy_id,
        "symbol": symbol,
        "quantity": amount, 
        "action": TradeSide.BUY.value,
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


def handle_trade_fills():

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
    #FETCH_WINDOW = 1800   ## 30min
    FETCH_WINDOW = 2
    start_date = end_date = datetime.today().date()

    while counter < FETCH_WINDOW:

        #filled_orders = download_executions(start_date, end_date, accounts=IB_ACCOUNT_NAME)
        filled_orders = test_harness.download_executions(start_date, end_date, accounts=[IB_ACCOUNT_NAME])

        for order in filled_orders:
            logger.info(f'Processing order_id: {order["OrderRef"]}')
            POS_MGR.update_trades( order, conversion_func=_convert_quantrocket_order )

        counter += 1
        # Sleep for 1 second before checking for new filled orders
        # await asyncio.sleep(1)


POS_MGR.initialize('Strategy1', ['SPY'])

test_harness.ref_price = 446.04 
order_id = create_order(TradeSide.BUY, 227, 'SPY', 'Strategy1')
print(order_id)
handle_trade_fills()
