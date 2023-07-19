from datetime import datetime, timedelta
#from quantrocket.realtime import get_prices 
#from quantrocket.blotter import place_order, download_executions
from clockutils import is_at, is_after
import calendar_calcs
import time 

import sys

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


START_TIME = "13:08"
OPEN_TIME = "11:32"
FIRST_HOUR = "11:40"
LAST_HOUR = "11:45"
EXIT_TIME = "11:50"
EOD_TIME = "11:55"

TEST_TIME= "13:05"

def mylog(text):
    now = datetime.now().strftime("%Y%m%d-%H:%M:%S")
    print(f'{now} | {text}')
        

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
    print('set up and initialization complete')

def main(strategy_id, universe):

    print('start main')

    sleep_interval = 1

    initialize()
    try_entry = True
    try_exit = True 
    while True:
        clock = datetime.now()

        if is_after(clock, START_TIME):
            check_fills()
            break

        if is_after(clock, TEST_TIME):
            send_order()
            
        time.sleep(sleep_interval)


if __name__ == "__main__":
    main('12345', ['SPY'])

