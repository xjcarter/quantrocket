import pandas
import uuid
from random import randint

order_queue = list()
bids = [ -0.03, -0.03, -0.02, -0.02, 0, 0, 0.02, 0.04, -0.02, 0,02, 0.03, 0, 0, 0.03, 0.01, 0.02, 0.03 ]
asks = [ x + 0.01 for x in bids ]
ref_close = None

YAHOO_DATA_DIRECTORY = os.environment.get('YAHOO_DATA_DIRECTORY', '/home/jcarter/work/trading/data/')

## force yesterday's close to be above/below the current anchor
## use adjust_close to tweak the close relative to the current anchor
def alter_data_to_anchor(stock_df, adjust_close=0):
    global ref_close 

    from indicators import MondayAnchor
    
    anchor = MondayAnchor(50)
    gg = stock_df[60:]

    last_index = None
    for i in range(gg.shape[0]):
        idate = gg.index[i]
        stock_bar = gg.loc[idate]
        cur_dt = datetime.strptime(idate,"%Y-%m-%d").date()
        anchor.push((cur_dt, stock_bar))
        last_index = idate

    anchor_bar = anchor.valueAt(1)
    ref_close = anchor_bar['Close'] + adjust_close
    stock_df.at[last_index,'Close'] = ref_close

    return stock_df 


def fill_price():
    global bids 
    global asks
    global ref_close

    i = randint(0,len(bids))
    bid, ask = bids[i], asks[i]
    ref_close = 0.5 * (2*ref_close +bid + ask )
    return ref_close


#order_id = place_order(account, symbol, quantity, action, order_type)
def place_order(account, symbol, quantity, action, order_type):
    global order_queue

    # Generate a unique order ID with timestamp
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    unique_id = str(uuid.uuid4())

    order = dict()
    order = {
        "account": account,
        "symbol": symbol,
        "quantity": quantity,
        "action": action,
        "order_type": order_type
        "OrderRef": unique_id
        "timestamp": timestamp
        "price": fill_price() 
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
    global bids
    global asks
    global ref_close 

    symbol = symbol_list[0]
    i = randint(0,len(bids))
    bid, ask = ref_close + bids[i], ref_close + asks[i]
    df = pandas.DataFrame(columns=['symbol','Bid','Ask'],data=[symbol, bid, ask])
    df.set_index('symbol', inplace=True)
    return df

