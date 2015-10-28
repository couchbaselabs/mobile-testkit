import requests
import json

import orch.syncgatewayactions

# Server
# GET /
# POST db/_session
# DELETE db/_session

class SyncGateway:

    def __init__(self, target):
        self.ip = target["ip"]
        self.url = "http://{}:4984".format(target["ip"])
        self.host_name = target["name"]

    def info(self):
        return requests.get(self.url)

    def stop(self):
        orch.syncgatewayactions.stop(self.host_name)

    def start(self):
        orch.syncgatewayactions.start(self.host_name)
