import requests
import json
import urllib3
import os

## suppress non-secure connection warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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
    else:
        err_msg = f'{msg}: status_code= {req.status_code}'
        print(err_msg)
        raise RuntimeError(err_msg)


def order_request(contract_id, order_type, side, qty):

    hostname = os.getenv('IB_WEB_HOST', 'localhost')
    account = os.getenv('IB_ACCOUNT', 'DU7631004')
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
    _check_fail(order_req, 'couldnt place order')
    order_json = json.dumps(order_req.json(), ensure_ascii=False, indent=4)

    print(order_json) 

if __name__ == "__main__":
    ## place mkt order to by AAPL
    order_request( 265598, 'MKT', 'BUY', 100 )  
