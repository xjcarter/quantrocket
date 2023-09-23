
import ib_endpoints
import json

#symbol='AAPL'
#contract_id = ib_endpoints.symbol_to_contract_id(symbol)
#print(f'contract_id = {contract_id}, symbol= {symbol}')

#strategy_id = 'stratX'
#account_info = ib_endpoints.account_summary()
#account_file = f'{strategy_id}.account_info.json'
#with open(account_file, 'w') as f:
#    acc_info = json.dumps(account_info, ensure_ascii=False, indent=4)
#    f.write(acc_info)

#ib_endpoints.current_position(265598)
#ib_endpoints.order_status()  
#ib_endpoints.order_request( 265598, 'MKT', 'BUY', 100 )  
#ib_endpoints.order_request( 265598, 'STP', 'SELL', 50, tgt_price=200 )  

#ib_endpoints.market_connect( 265598 ) 
#market_init = ib_endpoints.market_connect( 265598 )
#print(market_init)

#ib_endpoints.market_snapshot( 265598 )  

"""
order_info = ib_endpoints.order_reply(reply_id='34d51a47-3307-44ec-81cf-06cb1a16ddd0',repeat=True)
print("-- order reply info--")
print(json.dumps(order_info, ensure_ascii=False, indent=4))
"""

"""
order_info = ib_endpoints.order_request( 265598, 'MKT', 'BUY', 100 )  
print("-- order info--")
print(json.dumps(order_info, ensure_ascii=False, indent=4))
"""

#p = ib_endpoints.tickle()  
#print(json.dumps(p, ensure_ascii=False, indent=4))
#ib_endpoints.status() 

"""
IMPORTANT: replace the order_status() call within OrderMonitor.monitor_orders() with
           mock_order_status(), and make sure the snap_order*.txt are in current dir

order_monitor = ib_endpoints.OrderMonitor()

i = 0
while i < 3:
    for fill in order_monitor.monitor_orders():
        print(fill)
    i += 1
"""
