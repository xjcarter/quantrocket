from datetime import datetime, timedelta
import asyncio

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


START_TIME = "08:57"
OPEN_TIME = "09:05"
EXIT_TIME = "10:20"
EOD_TIME = "10:45"


## create date time object a from time string (HH:MM)
## calculate the second between a benchmark datetime and the forward looking time.
def seconds_until(benchmark, time_string):
    now = benchmark
    logger.info(f'benchmark = {benchmark.strftime("%Y%m%d-%H%M%S")}')
    current_date = now.date()  # Get the current date
    time_parts = time_string.split(':')

    hour = int(time_parts[0])
    minute = int(time_parts[1])

    # Create a datetime object using the current date and the provided time
    new_time = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=hour, minutes=minute)
    secs_util = (new_time - now).total_seconds()
    logger.info(f'new_time= {new_time.strftime("%Y%m%d-%H%M%S")}, secs_util= {secs_util}')

    return new_time, secs_util

def time_until(date_string):
    now = datetime.now()
    return seconds_until(now, date_string) 


async def handle_trade_fills(tag):

    logger.info(f'handle_fills_start: {tag}') 

    FETCH_WINDOW = 1200 # 20min 

    #end_time = datetime.now() + timedelta(minutes=FETCH_WINDOW)
    #while datetime.now() < end_time:
    counter = 0
    while counter < FETCH_WINDOW:
       
        if counter % 60 == 0:
            logger.info(f'Processing potential order. counter= {counter}')

        counter += 1

        await asyncio.sleep(1)

    logger.info(f'handle_fills_end {tag}') 


async def main(strategy_id, universe):

    logger.info('start main')
    start_time, secs_until_start = time_until(START_TIME)
    logger.info(f'sleeping until {start_time.strftime("%Y%m%d-%H:%M:%S")} START.')
    await asyncio.sleep(secs_until_start)
    logger.info(f'*** START ***')

    open_time, secs_until_open = time_until(OPEN_TIME)
    logger.info(f'sleeping until {open_time.strftime("%Y%m%d-%H:%M:%S")} OPEN.')
    await asyncio.sleep(secs_until_open)
    logger.info(f'*** SENDING TRADE ON OPEN ***')
    asyncio.create_task( handle_trade_fills('OPEN') )

    exit_time, secs_until_exit = time_until(EXIT_TIME)
    logger.info(f'sleeping until {exit_time.strftime("%Y%m%d-%H:%M:%S")} EXIT.')
    logger.info(f'secs_until_exit = {secs_until_exit}')
    await asyncio.sleep(secs_until_exit)
    logger.info(f'*** EXIT -> CHECKING CLOSE ***')
    asyncio.create_task( handle_trade_fills('CLOSE') )

    eod_time, secs_until_eod = time_until(EOD_TIME)
    logger.info(f'sleeping until {eod_time.strftime("%Y%m%d-%H:%M:%S")} END OF DAY.')
    await asyncio.sleep(secs_until_eod)
    logger.info(f'*** END OF DAY ***')


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main('12345', ['SPY']))
