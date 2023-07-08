
import json 
from datetime import datetime
from enum import Enum

##
## state node for each name traded
## all nodes are saved to a state file to be loaded and updated by the trading engine each day
## 1. read the state json file, 
##    -- get all current positions, these would be state_codeged as 'PREOPEN'
##    -- check signals and update state -- state_codeged as 'OPEN' (This is created as a new LexNode to have an audit trail)
##    -- trade Open if necessary
##    -- check position and trade profitablity at Close, and update exit_price and duration as required -- (new LexNode state_codeged as 'CLOSE')
## 

class StateCode(str, Enum):
    PREOPEN = 'PREOPEN'
    OPEN = 'OPEN'
    INTRADAY = 'INTRADAY'
    CLOSE = 'CLOSE'

class LexNode(object):
    def __init__(self, name):
        self.name = name
        self.position = 0
        self.duration = 0
        self.entry_price = 0
        self.exit_price = 0
        self.timestamp = None
        self.state_code = None 

    def to_dict(self):
        m = dict()
        for k, v in self.__dict__.items():
            m.update({k:v})
        return m

    def stamp_with_time(self):
        now = datetime.now()
        self.timestamp = now.strftime("%Y%m%d-%H:%M:%S")


class TradeManager(object):
    def __init__(self, universe_file):
        self.trade_nodes = []  
        self.misfits = []

        ## give back a unique list of nodes, and their names
        nodes, names = self.read_trade_file()
        ## give me a list of unique list of name you wish to trade
        universe = self.read_universe_file(universe_file)
        ## join what you want to trade with nodes
        universe = universe.union(names)

        while len(nodes) > 0:
            node = nodes.pop()
            if node['name'] in universe:
                self.trade_nodes.append(node) 
            elif int(node['position']) != 0:
                self.misfits.append(node)

        if len(self.misfits) > 0:
            print('warning: open positions for names not included in universe.')
            print(json.dumps(misfits, ensure_ascii=False, indent=4))

    def read_trade_file(self, strategy_id):
        import os
        import re

        ## making sure you can't multiple position nodes in the state file
        def _remove_duplicates(trade_nodes):
            seen = set()
            duplicates = []
            good_nodes = []
                    
            for node in trade_nodes:
                name = node['name']
                if name in seen and name not in duplicates:
                    duplicates.append(name)
                else:
                    seen.add(name)
            
            if len(duplicates) > 0:
                bad_nodes = []
                for node in trade_nodes:
                    if node['name'] in duplicates:
                        bad_nodes.append(node)
                    else:
                        good_nodes.append(node)
                print('warning: duplicate trade nodes found.')
                print(json.dumps(bad_nodes, ensure_ascii=False, indent=4)
            else:
                good_nodes = trade_nodes

            return good_nodes, seen


        trade_nodes = []
        node_names = []

        ## Directory where the files are located
        directory = '/path/to/directory'

        ## Regex pattern to match the file names
        ## trade filename format = tstate.STRATID.YYYYMMDD.json
        regex_pattern = r'^tstate.*json$'
        matching_files = [f for f in os.listdir(directory) if re.match(regex_pattern, f)]
        sorted_files = sorted(matching_files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))

        if sorted_files:
            most_recent_file = sorted_files[-1]
            file_path = os.path.join(directory, most_recent_file)
            with open(file_path, 'r') as file:
                trade_nodes = json.load(file)
            trade_nodes, node_names = _remove_duplicates(trade_nodes) 
        else:
            print('No matching files found.')

        return trade_nodes, node_names

    def read_universe_file(self, univ_file):
        universe_list = []
        with open(univ_file, 'r') as f:
            for name in f.readlines():
                self.universe_list.append(name.strip().upper())

        ## make sure you are returning a unique list
        return set(universe_list)




if __name__ == "__main__":

    ## testing object -> dict -> json conversion
    n = LexNode('SPY')
    n.entry_price = 120.11
    n.state_code = StateCode.OPEN

    u = LexNode('UPRO')
    u.entry_price = 88.89 
    u.state_code = StateCode.CLOSE
    u.stamp_with_time()

    h = [ n.to_dict(), u.to_dict() ]

    ## Serializing json 
    with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(h, f, ensure_ascii=False, indent=4)

    ## reading json 
    with open('data.json', 'r') as f:
         json_object = json.load(f)

    print(json_object)
    for node in json_object:
        if node['state_code'] == StateCode.CLOSE: print(node)




