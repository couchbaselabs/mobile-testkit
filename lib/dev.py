import requests
import json
from contextlib import closing
from lib.cluster import Cluster

db = "db"
endpoint = "http://172.23.122.251:4985"

# cluster = Cluster()
# cluster.reset(config="sync_gateway_default_functional_tests.json")

params = {
    "feed": "continuous"
}

r = requests.get(url="{0}/{1}/_changes".format(endpoint, db), params=params, stream=True)
for line in r.iter_lines():
    # filter out keep-alive new lines
    if line:
        print(json.loads(line))

