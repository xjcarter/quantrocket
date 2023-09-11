from strategy import Strategy
from clockutils import TripWire, time_from_str, unix_time_to_string 
from datetime import datetime
#import test_harness as TESTER 
import time, pandas 
from posmgr import PosMgr, TradeSide, Trade, OrderType
import calendar_calcs
from indicators import MondayAnchor, StDev
import os, sys, json
import ib_endpoints


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


class Lex(Strategy):
    def __init__(self, strategy_id, configuration_file):
        super().__init__(strategy_id, configuration_file)

        self.order_monitor = ib_endpoints.OrderMonitor()
        self.pos_mgr = PosMgr()
        self.intra_prices = list()
        self.contract_id = None
        self.symbol = None


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
        ## ANCHOR_ADJUST = -1.50 
        ## stock_df = TESTER.alter_data_to_anchor(stock_df, adjust_close=ANCHOR_ADJUST)

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


    def get_bid_ask(self, show_volume=False):
        try:
            last_print = self.intra_prices[-1] 
            bid, ask = last_print['bid'], last_print['ask']
            bid_size, ask_size = last_print['bidsz'], last_print['asksz']
            if show_volume:
                logger.info(f'current bid/ask for {self.symbol}: bid:{bid_price} ({bid_size}), ask:{ask_price} ({ask_size})')
                return bid, ask, bid_size, ask_size
            else:
                logger.info(f'current bid/ask for {self.symbol}: bid:{bid_price}, ask:{ask_price}')
                return bid, ask

        except RuntimeError(e):
            logger.critical(f'No price data available for symbol= {self.symbol}, contract_id= {self.contract_id}!')
            logger.critical(e)


    def fetch_prices(self):
        market_data = ib_endpoints.market_snapshot(self.contract_id) 
        self.intra_prices.append(market_data)

    def check_exit(self, position_node, stdv):

        current_pos, entry_price = position_node.position, position_node.price
        duration = position_node.duration

        current_price, _ask, _bidsz, _asksz = self.get_bid_ask(show_volume=True)

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
        

    def create_order(self, side, amount, order_type=OrderType.MKT, order_notes=None):

        logger.info('sending order.')

        order_info = ib_endpoints.order_request(self.contract_id, order_type.value, side.value, amount)
        if order_info.get('reply_id') is not None:
            ## confirm to server that you want to send this order
            order_info = ib_endpoints.order_reply(order_info['reply_id'])

        logger.info(f'order_id: {order_id} submitted.')

        order_info = {
            'order_id': order_id,
            'symbol': self.symbol,
            'quantity': amount,
            'side': side.value,
            'order_type': order_type.value,
            'info': order_notes
        }
        logger.info(json.dumps(order_info, ensure_ascii=False, indent =4 ))

        return order_info


    def calc_trade_amount(self, trade_capital):
        bid, ask = self.get_bid_ask()
        spread = abs(bid - ask)

        ## we can get more creative with this by monitoring spread
        ## in realtime and using an average spread...
        return int( trade_capital/(ask+spread) )

    def process_fill(self, fill):

        def _get_side(fill):
            sides = { 'BUY': TradeSide.BUY, 'SELL': TradeSide SELL }
            v = fill.get('side', None)
            if v is not None:
                return sides[v.upper()]
            else:
                fill_json = json.dumps(fill, ensure_ascii=False, indent=4)
                raise RuntimeError(f'no BUY/SELL action indicated in order fill!\n order fill: {fill_json}')

        ## map ib web api order fill
        def _convert_ib_fill(fill):
            trd = Trade( fill['trade_id'] )
            trd.asset = fill["ticker"]
            trd.order_id = fill['order_id']
            trd.side = _get_side(fill)
            trd.units = fill['qty'] 
            trd.price = fill['price']
            ## conditionals
            tms = fill.get('lastExecutionTime_r')
            if tms is not None:
                trd.timestamp = unix_time_to_string(tms)
            else:
                trd.timestamp is None: trd.stamp_timestamp()
            trd.commission = fill.get("commission")
            trd.exchange = fill.get("conidex")

            return trd

        logger.info(f'Processing trade_id: {fill["trade_id"]}')
        self.pos_mgr.update_trades( fill, conversion_func=_convert_ib_fill )


    def create_directory(self, directory_path):
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)

    def dump_intraday_prices(self, filepath):
        try:
            df = pandas.DataFrame(self.intra_prices) 
            df.to_csv(filepath, index=False)
        except:
            logger.error(f"couldn't write intraday data: {filepath}")
            raise RuntimeError(f"couldn't write intraday data: {filepath}")

    def reconcile_capital(self):
        trade_capital = self.pos_mgr.trade_capital
        logger.info(f'using trade_capital = {trade_capital}')
        return trade_capital

    def reconcile_positions(self):
        ib_position_info = ib_endpoints.current_position(self.contract_id)
        ib_position, ib_avgp = ib_position_info['position'], ib_position_info['avgPrice']
        pos_node = self.pos_mgr.get_position(self.symbol)
        lex_position, lex_avgp = pos_node.position, pos_node.price
        logger.info(f'reconciling positions: ')
        logger.info(f'IB: {ib_position} @ {ib_avgp:.4f}, Lex: {lex_position} @ {lex_avgp:.4f}')
        if ib_avgp != lex_avgp:
            logger.critical('IB and Lex avg_costs do not match!')
        if ib_position != lex_position:
            logger.critical('IB and Lex positions do not match!')
            raise RuntimeError

    def run_strategy(self):

        logger.info(f'starting strategy.')

        self.pos_mgr.initialize(self.strategy_id, set(self.cfg['universe']))
        logger.info(f'pos mgr initialized.')

        pp = self.pos_mgr.position_count()
        if pp == 0:
            raise RuntimeError(f'No targeted positions for universe: {self.cfg["universe"]}')
        if pp != 1:
            raise RuntimeError(f'Too many names: {self.pos_mgr.positions} - this a single name strategy')

        ## grab the only instrument in the universe
        self.symbol = self.cfg['universe'][0]
        self.contract_id = ib_endpoints.stock_to_contract_id(self.symbol)

        ## returns a PosNode object
        position_node = self.pos_mgr.get_position(self.symbol)
        current_pos = position_node.position
        logger.info(f'{self.symbol} current position = {current_pos}')

        data = self.load_historical_data(self.symbol)

        logger.info(f'calculating trading metrics.')
        fire_entry, stdv = self.calc_metrics(data)
        logger.info(f'trading metrics calculated.')

        
        logger.info(f'pinging IB server.')
        ib_endpoints.tickle()

        logger.info(f'initialize market data connection for symbol= {self.symbol}, contract_id= {self.contract_id}')
        market_init = ib_endpoints.market_connect(self.contract_id)
        logger.info('fetch account information from IB')
        account_info = ib_endpoints.account_summary(self.contract_id)

        time.sleep(5)

        self.reconcile_positions(self.symbol)
        trade_capital = self.reconcile_capital()

        PRE_OPEN_TIME = "09:27"
        OPEN_TIME = "09:30"
        CLOSE_TIME = "15:57"
        EOD_TIME = "16:05"

        ## trading operations schedule
        at_open = TripWire(time_from_str(OPEN_TIME))
        at_close = TripWire(time_from_str(CLOSE_TIME))
        at_end_of_day = TripWire(time_from_str(EOD_TIME))
        fetch_intra_prices = TripWire(time_from_str(PRE_OPEN_TIME), interval_reset=5, stop_at=time_from_str(EOD_TIME))  

        logger.info(f'starting trading loop.')

        while True:
           
            ## capturing 5 sec price snapshots
            ## if possible try to fetch starting at pre-open
            with fetch_intra_prices as fetch_intra:
                if fetch_intra:
                    self.fetch_prices()

            with at_open as opening:
                if opening:
                    if current_pos == 0:
                        trade_amt = self.calc_trade_amount(trade_capital)
                        if fire_entry and trade_amt > 0:
                            logger.info(f'entry triggered.')

                            _bid, open_price, _bidsz, _asksz = self.get_bid_ask(show_volume=True)

                            logger.info(f'opening ask price: {open_price}')
                            order_info = self.create_order(TradeSide.BUY, trade_amt, order_notes=self.strategy_id)
                            self.pos_mgr.register_order(order_info)
                        elif fire_entry:
                            logger.warning('entry triggered but trade_amt == 0!')
                    else:
                        logger.info(f'no trade: working open position: {symbol} {current_pos}')

            for fill in self.order_monitor.check_orders():
                self.process_fill(fill)

            with at_close as closing:
                if closing:
                    position_node = self.pos_mgr.get_position(self.symbol)
                    fire_exit, current_pos = self.check_exit(position_node, stdv)
                    logger.info(f'{symbol} {current_pos}, fire_exit = {fire_exit}')
                    if fire_exit: 
                        order_info = self.create_order(TradeSide.SELL, current_pos, order_notes=self.strategy_id)
                        self.pos_mgr.register_order(order_info)

            with at_end_of_day as end_of_day:
                if end_of_day:
                    today = datetime.today().strftime("%Y%m%d")
                    self.create_directory(f'{self.cfg["intraday_prices_dir"]}/{self.strategy_id}/')
                    intra_file = f'{self.cfg["intraday_prices_dir"]}/{self.strategy_id}/{symbol}.{today}.csv'
                    logger.info('saving intraday prices ...')
                    self.dump_intraday_prices(intra_file) 
                    logger.info('updating position durations ...')
                    self.pos_mgr.update_durations()
                    logger.info('end of day completed.')
                    logger.info('logging out.')
                    ib_endpoints.logout()

                    break

            time.sleep(1)


if __name__ == "__main__":
    parser =  argparse.ArgumentParser()
    parser.add_argument("--config", help="configuration file", required=True)
    parser.add_argument("--strategy_id", help="strategy id", required=True)
    u = parser.parse_args()

    lex = Lex(u.strategy_id, u.config)
    lex.run_strategy()
