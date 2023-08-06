
import json

class Strategy(object):

    def __init__(self, strategy_id, configuration_file):
        self.strategy_id = strategy_id
        self.pos_mgr = None
        self.price_mgr = None
        self.cfg = self._read_config(configuration_file)

    def _read_config(self, filename):
        cfg = None
        fn = f'{filename}/{self.strategy_id}.json'
        with open(fn, 'r') as file:
            cfg = json.load(file)

        return cfg

