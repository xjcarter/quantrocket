from datetime import datetime, timedelta
#from quantrocket.realtime import get_prices 
#from quantrocket.blotter import place_order, download_executions
from clockutils import TripWire, time_from_str 

import logging
import sys, time

# Create a logger.info specific to __main__ module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s',
                    datefmt='%a %Y-%m-%d %H:%M:%S')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)



def snap_prices():
    logger.info('snapping prices')
    return 10

def check_fills():
    logger.info('check fills')

def check_entry():
    logger.info('check entry')
    return True

def check_exit():
    logger.info('check exit')
    return  True

def send_order():
    logger.info('send_order')

def initialize():
    logger.info('set up and initialization complete')


def main(strategy_id, universe):

    logger.info('start main')

    initialize()

    ##at_open = TripWire(time_from_str("09:31"))
    ##every_30_mins = TripWire(time_from_str("9:31"), interval_reset=(60*30))
    ##at_close = TripWire(time_from_str("15:55"))
    ##at_end = TripWire(time_from_str("16:10"))

    at_open = TripWire(time_from_str("09:30"))
    every_10_mins = TripWire(time_from_str("09:30"), interval_reset=(60*10))
    at_close = TripWire(time_from_str("15:55"))
    at_end = TripWire(time_from_str("16:05"))
    while True:
        with at_open as opening:
            if opening:
                check_entry()
                price_bar = snap_prices()
                send_order()

        with at_close as closing:
            if closing:
                check_exit()
                price_bar = snap_prices()
                send_order()
        
        with every_10_mins as check:
            if check:
                check_fills()

        with at_end as end_of_day:
            if end_of_day:
                logger.info("end_of_day!!")
                break

        time.sleep(1)


if __name__ == "__main__":
    main('12345', ['SPY'])

