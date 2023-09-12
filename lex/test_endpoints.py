
import ib_endpoints

#ib_endpoints.current_position(265598)
#ib_endpoints.account_summary()
#ib_endpoints.order_status()  
#ib_endpoints.order_request( 265598, 'MKT', 'BUY', 100 )  
#ib_endpoints.tickle()  
#ib_endpoints.status() 

order_monitor = ib_endpoints.OrderMonitor()

for fill in order_monitor.monitor_orders():
    print(fill)
