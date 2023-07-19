from datetime import datetime, timedelta
#from quantrocket.realtime import get_prices 
#from quantrocket.blotter import place_order, download_executions
from clockutils import is_at, is_after
import calendar_calcs
import time 

import logging
# Create a mylog specific to __main__ module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s',
                    datefmt='%a %Y-%m-%d %H:%M:%S')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


START_TIME = "08:19"
OPEN_TIME = "08:21"
FIRST_HOUR = "09:00"
LAST_HOUR = "10:30"
EXIT_TIME = "10:35"
EOD_TIME = "10:45"

counter = 0
sleep_interval = 1

def mylog(text):
    global counter
    global sleep_interval

    mod = 600
    if sleep_interval == 1:
        mod = 60

    if counter % mod == 0:
        logger.info(text)
        

def snap_prices():
    mylog('snapping prices')
    return 10

def check_fills():
    mylog('check fills')

def check_entry():
    mylog('check entry')
    return True

def check_exit():
    mylog('check exit')
    return  True

def send_order():
    mylog('send_order')

def time_check():
    now = datetime.now().strftime("%Y%m%d-%H:%M:%S")
    mylog(f'now: {now}')

def initialize():
    logger.info('setting up...')
    now = datetime.now()
    while now.second != 0:
        now = datetime.now()
    logger.info('set up and initialization complete')

def main(strategy_id, universe):
    global counter
    global sleep_interval

    logger.info('start main')

    initialize()
    sleep_interval = 1
    try_entry = True
    try_exit = True 
    while True:
        clock = datetime.now()

        time_check()

        if is_after(clock, START_TIME):
            check_fills()

        if is_at(clock, OPEN_TIME, window=5) and try_entry:
            if check_entry():
                price_bar = snap_prices()
                send_order()
                try_entry = False

        if is_after(clock, FIRST_HOUR):
            logger.info('finished first hour')
            sleep_interval = 30 * 60 

        if is_after(clock, LAST_HOUR):
            logger.info('starting last hour')
            sleep_interval = 1

        if is_at(clock, EXIT_TIME, window=5) and try_exit:
            if check_exit():
                price_bar = snap_prices()
                send_order()
                try_exit = False

        if is_after(clock, EOD_TIME):
            break

        counter += 1
        time.sleep(sleep_interval)


if __name__ == "__main__":
    main('12345', ['SPY'])

