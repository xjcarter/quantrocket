import test_harness
from indicators import MondayAnchor, StDev
from datetime import datetime
import time 

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
IB_ACCOUNT_NAME = 'my_account'

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

    FIX THIS: you will have to adjust _convert_quantrocket_order accordingly
    """

    ## map quantrocket order fill
    def _convert_quantrocket_trade(fill):
        trd = Trade( fill['trade_id'] )
        trd.order_id = fill['order_id']
        trd.asset = fill["symbol"]
        trd.exchange = fill.get("Exchange")
        trd.side = TradeSide.SELL if fill["action"] == 'SELL' else TradeSide.BUY
        trd.units = abs(fill["quantity"])
        trd.price = fill["price"]
        #trd.commission = fill["commission"]
        trd.timestamp = fill.get("executionTime")
        return trd

    counter = 0
    FETCH_WINDOW = 2   ## 30min
    start_date = end_date = datetime.today().date()

    while counter < FETCH_WINDOW:

        #filled_orders = download_executions(start_date, end_date, accounts=IB_ACCOUNT_NAME)
        filled_orders = test_harness.download_executions(start_date, end_date, accounts=IB_ACCOUNT_NAME)

        for fill in filled_orders:
            logger.info(f'Processing trade_id: {fill["trade_id"]}')
            POS_MGR.update_trades( fill, conversion_func=_convert_quantrocket_trade )

        counter += 1
        # Sleep for 1 second before checking for new filled orders
        time.sleep(1)


POS_MGR.initialize('Strategy1', ['SPY'])
test_harness.override_price = 123.45
order_info = test_harness.create_order(TradeSide.BUY, 87, 'SPY')
POS_MGR.register_order(order_info)
handle_trade_fills()

