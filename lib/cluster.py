import os

from conf.host_info import get_host_info


class Cluster:
    def __init__(self, ini_file):

        sgs, cbs = get_host_info(ini_file)

        self.sync_gateways = sgs
        self.servers = cbs

