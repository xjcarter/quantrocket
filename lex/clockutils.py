from datetime import datetime, timedelta

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

## create datetime for string in "%Y%m%d-%H%M%S"
def date_from_str(dstring):
    return datetime.strptime(dstring,"%Y%m%d").date()

def time_from_str(time_string, date_string=None):
    time_parts = time_string.split(':')
    hour = int(time_parts[0])
    minute = int(time_parts[1])

    current_date=  datetime.now().date()
    if date_string is not None:
        current_date = date_from_str(date_string)
    new_time = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=hour, minutes=minute)
    return new_time


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


## context manager that executes a block of code once
## as time barrier 'trigger_dt' has been hit

from datetime import datetime, timedelta
import time

class TripWire:
    def __init__(self, trigger_dt, interval_reset=None):
        self.trigger_dt = trigger_dt
        self.triggered = False
        self.interval_reset = interval_reset

    def __enter__(self):
        current_dt = datetime.now()
        if not self.triggered and current_dt >= self.trigger_dt:
            self.triggered = True
            if self.interval_reset:
                self.trigger_dt += timedelta(seconds=self.interval_reset)
                self.triggered = False
            return self
        else:
            return None

    def __exit__(self, exc_type, exc_value, traceback):
        pass


if __name__ == "__main__":
    v = time_from_str("11:30")
    j = date_from_str("20111212")
    print(v, type(v))
    print(j, type(j))

    trigger_dt = datetime.now() + timedelta(seconds=5)
    end_dt = datetime.now() + timedelta(seconds=7)
    tt = TripWire(trigger_dt)

    print('running at:', datetime.now())
    while datetime.now() < end_dt:
        with tt as t:
            if t: 
                now = datetime.now()
                print(f'executing at: {now}')
                print('TripWire activated')

        now = datetime.now()
        print(now)
        time.sleep(1)




    
