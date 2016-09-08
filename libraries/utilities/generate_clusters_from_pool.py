import json
import os
import platform
import sys
import socket
import netifaces
from optparse import OptionParser


class ClusterDef:
    def __init__(self, name, num_sgs, num_acs, num_cbs, num_lgs, num_lbs):
        self.name = name
        self.num_sgs = num_sgs
        self.num_acs = num_acs
        self.num_cbs = num_cbs
        self.num_lgs = num_lgs
        self.num_lbs = num_lbs


    def num_machines_required(self):
        return (
            self.num_sgs +
            self.num_acs +
            self.num_cbs +
            self.num_lgs +
            self.num_lbs
        )


def write_config(config, pool_file):
    ips = get_ips(pool_file)
    print("ips: {}".format(ips))

    if len(ips) < config.num_machines_required():
        print("WARNING: Skipping config {} since {} machines required, but only {} provided".format(
            config.name,
            config.num_machines_required(),
            len(ips))
        )
        return

    print("\nGenerating config: {}".format(config.name))

    ansible_cluster_conf_file = "resources/cluster_configs/{}".format(config.name)
    cluster_json_file = "resources/cluster_configs/{}.json".format(config.name)

    with open(ansible_cluster_conf_file, "w") as f:

        hosts = []
        couchbase_servers = []
        sync_gateways = []
        accels = []
        load_generators = []
        load_balancers = []

        f.write("[pool]\n")
        count = 1
        for ip in ips:
            f.write("ma{} ansible_host={}\n".format(count, ip))
            hosts.append({
                "name": "host{}".format(count),
                "ip": ip
            })
            count += 1

        f.write("\n")
        f.write("\n")

        # Write Servers
        cbs_ips_to_remove = []
        f.write("[couchbase_servers]\n")
        for i in range(config.num_cbs):
            ip = ips[i]
            f.write("cb{} ansible_host={}\n".format(i + 1, ip))
            couchbase_servers.append({
                "name": "cb{}".format(i + 1),
                "ip": ip
            })
            cbs_ips_to_remove.append(ip)

        for cbs_ip in cbs_ips_to_remove:
            ips.remove(cbs_ip)

        f.write("\n")

        # Write sync_gateways
        f.write("[sync_gateways]\n")
        sg_ips_to_remove = []
        for i in range(config.num_sgs):
            ip = ips[i]
            f.write("sg{} ansible_host={}\n".format(i + 1, ip))
            sync_gateways.append({
                "name": "sg{}".format(i + 1),
                "ip": ip
            })
            sg_ips_to_remove.append(ip)

        for sg_ip in sg_ips_to_remove:
            ips.remove(sg_ip)

        f.write("\n")

        # Write sg_accels
        ac_ips_to_remove = []
        f.write("[sg_accels]\n")
        for i in range(config.num_acs):
            ip = ips[i]
            f.write("ac{} ansible_host={}\n".format(i + 1, ip))
            accels.append({
                "name": "ac{}".format(i + 1),
                "ip": ip
            })
            ac_ips_to_remove.append(ip)

        for ac_ip in ac_ips_to_remove:
            ips.remove(ac_ip)

        f.write("\n")

        # Write load generators
        lg_ips_to_remove = []
        f.write("[load_generators]\n")
        for i in range(config.num_lgs):
            ip = ips[i]
            f.write("lg{} ansible_host={}\n".format(i + 1, ip))
            load_generators.append({
                "name": "lg{}".format(i + 1),
                "ip": ip
            })
            lg_ips_to_remove.append(ip)

        for lg_ip in lg_ips_to_remove:
            ips.remove(lg_ip)

        f.write("\n")

        # Write load balancers
        lb_ips_to_remove = []
        f.write("[load_balancers]\n")
        for i in range(config.num_lbs):
            ip = ips[i]
            f.write("lb{} ansible_host={}\n".format(i + 1, ip))
            load_balancers.append({
                "name": "lb{}".format(i + 1),
                "ip": ip
            })
            lb_ips_to_remove.append(ip)

        for lb_ip in lb_ips_to_remove:
            ips.remove(lb_ip)

        f.write("\n")

        # Get local address to run webhook server on
        # TODO: make the webhook receiver it's own endpoint, or come up w/ better design.
        try:
            f.write("[webhook_ip]\n")
            if platform.system() == "Darwin":
                local_ip = socket.gethostbyname(socket.gethostname())
            elif platform.system() == "Linux":
                local_ip = netifaces.ifaddresses("eth1")[2][0]["addr"]
            else:
                local_ip = netifaces.ifaddresses("eth0")[2][0]["addr"]
            print("webhook ip: {}".format(local_ip))
            f.write("tf1 ansible_host={}".format(local_ip))
        except Exception as e:
            print "Failed to find local_ip, webhook tests will fail.  Error: {}".format(e)

        print("Generating {}.json".format(config.name))

        # Write json file consumable by testkit.cluster class
        cluster_dict = {
            "hosts": hosts,
            "couchbase_servers": couchbase_servers,
            "sync_gateways": sync_gateways,
            "sg_accels": accels,
            "load_generators": load_generators,
            "load_balancers": load_balancers
        }

        with open(cluster_json_file, "w") as f_json:
            f_json.write(json.dumps(cluster_dict, indent=4))


def get_ips(pool_file="resources/pool.json"):
    with open(pool_file) as f:
        pool_dict = json.loads(f.read())
        ips = pool_dict["ips"]

    # Make sure there are no duplicate endpoints
    if len(ips) != len(set(ips)):
        print("Duplicate endpoints found in 'resources/pools'. Make sure they are unique. Exiting ...")
        sys.exit(1)

    return ips

if __name__ == "__main__":
    usage = """
    usage: python generate_cluster_from_pool.py"
    """

    parser = OptionParser(usage=usage)

    parser.add_option("", "--pool-file",
                      action="store", type="string", dest="pool_file", default="resources/pool.json",
                      help="path to pool.json file")

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    cluster_configs = [
        ClusterDef("1sg",               num_sgs=1, num_acs=0, num_cbs=0, num_lgs=0, num_lbs=0),
        ClusterDef("2sgs",              num_sgs=2, num_acs=0, num_cbs=0, num_lgs=0, num_lbs=0),
        ClusterDef("1cbs",              num_sgs=0, num_acs=0, num_cbs=1, num_lgs=0, num_lbs=0),
        ClusterDef("1sg_1cbs",          num_sgs=1, num_acs=0, num_cbs=1, num_lgs=0, num_lbs=0),
        ClusterDef("1sg_1ac_1cbs",      num_sgs=1, num_acs=1, num_cbs=1, num_lgs=0, num_lbs=0),
        ClusterDef("1sg_2ac_1cbs",      num_sgs=1, num_acs=2, num_cbs=1, num_lgs=0, num_lbs=0),
        ClusterDef("2sg_1cbs",          num_sgs=2, num_acs=0, num_cbs=1, num_lgs=0, num_lbs=0),
        ClusterDef("2sg_1cbs_1lbs",     num_sgs=2, num_acs=0, num_cbs=1, num_lgs=0, num_lbs=1),
        ClusterDef("2sg_3cbs_2lgs",     num_sgs=2, num_acs=0, num_cbs=3, num_lgs=2, num_lbs=0),
        ClusterDef("2sg_2ac_3cbs_2lgs", num_sgs=2, num_acs=2, num_cbs=3, num_lgs=2, num_lbs=0),
    ]

    if not os.path.isfile(opts.pool_file):
        print("Pool file not found in 'resources/'. Please modify the example to include your machines.")
        sys.exit(1)


    print("Using the following machines to run functional tests ... ")
    for host in get_ips(opts.pool_file):
        print(host)

    print("Generating 'resources/cluster_configs/'")
    for cluster_config in cluster_configs:
        write_config(cluster_config, opts.pool_file)

