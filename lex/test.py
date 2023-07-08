
from enum import Enum

class gg(str, Enum):
    YES = 'YES'
    NO = 'NO'

if gg.YES == 'YES':
    print(gg.YES.value)

