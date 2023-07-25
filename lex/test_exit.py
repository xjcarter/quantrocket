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

from posmgr import PosMgr, TradeSide, Trade


MAX_HOLD_PERIOD = 3 


def check_exit(position_node, stdv):

    current_pos, entry_price = position_node.position, position_node.price
    duration = position_node.duration
    #current_price = get_current_price(position_node.name)
    current_price = test_harness.get_current_price(position_node.name)

    get_out = False
    alert = 'NO_EXIT'
    if current_pos > 0:
        if current_price > entry_price:
            alert = 'PNL'
            get_out = True
        elif duration > MAX_HOLD_PERIOD:
            alert = 'EXPIRY'
            get_out = True
        elif (entry_price - current_price) > stdv * 2:
            alert = 'STOP ON CLOSE'
            get_out = True

    logger.info(f'check_exit: exit= {get_out}, {position_node.name}, {current_pos}')
    logger.info(f'exit_details: {position_node.name}, alert= {alert} current_price= {current_price}, entry= {entry_price}, duration= {duration}')
    return get_out, current_pos

pmgr = PosMgr()
pmgr.initialize('Strategy1', ['SPY'])

pos_node = pmgr.get_position('SPY')
test_harness.override_price = pos_node.price
test_harness.override_price_skew = 1.50
check_exit(pos_node, stdv=0.5)




