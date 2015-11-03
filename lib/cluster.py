from lib.syncgateway import SyncGateway
from conf.host_info import get_host_info
from orch import clusteractions


class Cluster:

    def __init__(self, ini_file):

        sgs, cbs = get_host_info(ini_file)

        self.sync_gateways = [SyncGateway(sg) for sg in sgs]
        self.servers = cbs

    def reset(self, config):
        clusteractions.reset(config)






