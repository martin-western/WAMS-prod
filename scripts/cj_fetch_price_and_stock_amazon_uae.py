import requests
import json

URL = "0.0.0.0:8028/mws/fetch-price-and-stock-periodically-amazon-uae"

r = requests.post(url=URL, data={}, verify=False)

r = json.loads(r.content)

print(r)

