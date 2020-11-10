import argparse
import json
import os

if __name__ == "__main__":
    
    # taking arguments from sequoia framework
    parser = argparse.ArgumentParser(description='Sequoia component test for Sync Gateway')
    args = get_arguments_from_sequoia(parser)
    # generate ansible.cfg
    generate_ansible_cfg(args["ssh_user"])
    # generate pool.json
    generate_pool_json(args["cbs_hosts"], args["sgw_hosts"])


def get_arguments_from_sequoia(parser):
    parser.addoption("--ssh-user",
                      action="store",
                      default="root",
                      help="ssh-user: the user name used for ansible and key generator to access cbs and sgw")

    parser.addoption("--cbs-hosts",
                      action="store",
                      help="cbs-hosts: the host ips for cbs")

    parser.addoption("--sgw-hosts",
                      action="store",
                      help="sgw-hosts: the host ips for sgw")

    return parser.parse_args()


def generate_ansible_cfg(user):
    # Create ansible config
    with open("ansible.cfg", "w") as file:
        file.write("[defaults]")
        file.write("remote_user = {}".format(user))
        file.write("host_key_checking = False")


def generate_pool_json(cbs_hosts, sgw_hosts):
    data = {}
    cbs_host_list = cbs_hosts.split(',').trim()
    sgw_host_list = sgw_hosts.split(',').trim()
    data['ips'] = []
    data['ip_to_node_type'] =[]
    for cbs_host in cbs_hosts:
        data['ips'].append(cbs_host)
        data['ip_to_node_type'].append({cbs_host: "couchbase_servers"})
    for sgw_host in sgw_hosts:
        data['ips'].append(sgw_host)
        data['ip_to_node_type'].append({sgw_host: "sync_gateways"})
    
    with open("resources/pool.json", "w") as outfile:
        json.dump(data, outfile)
