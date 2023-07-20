
from clockutils import TripWire, time_from_str
import time 
from datetime import datetime

_every_10 = TripWire( time_from_str("17:40"), interval_reset=10 )
i = 0

while i < 200:
    with _every_10 as ten:
        if ten:
            v = datetime.now().strftime("%Y%m%d-%H:%M:%S")
            print(f'now = {v}')

    i += 1
    time.sleep(1)

