from datetime import datetime, timedelta
#from quantrocket.realtime import get_prices 
#from quantrocket.blotter import place_order, download_executions
from clockutils import is_at, is_after
import calendar_calcs
import time 

import logging
# Create a logger specific to __main__ module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s',
                    datefmt='%a %Y-%m-%d %H:%M:%S')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


START_TIME = "10:15"
OPEN_TIME = "10:21"
FIRST_HOUR = "10:50"
LAST_HOUR = "11:30"
EXIT_TIME = "11:35"
EOD_TIME = "11:45"


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
    sleep_interval = 1
    try_entry = True
    try_exit = True 
    marked = marked2 = False
    while True:
        clock = datetime.now()

        if is_after(clock, START_TIME):
            check_fills()

        if is_at(clock, OPEN_TIME, window=5) and try_entry:
            if check_entry():
                price_bar = snap_prices()
                send_order()
                try_entry = False

        if is_after(clock, FIRST_HOUR) and not marked:
            logger.info('finished first hour')
            marked = True

        if is_after(clock, LAST_HOUR) and not marked2:
            logger.info('starting last hour')
            marked2 = True

        if is_at(clock, EXIT_TIME, window=5) and try_exit:
            if check_exit():
                price_bar = snap_prices()
                send_order()
                try_exit = False

        if is_after(clock, EOD_TIME):
            logger.info('EOD')
            break

        time.sleep(sleep_interval)


if __name__ == "__main__":
    main('12345', ['SPY'])

