from strategy import Strategy
from clockutils import TripWire, time_from_str
from datetime import datetime
#from quantrocket.realtime import get_prices 
#from quantrocket.blotter import place_order, download_executions
import test_harness as TESTER 
import time, pandas 
from posmgr import PosMgr, TradeSide, Trade, OrderType
import calendar_calcs
from indicators import MondayAnchor, StDev
import os, sys, json
import uuid
from price_scraper import PriceSnapper

import logging
# Create a logger specific to __main__ module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
FORMAT = "%(asctime)s: %(levelname)8s [%(module)15s:%(lineno)3d - %(funcName)20s ] %(message)s"
#FORMAT = "%(asctime)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s"
formatter = logging.Formatter(FORMAT, datefmt='%a %Y-%m-%d %H:%M:%S')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

import argparse

# Connect to QuantRocket
# Make sure you have a running QuantRocket deployment
# and have configured the necessary credentials


ANCHOR_ADJUST = 0 
self.cfg['max_hold_period'] = 9


class Lex(Strategy):
    def __init__(self, strategy_id, configuration_file):
        super().__init__(strategy_id, configuration_file)

        self.pos_mgr = PosMgr()

    def load_historical_data(self, symbol):

        ## load yahoo OHLC data
        try:
            stock_file = f'{self.cfg["historical_data_dir"]}/{symbol}.csv'
            stock_df = pandas.read_csv(stock_file)
            stock_df.set_index('Date', inplace=True)
            logger.info(f'{symbol} historical data loaded.')
        except Exception as e:
            raise e
        
        ## alter data for testing 
        stock_df = TESTER.alter_data_to_anchor(stock_df, adjust_close=ANCHOR_ADJUST)

        return stock_df


    def calc_metrics(self, stock_df):

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
            if bkout < 0 and end_of_week == False:
                valid_entry = True
            x = "<-" if valid_entry else ""
            logger.info(f'{ldate}: A:{anchor_bar}, C: {last_close} {x}')

        return valid_entry, stdev.valueAt(0) 


    def get_current_bid_ask(self, symbol):

        fields = ["Bid", "Ask"]
        #prices = get_prices([symbol], fields)
        prices = TESTER.get_prices([symbol], fields)

        # Extract the bid and ask prices for SPY
        bid_price = prices.loc[symbol, "Bid"]
        ask_price = prices.loc[symbol, "Ask"]
        logger.info(f'current bid/ask for {symbol}: bid:{bid_price}, ask:{ask_price}')

        return bid_price, ask_price

    def get_current_price(self, symbol):
        bid, ask = self.get_current_bid_ask(symbol)
        return ask 

    def fetch_prices_NEW(self, symbol):
        #bar = TESTER.generate_ohlc()
        if self.price_mgr is None:
            self.price_mgr = PriceSnapper(symbol, bar_length=12)

        bar = self.price_mgr.snap_prices()
        if bar is not None:
            now = datetime.now()
            dt, tm = now.strftime("%Y%m%d"), now.strftime("%H:%M:%S")
            logger.info(f'new bar: {dt}-{tm}, {bar}')
            return [dt, tm, bar.open, bar.high, bar.low, bar.close] 
        else:
            return None

    def fetch_prices_OLD(self, symbol):
        bar = TESTER.generate_ohlc()
        nn = datetime.now()
        dt = nn.strftime("%Y%m%d")
        tm = nn.strftime("%H:%M:%S")
        logger.info(f'new bar: {dt}-{tm}, {bar}')
        return [dt, tm, bar.open, bar.high, bar.low, bar.close]


    def fetch_prices(self, symbol):
        return self.fetch_prices_OLD(symbol)

    def check_exit(self, position_node, stdv):

        current_pos, entry_price = position_node.position, position_node.price
        duration = position_node.duration

        current_price = self.get_current_price(position_node.name)

        get_out = False
        alert = 'NO_EXIT'
        if current_pos > 0:
            if current_price > entry_price:
                alert = 'PNL'
                get_out = True
            elif duration > int(self.cfg['max_hold_period']):
                alert = 'EXPIRY'
                get_out = True
            elif (entry_price - current_price) > stdv * 2: 
                alert = 'STOP ON CLOSE'
                logger.warning('stop on close triggered! current_price= {current_price}')
                get_out = True 

        logger.info(f'check_exit: exit= {get_out}, {position_node.name}, {current_pos}')
        logger.info(f'exit_details: {position_node.name}, alert= {alert} current_price= {current_price}, entry= {entry_price}, duration= {duration}')
        return get_out, current_pos
        

    ## creates and submits order
    ## order_notes is a field to hold any info that many help in auditting trades
    def create_order(self, side, symbol, amount, order_type=OrderType.MKT, order_notes=None):

        def _new_order_id(tag=None):
            # Generate a unique order ID with timestamp
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            unique_id = str(uuid.uuid4())
            if tag is not None:
                return f"{tag}-{unique_id}-{timestamp}"
            else:
                return f"{unique_id}-{timestamp}"

        # Create a market order to buy 100 shares of SPY

        order = {
            "account": self.cfg['ib_account'],
            "quantity": amount,
            "symbol": symbol,
            "action": side.value,
            "order_type": order_type.value
        }

        logger.info('sending order.')

        # Place the order

        #legacy submission
        #ib_order_id = _new_order_id(self.strategy_id) 
        #ticket = OrderStatuses.submit_order(order, ib_order_id)

        #order_id = place_order(account, symbol, quantity, action, order_type)
        #order_id = place_order(**order)
        order_id = TESTER.place_order(**order)
        logger.info(f'order_id: {order_id} submitted.')

        order_info = {
            'order_id': order_id,
            'symbol': order['symbol'],
            'quantity': order['quantity'],
            'side': order['action'],
            'order_type': order['order_type'],
            'info': order_notes
        }
        logger.info(json.dumps(order_info, ensure_ascii=False, indent =4 ))

        return order_info


    def calc_trade_amount(self, symbol, trade_capital):
        bid, ask = self.get_current_bid_ask(symbol)
        spread = abs(bid - ask)

        ## we can get more creative with this by monitoring spread
        ## in realtime and using an average spread...
        return int( trade_capital/(ask+spread) )


    def check_for_fills(self):

        ## handle fills and post all files through PosMgr object

        """
        Here are some common fields that you may typically find in the executions DataFrame:

        OrderRef: The reference or ID of the order associated with the execution.
        Symbol: The symbol or ticker of the instrument being traded.
        Exchange: The exchange where the execution occurred.
        Quantity: The quantity of the executed order.
        Side: The side of the executed order (Buy or Sell).
        Price: The execution price.
        Currency: The currency of the traded instrument.
        ExecutionTime: The timestamp of the execution.
        Account: The account associated with the execution.
        Strategy: The strategy or algorithm associated with the execution.

        FIX THIS: you have to adjust _convert_quantrocket_fill 
        """

        def _get_side(fill):
            sides = { 'BUY': TradeSide.BUY, 'SELL': TradeSide.SELL }
            v = fill.get('side', fill.get('action'))
            if v is not None:
                return sides[v]
            else:
                raise RuntimeError(f'no BUY/SELL action indicated in order!\n order: {order}')

        ## map quantrocket order fill
        def _convert_quantrocket_fill(fill):
            trd = Trade( fill['trade_id'] )
            trd.asset = fill["symbol"]
            trd.order_id = fill['order_id']
            trd.side = _get_side(fill)
            trd.units = abs(int(fill["quantity"]))
            trd.price = fill["price"]

            ## conditionals
            trd.timestamp = fill.get("timestamp")
            if trd.timestamp is None: trd.stamp_timestamp()
            trd.commission = fill.get("commission")
            trd.exchange = fill.get("exchange")

            return trd


        logger.info('checking for fills.')

        #filled_orders = download_executions()
        start_date = end_date = datetime.today().date()
        filled_orders = TESTER.download_executions(start_date, end_date, accounts=[self.cfg['ib_account']])

        for fill in filled_orders:
            logger.info(f'Processing trade_id: {fill["trade_id"]}')
            self.pos_mgr.update_trades( fill, conversion_func=_convert_quantrocket_fill )

    def create_directory(self, directory_path):
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)

    def dump_intraday_prices(self, data, filepath):
        df = pandas.DataFrame(columns=['Date','Time','Open','High','Low','Close'], data=data)
        try:
            df.set_index('Date',inplace=True)
            df.to_csv(filepath)
        except:
            logger.error(f"couldn't write intraday data: {filepath}")
            raise RuntimeError(f"couldn't write intraday data: {filepath}")


    def run(self):

        global ANCHOR_ADJUST 

        ANCHOR_ADJUST = -1.50 
        OPEN_TIME = "09:30"
        CLOSE_TIME = "15:57"
        EOD_TIME = "16:05"

        logger.info(f'starting strategy.')

        self.pos_mgr.initialize(self.strategy_id, set(self.cfg['universe']))
        logger.info(f'pos mgr initialized.')

        pp = self.pos_mgr.position_count()
        if pp == 0:
            raise RuntimeError(f'No targeted positions for universe: {universe}')
        if pp != 1:
            raise RuntimeError(f'Too many names: {self.pos_mgr.positions} - this a single name strategy')

        ## grab the only instrument in the universe
        symbol = self.cfg['universe'][0]

        ## returns a PosNode object
        position_node = self.pos_mgr.get_position(symbol)
        current_pos = position_node.position
        logger.info(f'{symbol} current position = {current_pos}')

        data = self.load_historical_data(symbol)

        logger.info(f'calculating trading metrics.')
        fire_entry, stdv = self.calc_metrics(data)
        logger.info(f'trading metrics calculated.')

        logger.info(f'trading loop initiated.')

        ## trading operations schedule
        at_open = TripWire(time_from_str(OPEN_TIME))
        at_close = TripWire(time_from_str(CLOSE_TIME))
        at_end_of_day = TripWire(time_from_str(EOD_TIME))
        fetch_intra_prices = TripWire(time_from_str(OPEN_TIME), interval_reset=60, stop_at=time_from_str(EOD_TIME))  

        intra_prices = list()


        while True:
           
            ## capturing 1min bars with 5sec price snapshots
            with fetch_intra_prices as fetch_intra:
                if fetch_intra:
                    new_bar = self.fetch_prices(symbol)
                    if new_bar:
                        intra_prices.append( new_bar )

            with at_open as opening:
                if opening:

                    if current_pos == 0:
                        trade_amt = self.calc_trade_amount(symbol, self.pos_mgr.trade_capital)
                        if fire_entry and trade_amt > 0:
                            logger.info(f'entry triggered.')

                            open_price = self.get_current_price(position_node.name)

                            logger.info(f'opening price: {open_price}')
                            order_info = self.create_order(TradeSide.BUY, symbol, trade_amt, order_notes=self.strategy_id)
                            self.pos_mgr.register_order(order_info)
                        elif fire_entry:
                            logger.warning('entry triggered but trade_amt == 0!')
                    else:
                        logger.info(f'no trade: working open position: {symbol} {current_pos}')


            with at_close as closing:
                if closing:

                    position_node = self.pos_mgr.get_position(symbol)
                    fire_exit, current_pos = self.check_exit(position_node, stdv)
                    logger.info(f'{symbol} {current_pos}, fire_exit = {fire_exit}')
                    if fire_exit: 
                        order_info = self.create_order(TradeSide.SELL, symbol, current_pos, order_notes=self.strategy_id)
                        self.pos_mgr.register_order(order_info)

            self.check_for_fills()

            with at_end_of_day as end_of_day:
                if end_of_day:
                    today = datetime.today().strftime("%Y%m%d")
                    self.create_directory(f'{self.cfg["intraday_prices_dir"]}/{self.strategy_id}/')
                    intra_file = f'{self.cfg["intraday_prices_dir"]}/{self.strategy_id}/{symbol}.{today}.csv'
                    logger.info('saving intraday prices ...')
                    self.dump_intraday_prices(intra_prices, intra_file) 
                    logger.info('updating position durations ...')
                    self.pos_mgr.update_durations()
                    logger.info('end of day completed.')
                    break


            time.sleep(1)


if __name__ == "__main__":
    parser =  argparse.ArgumentParser()
    parser.add_argument("--config", help="configuration file", required=True)
    parser.add_argument("--strategy_id", help="strategy id", required=True)
    u = parser.parse_args()

    lex = Lex(u.strategy_id, u.config)
    lex.run()
