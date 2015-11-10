from lib.syncgateway import SyncGateway
from conf.ini_to_ansible_host import ini_to_ansible_host
from orchestration import clusteractions


class Cluster:

    def __init__(self, ini_file):

        sgs, cbs, lds = ini_to_ansible_host(ini_file)

        self.sync_gateways = [SyncGateway(sg) for sg in sgs]
        self.servers = cbs

    def reset(self, config):
        clusteractions.reset(config)






