import requests
import json
import urllib3
import os

## suppress non-secure connection warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _check_fail(req, msg):
    if req.status_code != 200:
        err_msg = f'{msg}: status_code= {req.status}'
        print(err_msg)
        raise RuntimeError(err_msg)

def order_request(contract_id, order_type, side, qty):

    hostname = os.getenv('IB_WEB_HOST', 'localhost')
    account = os.getenv('IB_ACCOUNT', 'wccpid782')
    base_url = f'https://{hostname}:5000/v1/api/'
    endpoint = f'iserver/account/{account}/orders'

    json_body = {
            "orders":[ 
                {
                    "conid": contract_id,
                    "orderType": order_type,
                    "side": side,
                    "tif": "DAY",
                    "quantity": qty
                }
            ]
    }

    order_req = requests.post(url=base_url+endpoint, verify=False, json=json_body)
    order_json = json.dumps(order_req.json(), ensure_ascii=False, indent=4)\

    _check_fail(order_req, 'couldnt place order')

    print(order_json) 

    order_info = {
        'order_id': order_json.get('order_id')
        'order_status': order_json.get('order_status')
        'reply_id': order_json.get('id')
        'reply_messeage': order_json.get('message')
    }

    return order_info

## answer to precautionary messages after an order placement.
def order_reply(reply_id, repeat=True):

    hostname = os.getenv('IB_WEB_HOST', 'localhost')
    base_url = f'https://{hostname}:5000/v1/api/'
    endpoint = f'iserver/reply/'
   
    while reply_id != None:

        reply_url = "".join([base_url, endpoint, reply_id])

        ## responding to 'are you sure?' reply
        json_body = {"confirmed": True}

        reply_req = requests.post(url=reply_url, verify=False, json=json_body)
        reply_json = json.dumps(reply_req.json(), ensure_ascii=False, indent=4)

        _check_fail(reply_req, 'order request reply')
        
        print(reply_json)

        order_info = {
            'order_id': order_json.get('order_id')
            'order_status': order_json.get('order_status')
            'reply_id': order_json.get('id')
            'reply_messeage': order_json.get('message')
        }

        if repeat:
            new_reply_id = order_info['reply_id']
            if new_reply_id != None and new_reply_id != reply_id:
                reply_id = new_reply_id
            else:
                err_msg = 'error: current reply_id = new reply_id!'
                print(err_msg)
                raise RuntimeError(err_msg)
                break

    return order_info 


def order_status(filters):

    hostname = os.getenv('IB_WEB_HOST', 'localhost')
    account = os.getenv('IB_ACCOUNT', 'wccpid782')
    base_url = f'https://{hostname}:5000/v1/api/'
    endpoint = f'iserver/account/order'

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
    if len(filters_string) > 0:
        request_url += f'?Filters={filters_string}'

    fill_req = request.get(url=request_url, verify=False)
    fill_json = json.dumps(fill_req.json(), ensure_ascii=False, indent=4)
    print(fill_json)

    _check_fail(fill_req, 'check fills error')

    return fill_json.get('orders') 




## initializes marlet subscription - call before snapshot
def market_connect(contract_id):
    
    hostname = os.getenv('IB_WEB_HOST', 'localhost')
    account = os.getenv('IB_ACCOUNT', 'wccpid782')
    base_url = f'https://{hostname}:5000/v1/api/'
    endpoint = f'iserver/marketdata/snapshot'

    fields=f'fields=55'

    params = "&".join([f'conids={contract_id}', fields])
    request_url = "".join([base_url, endpoint, "?", params])

    md_req = request.get(url=request_url, verify=False)
    md_json = json.dumps(md_req.json(), ensure_ascii=False, indent=4)
    print(md_json)

    _check_fail(md_req, 'market connect error')

    print(f'market connected for conid= {contract_id}')

    return True


def market_snapshot(contract_id):
    
    hostname = os.getenv('IB_WEB_HOST', 'localhost')
    base_url = f'https://{hostname}:5000/v1/api/'
    endpoint = f'iserver/marketdata/snapshot'

    def _v_x100(v):
        if v is None: return v
        return int(v) * 100
 
    def _int(v):
        if v is None: return v
        return int(v)

    def _float(v):
        if v is None: return v
        return float(v)

    def _str(v):
        if v is None: return v
        return float(v)
        
         
    field_dict = {
            'last': ('31', _float),
            'ask': ('84', _float),
            'bid': ('86', _float),
            'bid_sz': ('88', _v_x100),
            'ask_sz': ('85', _v_x100),
            'volume': ('7762' _int),
            'symbol': ('55', _str)
            'conid': ('6008', int)
    }

    values = ",".join(field_dict.values())
    fields=f'fields={values}'

    params = "&".join([f'conids={contract_id}', fields])
    request_url = "".join([base_url, endpoint, "?", params])

    md_req = request.get(url=request_url, verify=False)
    md_json = json.dumps(md_req.json(), ensure_ascii=False, indent=4)
    print(md_json)

    _check_fail(md_req, 'market snapshot error')

    data_dict = md_req[0]
    ## v[0] data field number, v[1] conversion func for the field
    market_data = dict([ (k, v[1](data_dict.get(v[0])) ) for k,v in fields_dict.items() ])

    return market_data
    

def account_summary(contract_id):
    
    hostname = os.getenv('IB_WEB_HOST', 'localhost')
    account = os.getenv('IB_ACCOUNT', 'wccpid782')
    base_url = f'https://{hostname}:5000/v1/api/'
    endpoint = f'portfolio/{account}/summary'

    pos_req = requests.get(url=base_url+endpoint, verify=False)
    pos_json = json.dumps(pos_req.json(), ensure_ascii=False, indent=4)
    print(pos_json)

    _check_fail(pos_req, 'account summary error')

    return pos_req.json()


def current_position(contract_id):
    
    hostname = os.getenv('IB_WEB_HOST', 'localhost')
    account = os.getenv('IB_ACCOUNT', 'wccpid782')
    base_url = f'https://{hostname}:5000/v1/api/'
    endpoint = f'portfolio/{account}/position/{contract_id}'

    pos_req = requests.get(url=base_url+endpoint, verify=False)
    pos_json = json.dumps(pos_req.json(), ensure_ascii=False, indent=4)
    print(pos_json)

    _check_fail(pos_req, 'current position error')

    return pos_req.json()


## takes a list of symbols and returns contract ids specific to exchange
def stock_to_contract_id(symbols_list):
    
    hostname = os.getenv('IB_WEB_HOST', 'localhost')
    base_url = f'https://{hostname}:5000/v1/api/'
    endpoint = f'trsrv/stocks'

    syms = ",".join([x.upper() for x in symbols_list])
    symbols = f'symbols={syms}'

    url = "".join([base_url, endpoint, "?", symbols])
    stk_req = requests.get(url=url, verify=False)
    stk_json = json.dumps(stk_req.json(), ensure_ascii=False, indent=4)
    print(stk_json)

    _check_fail(stk_req, 'stock conid lookup error')

    return stk_json


def tickle():
    
    hostname = os.getenv('IB_WEB_HOST', 'localhost')
    account = os.getenv('IB_ACCOUNT', 'wccpid782')
    base_url = f'https://{hostname}:5000/v1/api/'
    endpoint = f'tickle'

    svr_req = requests.get(url=base_url+endpoint, verify=False)
    svr_json = json.dumps(svr_req.json(), ensure_ascii=False, indent=4)
    print(svr_json)

    _check_fail(svr_req, 'tickle server error')


def logout():
    
    hostname = os.getenv('IB_WEB_HOST', 'localhost')
    account = os.getenv('IB_ACCOUNT', 'wccpid782')
    base_url = f'https://{hostname}:5000/v1/api/'
    endpoint = f'logout'

    svr_req = requests.get(url=base_url+endpoint, verify=False)
    svr_json = json.dumps(svr_req.json(), ensure_ascii=False, indent=4)
    print(svr_json)

    _check_fail(svr_req, 'logout error')
