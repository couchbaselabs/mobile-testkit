import json
import os
import sys
import socket


class ClusterDef:
    def __init__(self, name, num_sgs, num_acs, num_cbs, num_lgs):
        self.name = name
        self.num_sgs = num_sgs
        self.num_acs = num_acs
        self.num_cbs = num_cbs
        self.num_lgs = num_lgs


def write_config(config):

    ips = get_ips()

    with open("resources/cluster_configs/{}".format(config.name), "w") as f:

        f.write("[couchbase_servers]\n")
        for i in range(config.num_cbs):
            ip = ips[i]
            f.write("{}\n".format(ip))
            ips.remove(ip)

        f.write("\n")

        # TODO Currently kind of hackish. Will be clean when clean up of sync_gateway_writer defs happen
        f.write("[sync_gateways]\n")
        sg_ips = []
        for i in range(config.num_sgs + config.num_acs):
            ip = ips[i]
            sg_ips.append(ip)
            f.write("{}\n".format(ip))
            ips.remove(ip)

        f.write("\n")

        f.write("[sync_gateway_index_writers]\n")
        for i in range(config.num_acs):
            f.writelines("{}\n".format(sg_ips[i]))

        f.write("\n")

        # Get local address to run webhook server on
        f.write("[webhook_ip]\n")
        local_ip = socket.gethostbyname(socket.gethostname())
        f.write(local_ip)


def get_ips():
    with open(pool_file) as f:
        pool_dict = json.loads(f.read())
        ips = pool_dict["ips"]
    return ips

if __name__ == "__main__":
    usage = """
    usage: python generate_cluster_from_pool.py"
    """

    min_num_machines = 6
    pool_file = "resources/pool.json"

    cluster_configs = [
        ClusterDef("1sg_1cbs",      num_sgs=1, num_acs=0, num_cbs=1, num_lgs=0),
        ClusterDef("1sg_1ac_1cbs",  num_sgs=1, num_acs=1, num_cbs=1, num_lgs=0),
        ClusterDef("1sg_2ac_1cbs",  num_sgs=1, num_acs=2, num_cbs=1, num_lgs=0),
        ClusterDef("2sg_1cbs",      num_sgs=2, num_acs=0, num_cbs=1, num_lgs=0),
    ]

    if not os.path.isfile(pool_file):
        print("Pool file not found in 'resources/'. Please modify the example to include your machines.")
        sys.exit(1)

    if len(get_ips()) < min_num_machines:
        print("You are required to have {} machines defined to be able to run the full suite.".format(min_num_machines))
        sys.exit(1)

    print("Using the following machines to run functional tests ... ")
    for host in get_ips():
        print(host)

    print("Generating 'resources/cluster_configs/'")
    for cluster_config in cluster_configs:
        write_config(cluster_config)

