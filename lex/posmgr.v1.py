
import json 
from datetime import datetime
import re
import os
import pandas
from enum import Enum
import mysql.connector
import calendar_calcs

import logging
# Create a logger specific to __main__ module
logger = logging.getLogger(__name__)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s',
                    datefmt='%a %Y-%m-%d %H:%M:%S')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


##
## position node for each name traded
## all nodes are saved to a state file to be loaded and updated by the trading engine each day
## framework for loading daily trades and names to trade
## 


PORTFOLIO_DIRECTORY = os.environ.get('PORTFOLIO_DIRECTORY', '/home/jcarter/junk/portfolio/')

class TradeSide(str, Enum):
    BUY = 'BUY'
    SELL = 'SELL'

class PosNode(object):
    def __init__(self, name):
        self.name = name
        self.position = 0
        self.duration = 0
        self.price = 0
        self.timestamp = '' 

    def to_dict(self):
        m = dict()
        for k, v in self.__dict__.items():
            m.update({k:v})
        return m

    def from_dict(self, json_dict):
        for k, v in json_dict.items():
            self.__dict__.update({k:v})
        return self

    def copy(self):
        new_node = PosNode(self.name)
        new_node.__dict__.update(self.__dict__)
        return new_node

    def stamp_with_time(self):
        now = datetime.now()
        self.timestamp = now.strftime("%Y%m%d-%H:%M:%S")

## 
## capital allocation node
## shows cash available 'cash' to total cash allocated across all accounts for the strategy 'total_cash'
##

class AllocNode(object):
    def __init__(self, account_id):
        self.account_id = account_id 
        self.cash = 0
        self.timestamp = ''

    def to_dict(self):
        m = dict()
        for k, v in self.__dict__.items():
            m.update({k:v})
        return m

    def from_dict(self, json_dict):
        for k, v in json_dict.items():
            self.__dict__.update({k:v})
        return self

    def copy(self):
        new_node = AllocNode(self.account_id)
        new_node.__dict__.update(self.__dict__)
        return new_node

    def stamp_with_time(self):
        now = datetime.now()
        self.timestamp = now.strftime("%Y%m%d-%H:%M:%S")


class Trade(object):
    def __init__(self, trade_id=None ):
        self.trade_id = trade_id
        self.strategy_id = None
        self.side = None
        self.asset = None
        self.units = 0
        self.price = 0
        self.commission = 0
        self.fees = 0 
        self.broker = None
        self.exchange = None
        self.timestamp = None

    def to_dict(self):
        m = dict()
        for k, v in self.__dict__.items():
            m.update({k:v})
        return m

    ## make sure all assigned values are of the correct type
    def __setattr__(self, name, value):
        if name in ['units', 'price', 'commissions', 'fees']:
            value = float(value)
        super.__setattr__(self, name, value)

    def from_dict(self, json_dict):
        for k, v in json_dict.items():
            if k in ['units', 'price', 'commissions', 'fees']: v = float(v)
            self.__dict__.update({k:v})
        return self

    def copy(self):
        new_trade = Trade()
        new_trade.__dict__.update(self.__dict__)
        return new_trade
    
    def convert_timestamp(self, timestamp):
        self.timestamp = timestamp.strftime('%Y%m%d-%H%M%S')

    def stamp_timestamp(self):
        now = datetime.now()
        self.timestamp = now.strftime('%Y%m%d-%H%M%S')
    

class PosMgr(object):
    def __init__(self):
        self.strategy_id = None
        self.universe = None 

        ## current names to trade w/ current positions
        self.positions = []
        ## incremental detail of position changes
        self.position_detail = []  
        ## allocations per account for all the strategy trades
        self.allocations = []
        ## total cash available to initiate new positions
        self.trade_capital = 0
        ## trades
        self.trades = []

    def position_count(self):
        return len(self.positions)

    def get_position(self, symbol):
        for pos_node in self.positions:
            if pos_node.symbol == symbol:
                return pos_node
        return None

    def get_previous_trade_date(self):
        today = datetime.today()
        holidays = calendar_calcs.load_holidays()
        dt = calendar_calcs.prev_trading_day(today, holidays)
        if dt is not None:
            return dt
        return None

    ## validate that the YYYYMMDD tag in the filename is a valid date
    def _validate_file_date(self, filename):
        ## position filename format = <Strategy_id>.positions.<YYYYMMDD>.json
        date_string = filename.split('.')[2]
        try:
            datetime.strptime(date_string, "%Y%m%d")
            return True
        except ValueError:
            return False

    ## read position node file:
    ## position filename format = <Strategy_id>.positions.<YYYYMMDD>.json
    def read_positions_and_allocations(self):

        ## Directory where the files are located
        directory = f'{PORTFOLIO_DIRECTORY}/{self.strategy_id}/positions/' 

        ## Regex pattern to match the file names
        ## position filename format = <Strategy_id>.positions.<YYYYMMDD>.json
        regex_pattern = fr'{self.strategy_id}\.positions\.\d{{8}}\.json' 

        sorted_files = []
        if os.path.exists(directory):
            matching_files = [f for f in os.listdir(directory) if re.match(regex_pattern, f)]
            valid_files = [f for f in matching_files if self._validate_file_date(f)]
            sorted_files = sorted(valid_files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))

        pos_map = dict()
        pos_nodes = []
        alloc_nodes = []
        total_allocation = 0
        if len(sorted_files) > 0:
            most_recent_file = sorted_files[-1]
            print(f'position file: {most_recent_file}')
            file_path = os.path.join(directory, most_recent_file)
            with open(file_path, 'r') as file:
                pos_json = json.load(file)
                
                ## json file expected is as follows:
                ##
                ## {
                ##     'positions': [ array of PosNodes: { name, position, duration, price, timestamp } ],
                ##     'position_detail': [ array of position updates: { name, side, units, old_position, new_position, timestamp } ],
                ##     'allocations:' [ array of AllocNode: { accountId, cash} ]
                ##     'total_allocation': sum of cash allocations 
                ## }
                ##

                ## map all names to position nodes found
                ## return None if 'positions' or 'allocations' not found
                pos_nodes = pos_json.get('positions', [])
                if len(pos_nodes) > 0:
                    for node in pos_nodes:
                        name = node['name']
                        n = PosNode(name).from_dict(node)
                        try:
                            pos_map[name].append(n)
                        except KeyError:
                            pos_map[name] = [n]
                    
                alloc_nodes = pos_json.get('allocations', [])
                total_allocation = pos_json.get('total_allocation',0)

        else:
            print(f'warning: No matching position files found in {directory} for strategy_id: {self.strategy_id}.')

        return pos_map, alloc_nodes, total_allocation

    
    ## recover position detail and trade detail information from
    ## the CURRENT trading day - in situations where there was a program restart
    def recover_current_detail(self):
        today = datetime.today().strftime("%Y%m%d")

        directory = f'{PORTFOLIO_DIRECTORY}/{self.strategy_id}/positions/' 
        pos_file = f'{self.strategy_id}.positions.{today}.json' 

        pos_detail = [] 
        file_path = os.path.join(directory, pos_file)
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                pos_json = json.load(file)
                pos_detail = pos_json.get('position_detail', [])

        directory = f'{PORTFOLIO_DIRECTORY}/{self.strategy_id}/trades/' 
        trade_file = f'{self.strategy_id}.trades.{today}.json' 

        trade_detail = [] 
        file_path = os.path.join(directory, trade_file)
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                trade_json = json.load(file)
                trade_detail = trade_json.get('trades', [])

        return pos_detail, trade_detail


    def _positions_to_df(self):
        if len(self.positions) > 0:
            ## get the attribute names of the first PosNode to use as columns
            cols = self.positions[0].keys()
            df = pandas.DataFrame(columns=cols, data=self.positions)
            return df 

        return None


    def _fetch_cash_allocations(self, strategy_id):

        # Connect to the 'Operations' database
        connection = mysql.connector.connect(
            host="localhost",  # Replace with your MySQL server host
            user="root",  # Replace with your MySQL username
            password="tarzan001",  # Replace with your MySQL password
            database="Operations"
        )

        # Create a cursor to execute SQL queries
        cursor = connection.cursor()

        print(f'alert: fetching new capital available for {self.strategy_id}')

        # Perform the join query
        ## FIX IT - add timestamp to AccountValue table - shows last update and MTM time.
        query = """
            SELECT sa.accountId, av.cash, av.timestamp
            FROM StrategyAccount AS sa
            JOIN AccountValue AS av ON sa.accountId = av.accountId
            WHERE sa.strategyId = %s
        """
        cursor.execute(query, (strategy_id,))

        # Fetch all the results
        results = cursor.fetchall()

        # Print the retrieved data
        if results:
            for row in results:
                account_id, cash, timestamp = row
                print(f"{strategy_id}: accountId: {account_id}, cash: {cash}, timestamp: {timestamp}")
        else:
            print(f"No accounts found for strategyId '{strategy_id}'.")

        # Close the cursor and connection
        cursor.close()
        connection.close()

        total_cash = 0 
        alloc_nodes = []
        for row in results:
            account_id, cash, timestamp = row
            alloc_node = AllocNode(account_id)
            alloc_node.cash = float(cash)
            alloc_node.timestamp = timestamp
            total_cash += float(cash)
            alloc_nodes.append(alloc_node)

        print(f"{strategy_id}: trade_capital: {total_cash}")
        return alloc_nodes, total_cash


    ## master method used to load universe and positions for trading.
    def initialize(self):

        ## give back a map of pos nodes, indexed by names,  
        ## and the allocation breakdown for accounts
        ## and the sum of all allocations
        pos_map, alloc_nodes, total_allocation = self.read_positions_and_allocations()

        ## recover CURRENT day detail in the case of program restart 
        self.position_detail, self.trades = self.recover_current_detail() 

        open_positions = 0 
        newbies= []
        for name in self.universe:
            pos_nodes = pos_map.get(name)
            if pos_nodes is None:
                ## new name to trade in the universe
                new_node = PosNode(name)
                self.positions.append(new_node)
                newbies.append(new_node)
            else:
                items = len(pos_nodes)
                ## add singular position definition
                if items == 1:
                    open_node = pos_nodes[0]
                    self.positions.append(open_node)
                    open_positions += abs(open_node.position)
                else:
                    ## map returned multiple pos nodes for a specific name
                    print(f'warning: duplicate positions found for {name}.')
                    print(json.dumps(pos_nodes, ensure_ascii=False, indent =4 ))
       
        if len(newbies) > 0:
            print(f'created following new position nodes:')
            nn = [ x.to_dict() for x in newbies ]
            print(json.dumps(nn, ensure_ascii=False, indent=4))

        if len(self.positions) > 0:
            print(f'current position nodes:')
            oo = [ x.to_dict() for x in self.positions ]
            print(json.dumps(oo, ensure_ascii=False, indent=4))

            
        ## position names in position file - but not in current universe
        zombies = set(pos_map.keys()).difference(self.universe)
        if len(zombies) > 0:
            print(f'universe loaded = {self.universe}')
            print('warning: zombie positions not in current universe found.')
            zz = []
            for name in zombies:
                zombie_nodes = pos_map.get(name)
                zz.extend(zombie_nodes.to_dict())
            print(json.dumps(zz, ensure_ascii=False, indent =4 ))

        ## check allocations 
        if open_positions != 0:
            self.trade_capital = 0
            print('alert: using previous allocations on open positions')
            if len(alloc_nodes) > 0:
                print(json.dumps(alloc_nodes, ensure_ascii=False, indent=4))
                converted_allocs = []
                for alloc in alloc_nodes:
                    aa= AllocNode(alloc['account_id'])
                    converted_allocs.append(aa.from_dict(alloc))
                alloc_nodes = converted_allocs
                self.trade_capital = total_allocation
            else:
                print('error: no allocations posted for open positions')
        else:
            ## fetch new allocations 
            ## for a clean slate of zero positions 
            alloc_nodes, self.trade_capital = self._fetch_cash_allocations(self.strategy_id)

        self.allocations = alloc_nodes


    def create_directory(self, directory_path):
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)

    def write_positions(self, now):
        def _to_dict(lst):
            f = lambda x: x if isinstance(x,dict) else x.to_dict()
            return [ f(x) for x in lst ]
    
        ## sorts current detail by name, then timestamp
        sorted_detail = sorted(self.position_detail, key=lambda x: (x['name'], x['timestamp']))

        #ts = now.strftime("%Y%m%d-%H%M%S")
        tdy = now.strftime("%Y%m%d")
        newdir =f'{PORTFOLIO_DIRECTORY}/{self.strategy_id}/positions/'
        self.create_directory(newdir)
        position_file = f'{newdir}/{self.strategy_id}.positions.{tdy}.json'
        pp = { 'positions': _to_dict(self.positions), 
               'position_detail': sorted_detail, 
               'allocations': _to_dict(self.allocations),
               'total_allocation': self.trade_capital
             }
        with open(position_file, 'w') as f:
            s = json.dumps(pp, ensure_ascii=False, indent =4 )
            f.write(s + '\n')

        print(f'{position_file} updated')


    def write_trades(self, now):
        def _to_dict(lst):
            f = lambda x: x if isinstance(x,dict) else x.to_dict()
            return [ f(x) for x in lst ]

        ## sorts current by name, then timestamp
        sorted_trades = sorted( _to_dict(self.trades), key=lambda x: (x['asset'], x['timestamp']))

        tdy = now.strftime("%Y%m%d")
        newdir =f'{PORTFOLIO_DIRECTORY}/{self.strategy_id}/trades/'
        self.create_directory(newdir)
        trade_file = f'{newdir}/{self.strategy_id}.trades.{tdy}.json'
        tt = { 'trades': sorted_trades, 'allocations': _to_dict(self.allocations), 'total_allocation': self.trade_capital }
        with open(trade_file, 'w') as f:
            s = json.dumps(tt, ensure_ascii=False, indent =4 )
            f.write(s + '\n')

        print(f'{trade_file} updated')

    def update_positions(self, pos_node, trade_obj):

        def _calc_avg_price(curr_pos, curr_price, new_pos, new_price):
            x = abs(curr_pos)
            y = abs(new_pos)
            return (( x * curr_price ) + ( y* new_price)) / ( x+ y)
        

        new_node = pos_node.copy()
        if pos_node.position > 0:
            if trade_obj.side == TradeSide.BUY:
                new_node.price = _calc_avg_price(pos_node.position, pos_node.price, trade_obj.units, trade_obj.price)
                new_node.position += trade_obj.units
            elif trade_obj.side == TradeSide.SELL:
                new_node.position -= trade_obj.units
                if new_node.position < 0:
                    new_node.price = trade_obj.price
                else:
                    new_node.price = 0
        ## manage short positions 
        elif pos_node.position  < 0:
            if trade_obj.side == TradeSide.SELL:
                new_node.price = _calc_avg_price(pos_node.position, pos_node.price, trade_obj.units, trade_obj.price)
                new_node.position -= trade_obj.units
            elif trade_obj.side == TradeSide.BUY:
                new_node.position += trade_obj.units
                if new_node.position > 0:
                    new_node.price = trade_obj.price
                else:
                    new_node.price = 0
        ## start new position
        elif pos_node.position == 0:
            new_node.position = trade_obj.units if trade_obj.side == TradeSide.BUY else -(trade_obj.units)
            new_node.price = trade_obj.price

        ## update time of new position
        new_node.timestamp = trade_obj.timestamp

        ## record trade that affected the current position
        pos_detail = dict() 
        pos_detail['name'] = new_node.name
        pos_detail['prev_position'] = pos_node.position
        pos_detail['current_position'] = new_node.position
        pos_detail['side'] = trade_obj.side
        pos_detail['units'] = trade_obj.units
        pos_detail['trade_id'] = trade_obj.trade_id
        pos_detail['timestamp'] = trade_obj.timestamp

        return new_node, pos_detail


    ## take a new trade and update positions 
    ## and update position and trade files
    def update_trades(self, trade_object, conversion_func=None):

        def _convert_trade(trade_string):
            ##FIX this
            ##convert trade_string to trade object
            ### fake_trade = '12345, Strategy1, BUY, QQQ, 315, 25.67'
            vals = [ x.strip() for x in trade_string.split(',') ]
            cols = [ 'trade_id', 'strategy_id', 'side', 'asset', 'units', 'price' ]
            t_obj = Trade()
            t_obj.from_dict( dict(zip(cols, vals)) ) 
            t_obj.stamp_timestamp()

            return t_obj

        if conversion_func == None:
            conversion_func = _convert_trade

        trade_obj = conversion_func(trade_object)
        trade_dump = json.dumps(trade_obj.__dict__, ensure_ascii=False, indent=4)

        ## make sure you are not re-processing the same trade
        processed_trade_ids = [ x['trade_id'] for x in self.trades ]
        new_trade = trade_obj.trade_id not in processed_trade_ids 

        if new_trade:
            self.trades.append(trade_obj)
            print(f'captured trade: {trade_dump}')

            ## NOTE: trade_obj.units is ALWAYS > 0

            for idx, pos_node in enumerate(self.positions):
                if pos_node.name == trade_obj.asset:
                    new_node, new_detail = self.update_positions(pos_node, trade_obj) 
                    self.position_detail.append(new_detail)
                    self.positions[idx] = new_node

            now = datetime.now()
            self.write_positions(now)
            self.write_trades(now)
        else:
            print(f'rejecting duplicate trade: {trade_dump}')



if __name__ == "__main__":
    
    pmgr = PosMgr()
    pmgr.initialize('Strategy1', ['AAPL','SPY','QQQ'])


    print(pmgr.positions)

    fake_trade = '12513, Strategy1, BUY, SPY, 50, 419.00'
    pmgr.update_trades(fake_trade)

    #fake_trade = '12511, Strategy1, SELL, SPY, 43, 461.66'
    #pmgr.update_trades(fake_trade)
    #fake_trade = '12511, Strategy1, BUY, SPY, 120, 470.66'
    #pmgr.update_trades(fake_trade)


   


