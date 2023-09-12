
import ib_endpoints
import time


om = ib_endpoints.OrderMonitor()

## simulated mulitple polling of position snapshots
## used the mock_order_status() method in ib_endpoints
i = 0
while i < 3:
    print("")
    om.monitor_orders()
    time.sleep(2)
    i += 1
    
