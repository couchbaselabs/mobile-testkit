import os

from conf.ini_to_ansible_host import ini_to_ansible_host


class Cluster:
    def __init__(self, ini_file):

        sgs, cbs = ini_to_ansible_host(ini_file)

        self.sync_gateways = sgs
        self.servers = cbs


