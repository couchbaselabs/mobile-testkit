import os
import sys

import ansible.inventory
from ansible.parsing.dataloader import DataLoader
from ansible.vars import VariableManager


def hosts_for_tag(tag):

    hostfile = os.environ["CLUSTER_CONFIG"]

    if not os.path.isfile(hostfile):
        print("File 'provisioning_config' not found at {}".format(os.getcwd()))
        sys.exit(1)

    variable_manager = VariableManager()
    loader = DataLoader()
    i = ansible.inventory.Inventory(loader=loader, variable_manager=variable_manager, host_list=hostfile)

    group = i.get_group(tag)
    if group is None:
        return []
    hosts = group.get_hosts()
    return [host.get_vars() for host in hosts]