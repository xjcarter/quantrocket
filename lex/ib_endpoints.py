import requests
import json
import urllib3
import os
import re
from clockutils import timestamp_string, unix_time_to_string 

## suppress non-secure connection warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def _xns(number_string):
    if isinstance(number_string, (int, float)):
        return number_string

    ## _xns = extract_number_from_string
    ## Define a regular expression pattern to match numbers with optional '$' and commas
    pattern = r'\$?[\d,]+(?:\.\d+)?'
    numbers = re.findall(pattern, number_string)

    if numbers:
        # Remove commas and dollar signs, then convert to a float
        cleaned_number = float(numbers[0].replace(',', '').replace('$', ''))
        return cleaned_number
    else:
        # Return None if no numbers are found in the string
        return None


def _check_fail(req, msg):
    if req.status_code == 200:
        ## OK response
        return

    if req.status_code == 400:
        err_msg = f'{msg}: status_code= {req.status_code}, Bad request'
        print(err_msg)
        raise RuntimeError(err_msg)
    elif req.status_code == 401:
        err_msg = f'{msg}: status_code= {req.status_code}, Unauthorized to access endpoint'
        print(err_msg)
        raise RuntimeError(err_msg)
    elif req.status_code == 404:
        err_msg = f'{msg}: status_code= {req.status_code}, endpoint Not Found'
        print(err_msg)
        raise RuntimeError(err_msg)
    else:
        err_msg = f'{msg}: status_code= {req.status_code}'
        print(err_msg)
        raise RuntimeError(err_msg)


def order_request(contract_id, order_type, side, qty, tgt_price=None, lmt_price=None):

    hostname = os.getenv('IB_WEB_HOST', 'localhost')
    account = os.getenv('IB_ACCOUNT', 'DU7631004')
    base_url = f'https://{hostname}:5000/v1/api/'
    endpoint = f'iserver/account/{account}/orders'

    base_order = {
                    "conid": contract_id,
                    "orderType": order_type,
                    "side": side,
                    "tif": "DAY",
                    "quantity": qty
                }
    
    if order_type in ['STP', 'LMT']:
        ## tgt_price drives both limit and stop orders
        if tgt_price is not None:
            base_order.update( { "price": tgt_price } )
        else:
            print('critical: order ignored. no target price given for STOP or LIMIT order!')
            return None

    if order_type == 'STOP_LIMIT':
        if all([tgt_price, lmt_price]):
            base_order.update( { "price": lmt_price, "auxPrice": tgt_price } )
        else:
            print('critical: order ignored. incomplete STOP_LIMIT order!')
            return None

    json_body = { "orders": [ base_order ] }

    order_req = requests.post(url=base_url+endpoint, verify=False, json=json_body)
    _check_fail(order_req, 'couldnt place order')
    order_json = json.dumps(order_req.json(), ensure_ascii=False, indent=4)\

    print(order_json) 

    record = order_req.json()[0]

    order_info = {
        'order_id': record.get('order_id'),
        'order_status': record.get('order_status'),
        'reply_id': record.get('id'),
        'reply_message': record.get('message')
    }

    return order_info

    """
    sample response of a SUCCESSFUL submission:
    [
        {
            "order_id": "1149239278",
            "order_status": "PreSubmitted",
            "encrypt_message": "1"
        }
    ]

    sample response of a reply request submission:
    feed the reply "id" into the order_reply() endpoint to resolve
    [
        {
            "id": "8647ed1d-862b-4c58-95ff-ae6dd6893871",
            "message": [
                "This order will most likely trigger and fill immediately.\nAre you sure you want to submit this order?"
            ],
            "isSuppressed": false,
            "messageIds": [
                "o0"
            ]
        }
    ]
    """

## answer to precautionary messages after an order placement.
def order_reply(reply_id, repeat=True):

    hostname = os.getenv('IB_WEB_HOST', 'localhost')
    base_url = f'https://{hostname}:5000/v1/api/'
    endpoint = f'iserver/reply/{reply_id}'
   
    while reply_id is not None:

        ## responding to 'are you sure?' reply
        json_body = { "confirmed": True }

        reply_req = requests.post(url=base_url+endpoint, verify=False, json=json_body)
        _check_fail(reply_req, 'order request reply')
        reply_json = json.dumps(reply_req.json(), ensure_ascii=False, indent=4)

        print(reply_json)

        record = reply_req.json()[0]

        order_info = {
            'order_id': record.get('order_id'),
            'order_status': record.get('order_status'),
            'reply_id': record.get('id'),
            'reply_message': record.get('message')
        }
        
        new_reply_id = order_info.get('reply_id')
        if repeat and new_reply_id:
            if new_reply_id != reply_id:
                reply_id = new_reply_id
            else:
                err_msg = f'error: current reply_id = new reply_id! {reply_id}'
                print(err_msg)
                raise RuntimeError(err_msg)
        else:
            break

    return order_info

    """
    look to the order_info dictionary to see if additional replies need to be sent:
    -- order reply info--
    {
        "order_id": "749645736",
        "order_status": "PreSubmitted",
        "reply_id": null,
        "reply_message": null
    }
    if repeat == True: the method will continue to resubmit until the order is accepeted.
    """


def order_status(filters=['inactive', 'cancelled', 'filled']):

    hostname = os.getenv('IB_WEB_HOST', 'localhost')
    base_url = f'https://{hostname}:5000/v1/api/'
    endpoint = f'iserver/account/orders'

    filter_codes = ['inactive', 'pending_submit', 'pre_submitted', 'submitted',
                    'filled', 'pending_cancel', 'cancelled', 'warn_state', 'sort_by_time' ]

    my_filters = []
    for f in filters:
        if f in filter_codes:
            my_filters.append(f)
        else:
            print(f'order filter: {f} not valid.')
   
    filters_string = ",".join(my_filters)
    request_url = base_url+endpoint

    ## NOTE filters param IS a capital F!
    if len(filters_string) > 0:
        request_url += f'?Filters={filters_string}'


    print(request_url)

    fill_req = requests.get(url=request_url, verify=False)
    _check_fail(fill_req, 'check fills error')
    fill_json = json.dumps(fill_req.json(), ensure_ascii=False, indent=4)
    print(fill_json)

    return fill_req.json().get('orders') 

    """
    first call will 'connect' to get order status -
    sample response:
    {
        "orders": [],
        "snapshot": false
    }

    subsequent order_status() calls will provide order status info -
    sample response:
    {
        "orders": [
            {
                "acct": "DU7631004",
                "conidex": "265598",
                "conid": 265598,
                "orderId": 1149239278,
                "cashCcy": "USD",
                "sizeAndFills": "100",
                "orderDesc": "Bought 100 Market, Day",
                "description1": "AAPL",
                "ticker": "AAPL",
                "secType": "STK",
                "listingExchange": "NASDAQ.NMS",
                "remainingQuantity": 0.0,
                "filledQuantity": 100.0,
                "companyName": "APPLE INC",
                "status": "Filled",
                "order_ccp_status": "Filled",
                "avgPrice": "176.32",
                "origOrderType": "MARKET",
                "supportsTaxOpt": "1",
                "lastExecutionTime": "230912151804",
                "orderType": "Market",
                "bgColor": "#FFFFFF",
                "fgColor": "#000000",
                "timeInForce": "CLOSE",
                "lastExecutionTime_r": 1694531884000,
                "side": "BUY"
            },
            {
                "acct": "DU7631004",
                "conidex": "265598",
                "conid": 265598,
                "orderId": 1149239268,
                "cashCcy": "USD",
                "sizeAndFills": "100",
                "orderDesc": "Bought 100 Market, Day",
                "description1": "AAPL",
                "ticker": "AAPL",
                "secType": "STK",
                "listingExchange": "NASDAQ.NMS",
                "remainingQuantity": 0.0,
                "filledQuantity": 100.0,
                "companyName": "APPLE INC",
                "status": "Filled",
                "order_ccp_status": "Filled",
                "avgPrice": "176.49",
                "origOrderType": "MARKET",
                "supportsTaxOpt": "1",
                "lastExecutionTime": "230912150834",
                "orderType": "Market",
                "bgColor": "#FFFFFF",
                "fgColor": "#000000",
                "timeInForce": "CLOSE",
                "lastExecutionTime_r": 1694531314000,
                "side": "BUY"
            }
        ],
        "snapshot": true
    }
    """


### this was a test helper function
### it replaces the order_status() call 
### inside the OrderMonitor.monitor_orders() method
TESTFILE_COUNTER = 0
def mock_order_status():
    global TESTFILE_COUNTER
    snapshot_files = ['snap_order1.txt', 'snap_order2.txt', 'snap_order3.txt']

    if TESTFILE_COUNTER < 3:
        snapfile = snapshot_files[TESTFILE_COUNTER]
        print(f'snapshot: {snapfile}')
        with open(snapfile, 'r') as f:
            orders = json.load(f)
        TESTFILE_COUNTER += 1
        return orders['orders']

    return None


class OrderMonitor(object):
    def __init__(self):
        self.last_orders = dict() 

    def _generate_fill(self, current_order):

        remaining = 'remainingQuantity'
        filled = 'filledQuantity'
        price = 'avgPrice'

        fill = dict()
        
        number_of_fills = 1
        n_order_id = current_order['orderId']
        last_order = self.last_orders.get(n_order_id) 
        if last_order is not None:
            if current_order[remaining] != 0 and last_order[remaining] == current_order[remaining]:
                ## nothing has changed 
                return None
            else:
                number_of_fills = last_order['number_of_fills'] + 1

                filled_qty = float(current_order[filled])
                last_qty = float(last_order[filled])

                if filled_qty < last_qty:
                    ## the updated total fill amount DECREASED - throw error
                    raise RuntimeError(f'filled_qty: {filled_qty} < last_qty {last_qty}')

                filled_price = float(current_order[price])
                last_price = float(last_order[price])

                ## calc partial fill amount and price
                residual = filled_qty - last_qty
                residual_price = ((filled_qty*filled_price) - (last_qty*last_price)) / residual
                fill.update({ 'qty':residual, 'price': residual_price})
        else:
            fill.update({ 'qty': float(current_order[filled]), 'price': float(current_order[price]) })

        self.last_orders[n_order_id] = current_order
        self.last_orders[n_order_id]['number_of_fills'] = number_of_fills

        ttest_order_requestms= 'lastExecutionTime_r'
        fill['order_id'] = n_order_id 
        fill['trade_id'] = f'{n_order_id}-{number_of_fills:04d}' 
        fill['ticker'] = current_order['ticker']
        fill['side'] = current_order['side']
        fill['conidex'] = current_order['conidex']
        fill[tms] = current_order[tms]

        jfill = json.dumps(fill, ensure_ascii=False, indent=4)
        print(f'processed fill: {jfill}')

        return fill


    def monitor_orders(self):

        ## call the endpoint to grab all current orders 
        orders = order_status()

        fills = list()
        for order in orders:
            status = order['status'].lower()
            ticker = order['ticker']
            n_order_id = order['orderId']
            if status == 'filled':
                fill = self._generate_fill(order)
                if fill is not None: fills.append(fill)
            elif status in ['cancelled', 'inactive']:
                print(f'warning: orderId= {n_order_id} {status}. {ticker} {order["orderDesc"]}')
            elif status == 'submitted':
                print(f'orderId= {n_order_id} {status}. {ticker} {order["orderDesc"]}')

        return fills

    """
    tested.
    sammple output from  'for fill in order_monitor.monitor_orders():: print(fill)' 
    processed fill: {
        "qty": 100.0,
        "price": "176.32",
        "order_id": 1149239278,
        "trade_id": "1149239278-0001",
        "ticker": "AAPL",
        "side": "BUY",
        "conidex": "265598",
        "lastExecutionTime_r": 1694531884000
    }
    processed fill: {
        "qty": 100.0,
        "price": "176.49",
        "order_id": 1149239268,
        "trade_id": "1149239268-0001",
        "ticker": "AAPL",
        "side": "BUY",
        "conidex": "265598",
        "lastExecutionTime_r": 1694531314000
    }
    {'qty': 100.0, 'price': '176.32', 'order_id': 1149239278, 'trade_id': '1149239278-0001', 'ticker': 'AAPL', 'side': 'BUY', 'conidex': '265598', 'lastExecutionTime_r': 1694531884000}
    {'qty': 100.0, 'price': '176.49', 'order_id': 1149239268, 'trade_id': '1149239268-0001', 'ticker': 'AAPL', 'side': 'BUY', 'conidex': '265598', 'lastExecutionTime_r': 1694531314000}
    """
                        
      
##initializes market subscription - call before snapshot
def market_connect(contract_id):
    
    hostname = os.getenv('IB_WEB_HOST', 'localhost')
    base_url = f'https://{hostname}:5000/v1/api/'
    endpoint = f'iserver/marketdata/snapshot'

    fields=f'fields=55'

    params = "&".join([f'conids={contract_id}', fields])
    request_url = "".join([base_url, endpoint, "?", params])

    md_req = requests.get(url=request_url, verify=False)
    _check_fail(md_req, 'market connect error')
    md_json = json.dumps(md_req.json(), ensure_ascii=False, indent=4)
    print(md_json)

    print(f'market connected for conid= {contract_id}')

    return True

    """
    sample response:
    [
        {
            "conidEx": "265598",
            "conid": 265598
        }
    ]
    """


def market_snapshot(contract_id):
    
    hostname = os.getenv('IB_WEB_HOST', 'localhost')
    base_url = f'https://{hostname}:5000/v1/api/'
    endpoint = f'iserver/marketdata/snapshot'

    def _v_x100(v):
        v = _xns(v)
        if v is None: return v
        return int(v) * 100
 
    def _int(v):
        v = _xns(v)
        if v is None: return v
        return int(v)

    def _float(v):
        v = _xns(v)
        if v is None: return v
        return float(v)

    field_dict = {
            'last': ('31', _float),
            'ask': ('84', _float),
            'bid': ('86', _float),
            'bid_sz': ('88', _v_x100),
            'ask_sz': ('85', _v_x100),
            'volume': ('7762', _int),
            'symbol': ('55', str),
            'conid': ('6008', str)
    }

    field_codes = [ v[0] for v in field_dict.values() ]
    values = ",".join(field_codes)
    fields=f'fields={values}'

    params = "&".join([f'conids={contract_id}', fields])
    request_url = "".join([base_url, endpoint, "?", params])

    md_req = requests.get(url=request_url, verify=False)
    _check_fail(md_req, 'market snapshot error')
    md_json = json.dumps(md_req.json(), ensure_ascii=False, indent=4)
    print(md_json)

    data_dict = md_req.json()[0]
    ## v[0] data field number, v[1] conversion func for the field
    market_data = dict([ (k, v[1](data_dict.get(v[0])) ) for k,v in field_dict.items() ])
    dd, tt = timestamp_string(split_date_and_time=True)
    market_data.update( { 'date': dd, 'time': tt } )
    
    ## tack on non 'number_tageged' fields
    for add_on in [ 'conid', '_updated' ]:
        market_data.update( { add_on: data_dict.get(add_on) } )
    ## convert unix timestamp
    unix_ts = market_data['_updated']
    if unix_ts: market_data['_updated'] = unix_time_to_string(unix_ts) 

    return market_data

    """
    sample response:
    [
        {
            "conidEx": "265598",
            "conid": 265598,
            "server_id": "q0",
            "_updated": 1694639699133,
            "6119": "q0",
            "55": "AAPL",
            "7762": "83916700",
            "85": "200",
            "84": "173.95",
            "88": "800",
            "31": "173.96",
            "86": "173.96",
            "6509": "DPB",
            "6508": "&serviceID1=122&serviceID2=123&serviceID3=203&serviceID4=775&serviceID5=204&serviceID6=206&serviceID7=108&serviceID8=109"
        }
    ]

    -- returned market_data dict:
    {
        "last": 173.96,
        "ask": 173.95,
        "bid": 173.96,
        "bid_sz": 80000,
        "ask_sz": 20000,
        "volume": 83916700,
        "symbol": "AAPL",
        "conid": 265598,
        "date": "20230913",
        "time": "17:15:00",
        "_updated": "20230913-17:14:59"
    }
    """
        
def account_summary():
    
    hostname = os.getenv('IB_WEB_HOST', 'localhost')
    account = os.getenv('IB_ACCOUNT', 'DU7631004')
    base_url = f'https://{hostname}:5000/v1/api/'
    endpoint = f'portfolio/{account}/summary'

    pos_req = requests.get(url=base_url+endpoint, verify=False)
    _check_fail(pos_req, 'account summary error')
    pos_json = json.dumps(pos_req.json(), ensure_ascii=False, indent=4)
    print(pos_json)

    return pos_req.json()

    """
    sample response:  THIS DICT IS HUGE.
    {
        "accountcode": {
            "amount": 0.0,
            "currency": null,
            "isNull": false,
            "timestamp": 1694533459000,
            "value": "DU7631004",
            "severity": 0
        },
        "accountready": {
            "amount": 0.0,
            "currency": null,
            "isNull": false,
            "timestamp": 1694533459000,
            "value": "true",
            "severity": 0
        },
        ...
    """


def current_position(contract_id):
    
    hostname = os.getenv('IB_WEB_HOST', 'localhost')
    account = os.getenv('IB_ACCOUNT', 'DU7631004')
    base_url = f'https://{hostname}:5000/v1/api/'
    endpoint = f'portfolio/{account}/position/{contract_id}'

    pos_req = requests.get(url=base_url+endpoint, verify=False)
    _check_fail(pos_req, 'current position error')
    pos_json = json.dumps(pos_req.json(), ensure_ascii=False, indent=4)
    print(pos_json)

    return pos_req.json()

    """
    sample response:
    [
        {
            "acctId": "DU7631004",
            "conid": 265598,
            "contractDesc": "AAPL",
            "position": 200.0,
            "mktPrice": 176.973999,
            "mktValue": 35394.8,
            "currency": "USD",
            "avgCost": 176.415,
            "avgPrice": 176.415,
            "realizedPnl": 0.0,
            "unrealizedPnl": 111.8,
            "exchs": null,
            "expiry": null,
            "putOrCall": null,
            "multiplier": null,
            "strike": 0.0,
            "exerciseStyle": null,
            "conExchMap": [],
            "assetClass": "STK",
            "undConid": 0,
            "model": ""
        }
    ]
    """


## takes a list of symbols and returns contract ids specific to exchange
def stock_to_contract_id(symbols_list):
    
    hostname = os.getenv('IB_WEB_HOST', 'localhost')
    base_url = f'https://{hostname}:5000/v1/api/'
    endpoint = f'trsrv/stocks'

    syms = ",".join([x.upper() for x in symbols_list])
    symbols = f'symbols={syms}'

    url = "".join([base_url, endpoint, "?", symbols])
    stk_req = requests.get(url=url, verify=False)
    _check_fail(stk_req, 'stock conid lookup error')
    stk_json = json.dumps(stk_req.json(), ensure_ascii=False, indent=4)

    print(stk_json)

    return stk_json

    """
    sample output -> stock_to_contract_id(['AAPL', 'IBM'])
    {
        "AAPL": [
            {
                "name": "APPLE INC",
                "chineseName": "&#x82F9;&#x679C;&#x516C;&#x53F8;",
                "assetClass": "STK",
                "contracts": [
                    {
                        "conid": 265598,
                        "exchange": "NASDAQ",
                        "isUS": true
                    },
                    {
                        "conid": 38708077,
                        "exchange": "MEXI",
                        "isUS": false
                    },
                    {
                        "conid": 273982664,
                        "exchange": "EBS",
                        "isUS": false
                    }
                ]
            },
            {
                "name": "LS 1X AAPL",
                "chineseName": null,
                "assetClass": "STK",
                "contracts": [
                    {
                        "conid": 493546048,
                        "exchange": "LSEETF",
                        "isUS": false
                    }
                ]
            },
            {
                "name": "APPLE INC-CDR",
                "chineseName": "&#x82F9;&#x679C;&#x516C;&#x53F8;",
                "assetClass": "STK",
                "contracts": [
                    {
                        "conid": 532640894,
                        "exchange": "AEQLIT",
                        "isUS": false
                    }
                ]
            }
        ],
        "IBM": [
            {
                "name": "INTL BUSINESS MACHINES CORP",
                "chineseName": "&#x56FD;&#x9645;&#x5546;&#x4E1A;&#x673A;&#x5668;",
                "assetClass": "STK",
                "contracts": [
                    {
                        "conid": 8314,
                        "exchange": "NYSE",
                        "isUS": true
                    },
                    {
                        "conid": 1411277,
                        "exchange": "IBIS",
                        "isUS": false
                    },
                    {
                        "conid": 38709473,
                        "exchange": "MEXI",
                        "isUS": false
                    },
                    {
                        "conid": 41645598,
                        "exchange": "LSE",
                        "isUS": false
                    }
                ]
            },
            {
                "name": "INTL BUSINESS MACHINES C-CDR",
                "chineseName": "&#x56FD;&#x9645;&#x5546;&#x4E1A;&#x673A;&#x5668;",
                "assetClass": "STK",
                "contracts": [
                    {
                        "conid": 530091934,
                        "exchange": "AEQLIT",
                        "isUS": false
                    }
                ]
            }
        ]
    }
    """

def status():
    
    hostname = os.getenv('IB_WEB_HOST', 'localhost')
    base_url = f'https://{hostname}:5000/v1/api/'
    endpoint = f'iserver/auth/status'

    svr_req = requests.get(url=base_url+endpoint, verify=False)
    _check_fail(svr_req, 'auth status error')
    svr_json = json.dumps(svr_req.json(), ensure_ascii=False, indent=4)

    print(svr_json)

    """
    sample response:
    {
        "authenticated": true,
        "competing": false,
        "connected": true,
        "message": "",
        "MAC": "F4:03:43:DC:90:80",
        "serverInfo": {
            "serverName": "JifN10044",
            "serverVersion": "Build 10.25.0a, Aug 29, 2023 4:29:57 PM"
        },
        "fail": ""
    }
    """


def tickle():
    
    hostname = os.getenv('IB_WEB_HOST', 'localhost')
    base_url = f'https://{hostname}:5000/v1/api/'
    endpoint = f'tickle'

    svr_req = requests.get(url=base_url+endpoint, verify=False)
    _check_fail(svr_req, 'tickle server error')
    svr_json = json.dumps(svr_req.json(), ensure_ascii=False, indent=4)

    print(svr_json)

    """
    sample output:
    {
        "session": "38002a817255d0b6cfb1020b8454c6b7",
        "ssoExpires": 564163,
        "collission": false,
        "userId": 107838735,
        "hmds": {
            "error": "no bridge"
        },
        "iserver": {
            "authStatus": {
                "authenticated": true,
                "competing": false,
                "connected": true,
                "message": "",
                "MAC": "98:F2:B3:23:AE:D0",
                "serverInfo": {
                    "serverName": "JifN19007",
                    "serverVersion": "Build 10.25.0a, Aug 29, 2023 4:29:57 PM"
                }
            }
        }
    }
    """

def logout():
    
    hostname = os.getenv('IB_WEB_HOST', 'localhost')
    base_url = f'https://{hostname}:5000/v1/api/'
    endpoint = f'logout'

    svr_req = requests.get(url=base_url+endpoint, verify=False)
    _check_fail(svr_req, 'logout error')
    svr_json = json.dumps(svr_req.json(), ensure_ascii=False, indent=4)

    print(svr_json)

    """
    sample output:
    {
        "status": true
    } 
    """