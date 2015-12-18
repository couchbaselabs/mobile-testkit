import os
import sys
import ansible.inventory


def hosts_for_tag(tag):
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