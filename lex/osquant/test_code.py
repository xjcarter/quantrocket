import requests
import json

contract_id = 265598
ibportal = '127.0.0.1'
url = f"https://{ibportal}:5000/v1/api/iserver/contract/{contract_id}/info"

# We need to disable SSL verification to use the API
session = requests.Session()
session.verify = False
        
#r = session.get(url).json()
#print(r)

## contract details
#data = session.get(f'https://{ibportal}:5000/v1/api/trsrv/stocks?symbols=AAPL')
data = session.get(f'https://{ibportal}:5000/v1/api/trsrv/stocks', params={'symbols': 'AAPL'})
print(json.dumps(data.json(), ensure_ascii=False, indent =4 ))

print ('\nAccount Info')

data = session.get(f'https://{ibportal}:5000/v1/api/iserver/accounts')
print(json.dumps(data.json(), ensure_ascii=False, indent =4 ))

##data snapshot
