import sys
import os.path
import ansible.inventory

from lib.syncgateway import SyncGateway
from orchestration import clusteractions




class Cluster:

    def __init__(self):

        # get hosts
        cbs_host_vars = self._hosts_for_tag("couchbase_servers")
        sgs_host_vars = self._hosts_for_tag("sync_gateways")
        sgsw_host_vars = self._hosts_for_tag("sync_gateway_index_writers")
        lds_host_vars = self._hosts_for_tag("load_generators")

        # provide simple consumable dictionaries to functional framwork
        cbs = [{"name": cbsv["inventory_hostname"], "ip": cbsv["ansible_ssh_host"]} for cbsv in cbs_host_vars]
        sgs = [{"name": sgv["inventory_hostname"], "ip": sgv["ansible_ssh_host"]} for sgv in sgs_host_vars]
        sgsw = [{"name": sgwv["inventory_hostname"], "ip": sgwv["ansible_ssh_host"]} for sgwv in sgsw_host_vars]
        lds = [{"name": ldv["inventory_hostname"], "ip": ldv["ansible_ssh_host"]} for ldv in lds_host_vars]

        self.sync_gateways = [SyncGateway(sg) for sg in sgs]
        self.sync_gateway_writers = [SyncGateway(sgw) for sgw in sgsw]
        self.servers = cbs
        self.load_generators = lds

    def _hosts_for_tag(self, tag):
        hostfile = "provisioning_config"

        if not os.path.isfile(hostfile):
            print("File 'provisioning_config' not found at {}".format(os.getcwd()))
            sys.exit(1)

        i = ansible.inventory.Inventory(host_list=hostfile)
        group = i.get_group(tag)
        if group is None:
            return []
        hosts = group.get_hosts()
        return [host.get_variables() for host in hosts]

    def reset(self, config):
        clusteractions.reset(config)

    def __repr__(self):
        s = "\n\n"
        s += "Sync Gateways\n"
        for sg in self.sync_gateways:
            s += str(sg)
        s += "Sync Gateway Writers\n"
        for sgw in self.sync_gateway_writers:
            s += str(sgw)
        s += "Couchbase Servers\n"
        for server in self.servers:
            s += str(server)
        s += "Load Generators\n"
        for lg in self.load_generators:
            s += str(lg)
        s += "\n"
        return s







