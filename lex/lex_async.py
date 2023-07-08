import schedutils
from datetime import datetime
from quantrocket.blotter import order_statuses, OrderStatuses
from quantrocket.realtime import collect_market_data
import asyncio
from posmgr import PosMgr

# Connect to QuantRocket
# Make sure you have a running QuantRocket deployment
# and have configured the necessary credentials

# Set the account
account = "YOUR_ACCOUNT_NAME"


START_TIME = "09:25"
OPEN_TIME = "09:30"
EXIT_TIME = "15:55"
EOD_TIME = "16:30"

def time_until(date_string):
    now = datetime.now()
    return schedutils.seconds_until(now, date_string) 

def load_historical_data():
    ## load yahoo OHLC data

def place_entry(data):
    ## load in calendar
    ## load in MondayAnchor 
    ## return True False to trade

def place_exit(current_price, entry_price, duration):
    ## load in calendar
    ## load in MondayAnchor 
    ## return True False to trade

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


def get_current_price():
    ## get current realtime price

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

    load_current_positions(stratefgy_id, universe) 

    data = load_historical_data()
    
    start_time, secs_until_start = time_until(START_TIME)
    await asyncio.sleep(secs_until_start)

    if current_pos == 0 and place_entry(data):
        asyncio.create_task(handle_trade_fills)
        open_time, secs_until_open = time_until(OPEN_TIME)
        await asyncio.sleep(secs_until_open)
        entry_tkt = create_order(TradeSide.BUY, symbol, trade_amt)

    exit_time, secs_until_exit = time_until(EXIT_TIME)
    await asyncio.sleep(secs_until_exit)

    current_price = get_current_price()
    if current_pos > 0 and place_exit(current_price, entry_price, duration)
        asyncio.create_task(handle_trade_fills)
        exit_tkt = create_order(TradeSide.SELL, symbol, current_pos)

    eod_time, secs_until_eod = time_until(EOD_TIME)
    await asyncio.sleep(secs_until_eod)


if __name__ == "__main__":
    asyncio.run(main(u.strategy_id, universe=universe))

    
