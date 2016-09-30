import os
import sys

import ansible.inventory
from ansible.parsing.dataloader import DataLoader
from ansible.vars import VariableManager


def hosts_for_tag(cluster_config, tag):

    if not os.path.isfile(cluster_config):
        print("Hostfile does not exist {}".format(cluster_config))
        sys.exit(1)

    variable_manager = VariableManager()
    loader = DataLoader()

    i = ansible.inventory.Inventory(loader=loader, variable_manager=variable_manager, host_list=cluster_config)
    variable_manager.set_inventory(i)

    group = i.get_group(tag)
    if group is None:
        return []
    hosts = group.get_hosts()
    return [host.get_vars() for host in hosts]
