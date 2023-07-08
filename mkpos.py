
from posmgr import PosNode

a = PosNode('TECL')
a.position = 100
a.duration = 1
a.entry_price = 100
a.stamp_with_time()


b = PosNode('SPY')
b.position = 200
b.duration = 3
b.entry_price = 99.50 
b.stamp_with_time()


c = PosNode('UPRO')
c.position = 75 
c.duration = 3
c.entry_price = 35.25 
c.stamp_with_time()

g = [a,b,c]
g = [x.to_dict() for x in g]

import json
with open('posfile.json', 'w') as f:
    json.dump(g,f,ensure_ascii=False,indent=4)

