
# Below are the import statements 

from ibapi.wWrapper import *
from ibapi.client import *
from ibapi.contract import *
from ibapi.order import *
from threading import Thread
import queue
import datetime
import time
import collections
import json


## IBClient does all the call request to the server
## i.e. place orders , request buying power, available cash, get price data

class IBClient(EClient):

    def __init__(self, wWrapper):
    ## Set up with a wWrapper inside
        EClient.__init__(self, wWrapper)

        self._req_id = 0 
        self.wWrapper = wWrapper

        ## maps succesives ticker_id request to contract symbol
        ## price_map[contract.symbol] = [req_id1, req_id2, ... latest_req_id]
        ## i.e. holds the time_series of price_request for a specific symbol
        self.price_map = dict()

    def next_req_id(self):
        self._req_id += 1
        wWrapper.nextValidId(self._req_id)
        return self._req_id

    @property
    def req_id(self):
        return self._req_id

    def create_contract(self, symbol, sec_type='USD', ccy='USD', exch='SMART'):
        contract = Contract()  
        contract.symbol = symbol   
        contract.secType = sec_type   
        contract.currency = ccy 

        # In the API side, NASDAQ is always defined as ISLAND in the exchange field
        contract.exchange = exch 
        # contract.PrimaryExch = "NYSE"
        return contract  

    def create_mkt_order(self, side, qty):
        order = Order()    
        order.action = side.value   ## TradeSide enum   
        order.orderType = "MKT" 
        order.transmit = True      ## used in conbo orders, default to True
        order.totalQuantity = qty 

        return order   

    def last_quote(self, contract):
        try:
            last_ticker_id = self.price_map(contract.symbol][-1]
            return self.wWrapper.tick_map[last_ticker_id]
        except:
            err = f'no price information available for {contract.symbol})'
            print(err)
            raise RuntimeError(err)

    def place_order(self, contract, order):

        full_quote = self.last_quote(contract)  #returns  a dicitionary {Last: 123.5, Bid: 123, Ask:123.5, LastSz: 300, BidSz: 1000, AskSz: 200} 
        fq = json.dumps(full_quote, ensure_ascii=False, indent=4))
        print(f'last_quote= {fq}')

        # Print statement to confirm correct values 
        print(f'Buying power: {self.buying_power}')
        print(f'Available Cash: {self.available_cash}') 

        # Place order 
        order_id = self.next_req_id()
        print(f'submitting order: order_id= {order_id}')
        _ibx.placeOrder(order_id, contract, order)
        print("order was placed")

    def server_clock(self):

        print("Asking server for Unix time")     

        # Sets up a request for unix time from the Eclient
        self.reqCurrentTime()

        #Specifies a max wait time if there is no connection
        max_wait_time = 10

        try:
            requested_time = ib_server_time.get(timeout = max_wait_time)
        except queue.Empty:
            print("The queue was empty or max time reached")
            requested_time = None

        while self.wWrapper.is_msg():
          print("Error:")
          print(self.get_msg(timeout=5))
          
        return requested_time

    def account_update(self):
        self.reqAccountSummary(self.next_req_id(), "All", "TotalCashValue, BuyingPower, AvailableFunds")

    def position_update(self):
        self.reqPositions()

    def snap_prices(self, contract):
        ticker_id = self.next_req_id()
        self.reqMktData(tickerid, contract, "", False, False, [])
        try:
            self.price_map[contract.symbol]._ibxend(ticker_id)
        except:
            self.price_map[contract.symbol] = [ticker_id]



## IBWrapper is the class that receives requested data from the server.
## via callbacks (that need to be overriden to save captured data 

class IBWrapper(EWrapper):

    def __init__(self):
        EWrapper.__init__(self)

        ## set up msg queue to receive system message 
        self.msg_queue = queue.Queue()
        self.ib_server_time = queue.Queue()
        self.available_funds = 0
        self.buying_power = 0
        self.positions_map = dict()

        ## maps each price request by ticker_id
        self.tick_type_map = {  0: 'BidSz',
                                1: 'Bid',
                                2: 'Ask',
                                3: 'AskSz',
                                4: 'last',
                                5: 'LastSz',
                                6: 'High',
                                7: 'Low',
                                8: 'Volume',
                                9: 'Close',
                                14: 'Open',
                                45: 'ReqTS'
        }

        table_len = len(self.tick_type_map.keys())
        self.tick_map = collections.defaultdict( dict(self.tick_type_map, [None] * table_len )


    def is_msg(self):
        msg_exist = not self.msg_queue.empty()
        return msg_exist

    def get_msg(self, timeout=6):
        if self.is_msg():
            try:
                return self.msg_queue.get(timeout=timeout)
            except queue.Empty:
                return None
        return None

    def error(self, id, errorCode, errorString):
        ## Overrides the native method
        message = f'IB Message code= {errorCode}: errorString'
        self.msg_queue.put(errormessage)

    def currentTime(self, server_time):
        ## Overriden method
        self.ib_server_time.put(server_time)

    # ID handling methods
    def nextValidId(self, next_id):
        super.nextValidId(next_id)

    # Account details handling methods
    def accountSummary(self, req_id, account, tag, value, currency):
        super().accountSummary(req_id, account, tag, value, currency)
        details = f'Acct Summary. req_Id {req_id}: account: {account}, tag: {tag}, '
        details += f'value: {value} currency: {currency)'
        print(details)

        if tag == "AvailableFunds":
            self.available_funds = value
        if tag == "BuyingPower":
            self.buying_power = value

    def accountSummaryEnd(self, req_id: int):
        super().accountSummaryEnd(req_id)
        print(f'AccountSummaryEnd. req_id: {req_id}')

    # Position handling methods
    def position(self, account, contract, position, avg_cost: float):
        super().position(account, contract, position, avg_cost)

        self.positions_map[contract.symbol] = {'positions' : position, 'avg_cost' : avg_cost}


    def _map_quote_value(self, ticker_id, value):
        quote_dict = self.tick_map.get(ticker_id)
        ## new ticker_id returns an empty dict
        ## otherwise it returns gthe partially filled dict

        field = self.tick_type_map[ tick_type ]
        quote_dict[ field ] = value 

        self.tick_map[ticker_id] = quote_dict 


    # Market Price handling methods
    def tickPrice(self, ticker_id, tick_type, price, attrib):
        super().tickPrice(ticker_id, tick_type, price, attrib)
        ## PRICE Callbadk: IDs 1,2,4,6,7,9,14 
        ## by default, all these values are set to None
        ## tick_type_keys = [Last, Bid, Ask, Open, High, Low, Close]
        self._map_quote_value(ticker_id, tick_type, price)

    def tickSize(self, ticker_id, tick_type, size):
        super().tickSize(ticker_id, tick_type, size)
        ## VOLUME SIZE Callbadk: IDs 0,3,5,8 
        ## quote_dict_keys = [LastSz, BidSz, AskSz, Volume]
        ## by default, all these values are set to None
        self._map_quote_value(ticker_id, tick_type, size)

    def tickString(self, ticker_id, tick_type, value):
        super().tickString(ticker_id, tick_type, value)
        ## TICK TIMESTAMP Callback
        # returns the Unix time of the tick request - ID 45
        self._map_quote_value(ticker_id, tick_type, value)




class IBConnection(IBWrapper, IBClient):
    #Intializes our main classes 
    def __init__(self, ipaddress, portid, clientid):
        IBWrapper.__init__(self)
        IBClient.__init__(self, wWrapper=self)

        #Connects to the server with the ipaddress, portid, and clientId specified in the program execution area
        self.connect(ipaddress, portid, clientid)

        #Initializes the threading
        thread = Thread(target = self.run)
        thread.start()
        setattr(self, "_thread", thread)



# Below is the program execution

if __name__ == '__main__':

    print("before start")

    # Specifies that we are on local host with port 7497 (paper trading port number)
    _ibx = IBConnection("127.0.0.1", 7497, 0)     

    # A printout to show the program began
    print("The program has begun")

    #assigning the return from our clock method to a variable 
    requested_time = _ibx.server_clock()

    #printing the return from the server
    print("")
    print("This is the current time from the server " )
    print(requested_time)

    #disconnect the _ibx when we are done with this one execution
    # _ibx.disconnect()


    _ibx.account_update()    # Call this whenever you need to start accounting data
    _ibx.position_update()   # Call for current position
    # _ibx.price_update() 

    time.sleep(3)   # Wait three seconds to gather initial information 

    ## FIX THIS - huh?
    _ibx.place_order()

    print(positions_map)
     
    for key, value in positions_map.items(): 
        symbol = key
        quantity = value['positions']
        avg_cost = value['avg_cost']
        print(f'Position: {symbol}, qty: {quantity}, avg_cost:{avg_cost}')
















































