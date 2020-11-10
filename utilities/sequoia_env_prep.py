import argparse
import json


def get_arguments_from_sequoia(parser):
    parser.add_argument("--ssh-user",
                        action="store",
                        default="root",
                        help="ssh-user: the user name used for ansible and key generator to access cbs and sgw")

    parser.add_argument("--cbs-hosts",
                        action="store",
                        help="cbs-hosts: the host ips for cbs")

    parser.add_argument("--sgw-hosts",
                        action="store",
                        help="sgw-hosts: the host ips for sgw")

    return parser.parse_args()


def generate_ansible_cfg(user):
    # Create ansible config
    with open("ansible.cfg", "w") as file:
        file.write("[defaults]\n")
        file.write("remote_user = {}\n".format(user))
        file.write("host_key_checking = False\n")


def generate_pool_json(cbs_hosts, sgw_hosts):
    data = {}
    cbs_host_list = cbs_hosts.split(',')
    sgw_host_list = sgw_hosts.split(',')
    data['ips'] = []
    data['ip_to_node_type'] = {}
    for cbs_host in cbs_host_list:
        data['ips'].append(cbs_host.strip())
        data['ip_to_node_type'][cbs_host.strip()] = "couchbase_servers"
    for sgw_host in sgw_host_list:
        data['ips'].append(sgw_host.strip())
        data['ip_to_node_type'][sgw_host.strip()] = "sync_gateways"

    with open("resources/pool.json", "w") as outfile:
        json.dump(data, outfile)


if __name__ == "__main__":
    # taking arguments from sequoia framework
    parser = argparse.ArgumentParser(description='Sequoia component test for Sync Gateway')
    args = get_arguments_from_sequoia(parser)
    # generate ansible.cfg
    generate_ansible_cfg(args.ssh_user)
    # generate pool.json
    generate_pool_json(args.cbs_hosts, args.sgw_hosts)
