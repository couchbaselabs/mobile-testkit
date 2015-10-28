import os
from prov.reset_sync_gateway import reset_sync_gateway

from conf.host_info import get_host_info


class Cluster:
    def __init__(self, ini_file):

        sgs, cbs = get_host_info(ini_file)

        self.sync_gateways = sgs
        self.servers = cbs

    def reset(self):
        reset_sync_gateway()


