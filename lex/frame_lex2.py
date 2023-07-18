from datetime import datetime, timedelta
#from quantrocket.realtime import get_prices 
#from quantrocket.blotter import place_order, download_executions
import asyncio
import os

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

START_TIME = "14:30"
OPEN_TIME = "14:45"
EXIT_TIME = "16:00"
EOD_TIME = "16:30"

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


async def handle_trade_fills(tag):

    logger.info(f'handle_fills_start: {tag}')

    counter = 0
    end_time = datetime.now() + timedelta(minutes=20)
    while datetime.now() < end_time:
#    while counter < 1200:

        if counter % 60 == 0:
            logger.info(f'Processing potential order. counter= {counter}')

        counter += 1

        await asyncio.sleep(1)

    logger.info(f'handle_fills_end {tag}')


async def main(strategy_id, universe):

    logger.info('start main')
    now = datetime.now()

    start_time, secs_until_start = time_until(now, START_TIME)
    open_time, secs_until_open = time_until(now, OPEN_TIME)
    exit_time, secs_until_exit = time_until(open_time, EXIT_TIME)
    eod_time, secs_until_eod = time_until(exit_time, EOD_TIME)

    logger.info(f'sleeping until {start_time.strftime("%Y%m%d-%H:%M:%S")} START.')
    logger.info(f'secs_until_start= {secs_until_start}')
    await asyncio.sleep(secs_until_start)
    logger.info(f'*** START ***')

    logger.info(f'sleeping until {open_time.strftime("%Y%m%d-%H:%M:%S")} OPEN.')
    logger.info(f'secs_until_open= {secs_until_open}')
    await asyncio.sleep(secs_until_open)
    logger.info(f'*** SENDING TRADE ON OPEN ***')
    open_task = asyncio.create_task( handle_trade_fills('OPEN') )

    logger.info(f'sleeping until {exit_time.strftime("%Y%m%d-%H:%M:%S")} EXIT.')
    logger.info(f'secs_until_exit= {secs_until_exit}')
    await asyncio.sleep(secs_until_exit)
    logger.info(f'*** EXIT -> CHECKING CLOSE ***')
    close_task = asyncio.create_task( handle_trade_fills('CLOSE') )

    logger.info(f'sleeping until {eod_time.strftime("%Y%m%d-%H:%M:%S")} END OF DAY.')
    logger.info(f'secs_until_eod= {secs_until_eod}')
    await asyncio.sleep(secs_until_eod)
    logger.info(f'*** END OF DAY ***')

    await open_task
    await close_task
    logger.info(f'jobs completed.')


    #await asyncio.gather(open_task, close_task)

def show_splits():
    now = datetime.now()
    start_time, secs_until_start = time_until(now, START_TIME)
    open_time, secs_until_open = time_until(now, OPEN_TIME)
    exit_time, secs_until_exit = time_until(open_time, EXIT_TIME)
    eod_time, secs_until_eod = time_until(exit_time, EOD_TIME)

    logger.info(f'{start_time} secs_until= {secs_until_start}')
    logger.info(f'{open_time} secs_until= {secs_until_open}')
    logger.info(f'{exit_time} secs_until= {secs_until_exit}')
    logger.info(f'{eod_time} secs_until= {secs_until_eod}')

if __name__ == "__main__":
    #show_splits()
    asyncio.run( main('12345', ['SPY']) )

