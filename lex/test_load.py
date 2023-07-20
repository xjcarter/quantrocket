import pandas
import calendar_calcs
import os 
import test_harness
from indicators import MondayAnchor, StDev
from datetime import datetime 

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s',
                    datefmt='%a %Y-%m-%d %H:%M:%S')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

YAHOO_DATA_DIRECTORY = os.environ.get('YAHOO_DATA_DIRECTORY', '/home/jcarter/work/trading/data/')

def load_historical_data(symbol):
    ## load yahoo OHLC data
    try:
        stock_file = f'{YAHOO_DATA_DIRECTORY}/{symbol}.csv'
        stock_df = pandas.read_csv(stock_file)
        stock_df.set_index('Date', inplace=True)
    except Exception as e:
        raise e


    return stock_df


def calc_metrics(stock_df):

    valid_entry = False

    daysback = 50
    holidays = calendar_calcs.load_holidays()
    anchor = MondayAnchor(derived_len=daysback)
    stdev = StDev(sample_size=daysback)

    ss = len(stock_df)
    if ss < daysback:
        logger.error(f'Not enoungh data to calc metrics: len={ss}, daysback={daysback}')
        raise RuntimeError(f'Not enoungh data to calc metrics: len={ss}, daysback={daysback}')

    today = datetime.today().date()
    gg = stock_df[-daysback:]
    end_of_week = calendar_calcs.is_end_of_week(today, holidays)

    last_indicator_date = None
    last_close = None
    for i in range(gg.shape[0]):
        idate = gg.index[i]
        stock_bar = gg.loc[idate]
        cur_dt = datetime.strptime(idate,"%Y-%m-%d").date()
        anchor.push((cur_dt, stock_bar))
        stdev.push(stock_bar['Close'])
        last_indicator_date = cur_dt
        last_close = stock_bar['Close']

    ## make sure the signal is for the previous trading day
    if last_indicator_date != calendar_calcs.prev_trading_day(today, holidays):
        logger.error(f'incomplete data for indicators, last_indicator_date: {last_indicator_date}')
        raise RuntimeError(f'incomplete data for indicators, last_indicator_date: {last_indicator_date}')

    ldate = last_indicator_date.strftime("%Y%m%d %a")
    if anchor.count() > 0:
        anchor_bar, bkout = anchor.valueAt(0)
        ## show last indcator date, anchor bar and close
        logger.info(f'>>> {ldate}: A:{anchor_bar}, C:{last_close}')
        if bkout < 0 and end_of_week == False:
            logger.info(f'buy triggered!')
            valid_entry = True

    return valid_entry, stdev.valueAt(0)




df = load_historical_data('SPY')
print(df.tail(15))

## alter data for testing
ndf = test_harness.alter_data_to_anchor(df, adjust_close=-0.03)
calc_metrics(ndf)
