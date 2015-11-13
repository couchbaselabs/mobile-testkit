import requests

import orchestration.syncgatewayactions


class SyncGateway:

    def __init__(self, target):
        self.ip = target["ip"]
        self.url = "http://{}:4984".format(target["ip"])
        self.host_name = target["name"]

    def info(self):
        r = requests.get(self.url)
        r.raise_for_status()
        return r.text

    def stop(self):
        orchestration.syncgatewayactions.stop(self.host_name)

    def start(self, config):
        orchestration.syncgatewayactions.start(self.host_name, config)

    def restart(self, config):
        orchestration.syncgatewayactions.restart(self.host_name, config)

    def __repr__(self):
        return "SyncGateway: {}:{}\n".format(self.host_name, self.ip)
