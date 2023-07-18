from datetime import datetime, timedelta
#from quantrocket.realtime import get_prices 
#from quantrocket.blotter import place_order, download_executions
import os, time
import threading

from posmgr import PosMgr, Trade, TradeSide
import calendar_calcs

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


# Connect to QuantRocket
# Make sure you have a running QuantRocket deployment
# and have configured the necessary credentials

# Set the account
IB_ACCOUNT_NAME = "YOUR_ACCOUNT_NAME"

YAHOO_DATA_DIRECTORY = os.environ.get('YAHOO_DATA_DIRECTORY', '/home/jcarter/work/trading/data/')

POS_MGR = PosMgr()

OPEN_TIME = "08:40"
EXIT_TIME = "09:40"
EOD_TIME = "10:10"

def time_until(benchmark, time_string):
    now = benchmark
    current_date = now.date()  # Get the current date
    time_parts = time_string.split(':')

    hour = int(time_parts[0])
    minute = int(time_parts[1])

    # Create a datetime object using the current date and the provided time
    new_time = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=hour, minutes=minute)
    secs_until = (new_time - now).total_seconds()

    return new_time, secs_until


def handle_fills(tag):

    logger.info(f'handle_fills_start: {tag}')

    counter = 0
    end_time = datetime.now() + timedelta(minutes=20)
    while datetime.now() < end_time:
    #while counter < 1200:

        if counter % 60 == 0:
            logger.info(f'Processing potential order. counter= {counter}')

        counter += 1

        time.sleep(1)

    logger.info(f'handle_fills_end {tag}')


def main(strategy_id, universe):

    logger.info('start main')
    now = datetime.now()

    open_time, secs_until_open = time_until(now, OPEN_TIME)
    exit_time, secs_until_exit = time_until(open_time, EXIT_TIME)
    eod_time, secs_until_eod = time_until(exit_time, EOD_TIME)

    logger.info(f'*** START ***')

    logger.info(f'sleeping until {open_time.strftime("%Y%m%d-%H:%M:%S")} OPEN.')
    logger.info(f'secs_until_open= {secs_until_open}')
    time.sleep(secs_until_open)

    logger.info(f'*** SENDING TRADE ON OPEN ***')
    thread1 = threading.Thread(target=handle_fills, args=('OPEN',))
    thread1.start()

    logger.info(f'sleeping until {exit_time.strftime("%Y%m%d-%H:%M:%S")} EXIT.')
    logger.info(f'secs_until_exit= {secs_until_exit}')
    time.sleep(secs_until_exit)

    logger.info(f'*** EXIT -> CHECKING CLOSE ***')
    thread2 = threading.Thread(target=handle_fills, args=('CLOSE',))
    thread2.start()

    logger.info(f'sleeping until {eod_time.strftime("%Y%m%d-%H:%M:%S")} END OF DAY.')
    logger.info(f'secs_until_eod= {secs_until_eod}')
    time.sleep(secs_until_eod)

    thread1.join()
    thread2.join()
    logger.info(f'*** END OF DAY ***')


def show_splits():
    now = datetime.now()
    open_time, secs_until_open = time_until(now, OPEN_TIME)
    exit_time, secs_until_exit = time_until(open_time, EXIT_TIME)
    eod_time, secs_until_eod = time_until(exit_time, EOD_TIME)

    logger.info(f'{open_time} secs_until= {secs_until_open}')
    logger.info(f'{exit_time} secs_until= {secs_until_exit}')
    logger.info(f'{eod_time} secs_until= {secs_until_eod}')

if __name__ == "__main__":
    #show_splits()
    main('12345', ['SPY'])

