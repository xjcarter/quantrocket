
import ib_endpoints
import json

#ib_endpoints.current_position(265598)
#ib_endpoints.account_summary()
#ib_endpoints.order_status()  
#ib_endpoints.order_request( 265598, 'MKT', 'BUY', 100 )  
#ib_endpoints.order_request( 265598, 'STP', 'SELL', 50, tgt_price=200 )  
#ib_endpoints.market_connect( 265598 )  
#ib_endpoints.market_snapshot( 265598 )  

"""
order_info = ib_endpoints.order_reply(reply_id='3062b1a0-005b-46c6-b99b-49d070793a52', repeat=True)
print("-- order reply info--")
print(json.dumps(order_info, ensure_ascii=False, indent=4))
"""

"""
order_info = ib_endpoints.order_request( 265598, 'MKT', 'BUY', 100 )  
print("-- order info--")
print(json.dumps(order_info, ensure_ascii=False, indent=4))
"""

#ib_endpoints.tickle()  
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
