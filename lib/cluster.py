
from conf.host_info import get_host_info

from prov.reset_sync_gateway import reset_sync_gateway

from lib.syncgateway import SyncGateway


class Cluster:
    def __init__(self, ini_file):

        sgs, cbs = get_host_info(ini_file)

        self.sync_gateways = [SyncGateway(sg) for sg in sgs]
        self.servers = cbs

    def reset(self):
        reset_sync_gateway()


