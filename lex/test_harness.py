import pandas
import uuid

order_queue = list()

#order_id = place_order(account, symbol, quantity, action, order_type)
def place_order(account, symbol, quantity, action, order_type):
    global order_queue

    # Generate a unique order ID with timestamp
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    unique_id = str(uuid.uuid4())

    order = {
        "account": account,
        "symbol": symbol,
        "quantity": quantity,
        "action": action,
        "order_type": order_type
        "OrderRef": unique_id
        "timestamp": timestamp
    }

    order_queue.append(order)
    return unique_id


#filled_orders = download_executions(start_date, end_date, accounts=IB_ACCOUNT_NAME)
def download_executions(start_date, end_date, account):
    global order_queue

    rq = [ x for x in order_queue ]
    order_queue = []
    return rq


"""
prices = get_prices([symbol], ["Bid", "Ask"])
bid_price = prices.loc[symbol, "Bid"]
ask_price = prices.loc[symbol, "Ask"]
"""
def get_prices(symbol_list, fields):
    from random import randint
    c = []
    for symbol in symbol_list:
        bid = randint(0,100)
        ask = randint(0,10)+bid
        c.append([symbol,bid,ask])
    df = pandas.DataFrame(columns=['symbol','Bid','Ask'],data=c)
    df.set_index('symbol', inplace=True)
    return df

