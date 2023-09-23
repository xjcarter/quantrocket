import json

with open('order_snapshot.txt', 'r') as f:
    json_data = json.load(f)

json_str = json.dumps(json_data, indent=4)
print(json_str)
