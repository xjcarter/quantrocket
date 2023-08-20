
# Below are the import statements 

from ibapi.wrapper import *
from ibapi.client import *
from ibapi.contract import *
from ibapi.order import *
from threading import Thread
import queue
from datetime import datetime
import time
import collections
import json

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


## IBWrapper is the class that receives requested data from the server.
## via callbacks (that need to be overriden to save captured data 

class IBWrapper(EWrapper):

    def __init__(self):
        EWrapper.__init__(self)

        ## set up msg queue to receive system message 
        self.msg_queue = queue.Queue()
        self.ib_server_time = queue.Queue()
        self.positions_map = dict()
        self.account_info = dict()
       
        ## monitors the response duration
        ## btwn client call and callback response
        self.response_check = dict()

        ## maps each price request by ticker_id
        self.tick_field_map = {  0: 'BidSz',
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
                                45: 'Server_TS'
        }

        _default_quote_map = lambda: dict( zip(self.tick_field_map.values(), [None] * len(self.tick_field_map)) )

        self.tick_map =  collections.defaultdict(_default_quote_map)

    # ID handling methods
    def nextValidId(self, next_id):
        super.nextValidId(next_id)

    def _timestamp(self):
        return datetime.now().strftime("%Y%m%d-%H:%M:%S")

    def has_msg(self):
        msg_exist = not self.msg_queue.empty()
        return msg_exist

    def get_msg(self, timeout=6):
        if self.has_msg():
            try:
                return self.msg_queue.get(timeout=timeout)
            except queue.Empty:
                return None
        return None

    def error(self, id, errorCode, errorString):
        ## Overrides the native method
        message = f'IB Message code= {errorCode}: errorString'
        self.msg_queue.put(message)

    def currentTime(self, server_time):
        ## Overriden method
        self.ib_server_time.put(server_time)


    # Account details handling methods
    def accountSummary(self, req_id, account, tag, value, currency):
        super().accountSummary(req_id, account, tag, value, currency)
        try:
            ## track response time of callback
            tag = 'accountSummary'
            dur = datetime.now() - self.response_check[tag]
            logger.debug(f'{tag} callback response: {dur.total_seconds()}') 
        except:
            pass

        details = f'Acct Summary. req_Id {req_id}: account: {account}, tag: {tag},'
        details += f' value: {value} currency: {currency)'
        logger.info(details)

        self.account_info[tag] = value


    def accountSummaryEnd(self, req_id: int):
        super().accountSummaryEnd(req_id)
        logger.info(f'AccountSummaryEnd. req_id: {req_id}')

    # Position handling methods
    def position(self, account, contract, position, avg_cost):
        super().position(account, contract, position, avg_cost)
        super().accountSummary(req_id, account, tag, value, currency)
        try:
            tag = 'position'
            dur = datetime.now() - self.response_check[tag]
            logger.debug(f'{tag} callback response: {dur.total_seconds()}') 
        except:
            pass

        self.positions_map[contract.symbol] = {'position': position, 'avg_cost': avg_cost}
        pp = json.dumps(self.positions_map, ensure_ascii=False, indent=4)
        logger.info('IB positions: {pp}')


    def _map_quote_value(self, ticker_id, tick_type, value):

        ## awesome defaultdict functionality to write fields as they come in!
        ## defaultdict is threadsafe and creates new quote_dict (see __init__)
        ## when in encounters a new key!
        field = self.tick_field_map.get(tick_type, None)
        if field is not None:
            self.tick_map[ticker_id][ field ] = value
            ## this will be updated until the quote dict is completed
            ## give as good marker of 'fill time' btwn Server_TS and Client_TS
            self.tick_map[ticker_id]['Client_TS'] = self._timestamp()

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


## IBClient does all the call request to the server
## i.e. place orders , request buying power, available cash, get price data

class IBClient(EClient):

    def __init__(self, wrapper):
    ## Set up with a wrapper inside
        EClient.__init__(self, wrapper)

        self._req_id = 0 
        self.wrapper = wrapper

        ## maps succesive ticker_id requests to contract symbol that requested the quote
        ## price_map[contract.symbol] = [req_id1, req_id2, ... latest_req_id]
        ## i.e. holds the time_series of price_request for a specific symbol
        self.price_map = collections.defaultdict(list())

    def next_req_id(self):
        self._req_id += 1
        self.wrapper.nextValidId(self._req_id)
        return self._req_id

    @property
    def req_id(self):
        return self._req_id

    def create_contract(self, symbol, sec_type='STK', ccy='USD', exch='SMART'):
        contract = Contract()  
        contract.symbol = symbol   
        contract.secType = sec_type   
        contract.currency = ccy 

        # In the API side, NASDAQ is always defined as ISLAND in the exchange field
        contract.exchange = exch 
        # contract.PrimaryExch = "NYSE"
        return contract  

    def mkt_order(self, side, qty):
        order = Order()    
        order.action = side.value   ## TradeSide enum   
        order.orderType = "MKT" 
        order.transmit = True      ## used in conbo orders, default to True
        order.totalQuantity = qty 

        return order   

    def place_order(self, contract, order):
        # Place order 
        order_id = self.next_req_id()
        logger.info(f'submitting order: order_id= {order_id}')
        ibx.placeOrder(order_id, contract, order)

        deets = dict(contract.__dict__)
        deets.update(order.__dict__)
        dd = json.dumps(deets, ensure_ascii=False, indent=4)
        logger.info("order ({order_id}) placed: {dd}")

        return order_id


    def last_quote(self, contract):
        ## returns a dict of quote attributes {'Bid':123, 'Ask':123.5, ... }
        try:
            symbol = contract.symbol
            last_ticker_id = self.price_map[symbol][-1]
            full_quote = self.wrapper.tick_map[last_ticker_id]
            ## wait until a full quote
            while None not in full_quote.values():
                full_quote = self.wrapper.tick_map[last_ticker_id]
                time.sleep(0.2)
            fq = json.dumps(full_quote, ensure_ascii=False, indent=4)
            logger.info(f'last_quote= {fq}')
            return full_quote 
        except:
            err = f'no price information available for {contract.symbol}'
            logger.error(err)
            raise RuntimeError(err)

    def snap_prices(self, contract):
        ticker_id = self.next_req_id()
        self.reqMktData(ticker_id, contract, "", False, False, [])

        ## defaultdict!  creates a new list on a new key.
        self.price_map[contract.symbol].append(ticker_id)



    def ping_server(self):

        logger.info("Asking server for Unix time")     

        self.reqCurrentTime()

        #Specifies a max wait time if there is no connection
        max_wait_time = 10

        try:
            begin = datetime.now()
            requested_time = self.wrapper.ib_server_time.get(timeout = max_wait_time)
            end = datetime.now()
            logger.info(f'current server time: {requested_time}')
            dur = end - begin
            logger.info(f'response time: {dur.total_seconds()} seconds')
        except queue.Empty:
            logger.error("response was empty or max time reached")
            requested_time = None

        while self.wrapper.has_msg():
          logger.info(self.get_msg(timeout=5))
          

    def account_update(self):
        logger.info('requested account update')
        self.wrapper.response_check['accountSummary'] = datetime.now()
        self.reqAccountSummary(self.next_req_id(), "All", "TotalCashValue, BuyingPower, AvailableFunds")

    def position_update(self):
        logger.info('requested position update')
        self.wrapper.response_check['position'] = datetime.now()
        self.reqPositions()



class IBConnection(IBWrapper, IBClient):
    #Intializes our main classes 
    def __init__(self, ipaddress, portid, clientid):
        IBWrapper.__init__(self)
        IBClient.__init__(self, wrapper=self)

        #Connects to the server with the ipaddress, portid, and clientId specified in the program execution area
        self.connect(ipaddress, portid, clientid)

        #Initializes the threading
        self._thread = Thread(target = self.run)
        self._thread.start()



if __name__ == '__main__':

    logger.info("Connecting to IB")

    # Specifies that we are on local host with port 7497 (paper trading port number)
    ibx = IBConnection("127.0.0.1", 7497, 0)     

    ibx.ping_server()

    ibx.account_update()    # Call this whenever you need to start accounting data
    ibx.position_update()   # Call for current position
    # ibx.price_update() 

    time.sleep(3)   # Wait three seconds to gather initial information 

    aapl = ibx.create_contract('AAPL')
    ibx.place_order(aapl, mkt_order(TradeSide.BUY, 100)

    ibx.snap_prices(aapl)

    time.sleep(3)
    
    ibx.last_quote(aapl)
    ibx.position_update()   # Call for current position

    time.sleep(3)

    #disconnect the ibx when we are done with this one execution
    # ibx.disconnect()
