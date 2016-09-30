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


def get_host_ips(cluster_conf):

    ips = []
    cbs_vars = hosts_for_tag(cluster_conf, "couchbase_servers")
    sg_vars = hosts_for_tag(cluster_conf, "sync_gateways")
    lg_vars = hosts_for_tag(cluster_conf, "load_generators")
    sgw_vars = hosts_for_tag(cluster_conf, "sync_gateway_index_writers")

    ips.extend([cbs_var["ansible_host"] for cbs_var in cbs_vars])
    ips.extend([sg_var["ansible_host"] for sg_var in sg_vars])
    ips.extend([lg_var["ansible_host"] for lg_var in lg_vars])
    ips.extend([sgw_var["ansible_host"] for sgw_var in sgw_vars])

    # Ips may be used for multiple purposes
    return set(ips)
