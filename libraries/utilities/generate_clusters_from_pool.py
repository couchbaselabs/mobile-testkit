import json
import os
import sys
import socket

from keywords.utils import log_info
from keywords.utils import log_warn
from keywords.utils import log_error
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


def write_config(config, pool_file, use_docker, sg_windows, sg_accel_windows):

    connection_string = ""
    if use_docker:
        connection_string = "ansible_connection=docker"

    ips, ip_to_node_type = get_hosts(pool_file)
    ip_to_node_type_len = len(ip_to_node_type)
    ip_to_node_type_defined = False

    resource_folder = os.path.dirname(pool_file)

    log_info("ips: {}".format(ips))

    if len(ips) < config.num_machines_required():
        log_warn("WARNING: Skipping config {} since {} machines required, but only {} provided".format(
            config.name,
            config.num_machines_required(),
            len(ips)))
        return

    if ip_to_node_type_len > 0:
        ip_to_node_type_defined = True

    # Check for number of IPs versus number of IPs in ip_to_node_type
    if ip_to_node_type and len(ip_to_node_type) != len(ips):
        raise Exception("Number of IPs in resources/pool:ips and ip_to_node_type do not match. Exiting ...")

    log_info("\nGenerating config: {}".format(config.name))

    ansible_cluster_conf_file = resource_folder + "/cluster_configs/{}".format(config.name)
    cluster_json_file = resource_folder + "/cluster_configs/{}.json".format(config.name)

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
            f.write("ma{} ansible_host={} {}\n".format(count, ip, connection_string))
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
            # Check if the IP is present in the ip_to_node_type

            j = 0
            found = False
            while ip_to_node_type_defined and j < len(ips):
                if ips[j] not in ip_to_node_type:
                    raise Exception("{} not in ip_to_node_type".format(ips[j]))

                if ip_to_node_type[ips[j]] != "couchbase_servers" or ips[j] in cbs_ips_to_remove:
                    # IP is not a cbs or if the cbs is already recorded
                    j += 1
                    continue
                else:
                    found = True
                    break

            # Check if the number of cbs in the ip_to_node_type match the config
            if ip_to_node_type_defined and not found:
                log_warn("WARNING: Skipping config {} since {} couchbase_servers required, but only {} provided".format(
                    config.name,
                    config.num_cbs,
                    len(cbs_ips_to_remove))
                )

                # Sometimes the config file is partially generated, correct sg but invalid cb etc.
                log_warn("WARNING: Removing the partially generated config {}".format(config.name))
                os.unlink(f.name)

                return

            # j is the counter for ip_to_node_type which is invalid if not defined
            if ip_to_node_type_defined:
                ip = ips[j]
            else:
                ip = ips[i]

            f.write("cb{} ansible_host={} {}\n".format(i + 1, ip, connection_string))
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
            # Check if the IP is present in the ip_to_node_type
            j = 0
            found = False

            while ip_to_node_type_defined and j < len(ips):
                if ips[j] not in ip_to_node_type:
                    raise Exception("{} not in ip_to_node_type".format(ips[j]))

                if ip_to_node_type[ips[j]] != "sync_gateways" or ips[j] in sg_ips_to_remove:
                    # IP is not a sg or if the sg is already recorded
                    j += 1
                    continue
                else:
                    found = True
                    break

            # Check if the number of sgs in the ip_to_node_type match the config
            if ip_to_node_type_defined and not found:
                log_warn("WARNING: Skipping config {} since {} sync_gateways required, but only {} provided".format(
                    config.name,
                    config.num_sgs,
                    len(sg_ips_to_remove)))

                # Sometimes the config file is partially generated, correct cbs but invalid sg etc.
                log_warn("WARNING: Removing the partially generated config {}".format(config.name))
                os.unlink(f.name)

                return

            # j is the counter for ip_to_node_type which is invalid if not defined
            if ip_to_node_type_defined:
                ip = ips[j]
            else:
                ip = ips[i]

            f.write("sg{} ansible_host={} {}\n".format(i + 1, ip, connection_string))
            sync_gateways.append({
                "name": "sg{}".format(i + 1),
                "ip": ip
            })
            sg_ips_to_remove.append(ip)

        for sg_ip in sg_ips_to_remove:
            print "REMOVING {} and {} from {}".format(sg_ip, sg_ips_to_remove, ips)
            ips.remove(sg_ip)

        f.write("\n")

        # Write sg_accels
        ac_ips_to_remove = []
        f.write("[sg_accels]\n")
        for i in range(config.num_acs):
            # Check if the IP is present in the ip_to_node_type
            j = 0
            found = False

            while ip_to_node_type_defined and j < len(ips):
                if ips[j] not in ip_to_node_type:
                    raise Exception("{} not in ip_to_node_type".format(ips[j]))

                if ip_to_node_type[ips[j]] != "sg_accels" or ips[j] in ac_ips_to_remove:
                    # IP is not a ac or if the ac is already recorded
                    j += 1
                    continue
                else:
                    found = True
                    break

            # Check if the number of acs in the ip_to_node_type match the config
            if ip_to_node_type_defined and not found:
                log_warn("WARNING: Skipping config {} since {} sg_accels required, but only {} provided".format(
                    config.name,
                    config.num_acs,
                    len(ac_ips_to_remove))
                )

                # Sometimes the config file is partially generated, correct cbs but invalid ac etc.
                log_warn("WARNING: Removing the partially generated config {}".format(config.name))
                os.unlink(f.name)

                return

            # j is the counter for ip_to_node_type which is invalid if not defined
            if ip_to_node_type_defined:
                ip = ips[j]
            else:
                ip = ips[i]

            f.write("ac{} ansible_host={} {}\n".format(i + 1, ip, connection_string))
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
            # Check if the IP is present in the ip_to_node_type
            j = 0
            found = False
            while ip_to_node_type_defined and j < len(ips):
                if ips[j] not in ip_to_node_type:
                    raise Exception("{} not in ip_to_node_type".format(ips[j]))

                if ip_to_node_type[ips[j]] != "load_generators" or ips[j] in lg_ips_to_remove:
                    # IP is not a lg or if the lg is already recorded
                    j += 1
                    continue
                else:
                    found = True
                    break

            # Check if the number of lgs in the ip_to_node_type match the config
            if ip_to_node_type_defined and not found:
                log_warn("WARNING: Skipping config {} since {} load_generators required, but only {} provided".format(
                    config.name,
                    config.num_lgs,
                    len(lg_ips_to_remove))
                )

                # Sometimes the config file is partially generated, correct cbs but invalid lg etc.
                log_warn("WARNING: Removing the partially generated config {}".format(config.name))
                os.unlink(f.name)

                return

            # j is the counter for ip_to_node_type which is invalid if not defined
            if ip_to_node_type_defined:
                ip = ips[j]
            else:
                ip = ips[i]

            f.write("lg{} ansible_host={} {}\n".format(i + 1, ip, connection_string))
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
            # Check if the IP is present in the ip_to_node_type
            j = 0
            found = False
            while ip_to_node_type_defined and j < len(ips):
                if ips[j] not in ip_to_node_type:
                    raise Exception("{} not in ip_to_node_type".format(ips[j]))

                if ip_to_node_type[ips[j]] != "load_balancers" or ips[j] in lb_ips_to_remove:
                    # IP is not a lb or if the lb is already recorded
                    j += 1
                    continue
                else:
                    found = True
                    break

            # Check if the number of lbs in the ip_to_node_type match the config
            if ip_to_node_type_defined and not found:
                log_warn("WARNING: Skipping config {} since {} load_balancers required, but only {} provided".format(
                    config.name,
                    config.num_lbs,
                    len(lb_ips_to_remove))
                )

                # Sometimes the config file is partially generated, correct cbs but invalid lb etc.
                log_warn("WARNING: Removing the partially generated config {}".format(config.name))
                os.unlink(f.name)

                return

            # j is the counter for ip_to_node_type which is invalid if not defined
            if ip_to_node_type_defined:
                ip = ips[j]
            else:
                ip = ips[i]

            f.write("lb{} ansible_host={} {}\n".format(i + 1, ip, connection_string))
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
            # HACK: http://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
            # Connect to Google's public DNS server and get the socketname tuple (<local_ip_address>, <port>)
            # The 'local_ip_address' is the ip of the machine on the LAN. This will be used to run mock server
            # for the web hook tests. It will be exposed on the LAN so that other machines on the LAN can connect to it
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()

            log_info("webhook ip: {}".format(local_ip))
            f.write("tf1 ansible_host={} {}".format(local_ip, connection_string))
        except Exception as e:
            log_error("Failed to find local_ip, webhook tests will fail.  Error: {}".format(e))

        f.write("\n\n[environment]\n")
        f.write("cbs_ssl_enabled=False\n")
        f.write("xattrs_enabled=False\n")

        if sg_windows:
            f.write("\n\n[sync_gateways:vars]\n")
            f.write("ansible_user=FakeUser\n")
            f.write("ansible_password=FakePassword\n")
            f.write("ansible_port=5986\n")
            f.write("ansible_connection=winrm\n")
            f.write("ansible_winrm_server_cert_validation=ignore\n")

        if sg_accel_windows:
            f.write("\n\n[sg_accels:vars]\n")
            f.write("ansible_user=FakeUser\n")
            f.write("ansible_password=FakePassword\n")
            f.write("ansible_port=5986\n")
            f.write("ansible_connection=winrm\n")
            f.write("ansible_winrm_server_cert_validation=ignore\n")

        log_info("Generating {}.json".format(config.name))

        # Write json file consumable by testkit.cluster class
        cluster_dict = {
            "hosts": hosts,
            "couchbase_servers": couchbase_servers,
            "sync_gateways": sync_gateways,
            "sg_accels": accels,
            "load_generators": load_generators,
            "load_balancers": load_balancers,
            "environment": {
                "cbs_ssl_enabled": False,
                "xattrs_enabled": False
            }
        }

        with open(cluster_json_file, "w") as f_json:
            f_json.write(json.dumps(cluster_dict, indent=4))


def get_hosts(pool_file="resources/pool.json"):
    with open(pool_file) as f:
        pool_dict = json.loads(f.read())
        ips = pool_dict["ips"]
        ip_to_node_type = []

        if "ip_to_node_type" in pool_dict:
            ip_to_node_type = pool_dict["ip_to_node_type"]

    # Make sure there are no duplicate endpoints
    if len(ips) != len(set(ips)):
        log_error("Duplicate endpoints found in 'resources/pools'. Make sure they are unique. Exiting ...")
        sys.exit(1)

    return ips, ip_to_node_type


def generate_clusters_from_pool(pool_file, use_docker, sg_windows=False, sg_accel_windows=False):

    cluster_confs = [

        ClusterDef("base_cc", num_sgs=1, num_acs=0, num_cbs=1, num_lgs=0, num_lbs=0),
        ClusterDef("base_di", num_sgs=1, num_acs=1, num_cbs=1, num_lgs=0, num_lbs=0),
        ClusterDef("ci_cc", num_sgs=1, num_acs=0, num_cbs=3, num_lgs=0, num_lbs=0),
        ClusterDef("ci_di", num_sgs=1, num_acs=2, num_cbs=3, num_lgs=0, num_lbs=0),
        ClusterDef("multiple_servers_cc", num_sgs=1, num_acs=0, num_cbs=3, num_lgs=0, num_lbs=0),
        ClusterDef("multiple_servers_di", num_sgs=1, num_acs=1, num_cbs=3, num_lgs=0, num_lbs=0),
        ClusterDef("multiple_sg_accels_di", num_sgs=1, num_acs=3, num_cbs=1, num_lgs=0, num_lbs=0),
        ClusterDef("multiple_sync_gateways_cc", num_sgs=2, num_acs=0, num_cbs=1, num_lgs=0, num_lbs=0),
        ClusterDef("multiple_sync_gateways_di", num_sgs=2, num_acs=1, num_cbs=1, num_lgs=0, num_lbs=0),
        ClusterDef("load_balancer_cc", num_sgs=2, num_acs=0, num_cbs=1, num_lgs=0, num_lbs=1),
        ClusterDef("load_balancer_di", num_sgs=2, num_acs=1, num_cbs=1, num_lgs=0, num_lbs=1),
        ClusterDef("1sg", num_sgs=1, num_acs=0, num_cbs=0, num_lgs=0, num_lbs=0),
        ClusterDef("2sgs", num_sgs=2, num_acs=0, num_cbs=0, num_lgs=0, num_lbs=0),
        ClusterDef("1cbs", num_sgs=0, num_acs=0, num_cbs=1, num_lgs=0, num_lbs=0),
        ClusterDef("1sg_1cbs_1lgs", num_sgs=1, num_acs=0, num_cbs=1, num_lgs=1, num_lbs=0),
        ClusterDef("1sg_1ac_1cbs_1lgs", num_sgs=1, num_acs=1, num_cbs=1, num_lgs=1, num_lbs=0),
        # 1 sync_gateway
        ClusterDef("1sg_1ac_3cbs_1lgs", num_sgs=1, num_acs=1, num_cbs=3, num_lgs=1, num_lbs=0),
        ClusterDef("1sg_2ac_3cbs_1lgs", num_sgs=1, num_acs=2, num_cbs=3, num_lgs=1, num_lbs=0),
        ClusterDef("1sg_3cbs_1lgs", num_sgs=1, num_acs=0, num_cbs=3, num_lgs=1, num_lbs=0),
        # 2 sync_gateways
        ClusterDef("2sg_1cbs_1lgs", num_sgs=2, num_acs=0, num_cbs=1, num_lgs=1, num_lbs=0),
        ClusterDef("2sg_3cbs_2lgs", num_sgs=2, num_acs=0, num_cbs=3, num_lgs=2, num_lbs=0),
        ClusterDef("2sg_6cbs_2lgs", num_sgs=2, num_acs=0, num_cbs=6, num_lgs=2, num_lbs=0),
        ClusterDef("2sg_2ac_3cbs_1lgs", num_sgs=2, num_acs=2, num_cbs=3, num_lgs=1, num_lbs=0),
        ClusterDef("2sg_2ac_3cbs_2lgs", num_sgs=2, num_acs=2, num_cbs=3, num_lgs=2, num_lbs=0),
        ClusterDef("2sg_2ac_6cbs_2lgs", num_sgs=2, num_acs=2, num_cbs=6, num_lgs=2, num_lbs=0),
        ClusterDef("2sg_4ac_3cbs_2lgs", num_sgs=2, num_acs=4, num_cbs=3, num_lgs=2, num_lbs=0),
        ClusterDef("2sg_8ac_3cbs_2lgs", num_sgs=2, num_acs=8, num_cbs=3, num_lgs=2, num_lbs=0),
        ClusterDef("2sg_2ac_6cbs_2lgs", num_sgs=2, num_acs=2, num_cbs=6, num_lgs=2, num_lbs=0),
        ClusterDef("2sg_8ac_6cbs_2lgs", num_sgs=2, num_acs=8, num_cbs=6, num_lgs=2, num_lbs=0),
        # 4 sync_gateways
        ClusterDef("4sg_2ac_3cbs_4lgs", num_sgs=4, num_acs=2, num_cbs=3, num_lgs=4, num_lbs=0),
        ClusterDef("4sg_2ac_6cbs_4lgs", num_sgs=4, num_acs=2, num_cbs=6, num_lgs=4, num_lbs=0),
        ClusterDef("4sg_4ac_3cbs_4lgs", num_sgs=4, num_acs=4, num_cbs=3, num_lgs=4, num_lbs=0),
        ClusterDef("4sg_4ac_6cbs_4lgs", num_sgs=4, num_acs=4, num_cbs=6, num_lgs=4, num_lbs=0),
        ClusterDef("4sg_8ac_3cbs_4lgs", num_sgs=4, num_acs=8, num_cbs=3, num_lgs=4, num_lbs=0),
        ClusterDef("4sg_8ac_6cbs_4lgs", num_sgs=4, num_acs=8, num_cbs=6, num_lgs=4, num_lbs=0),
        # 8 sync_gateways
        ClusterDef("8sg_4ac_3cbs_8lgs", num_sgs=8, num_acs=4, num_cbs=3, num_lgs=8, num_lbs=0),
        ClusterDef("8sg_4ac_6cbs_8lgs", num_sgs=8, num_acs=4, num_cbs=6, num_lgs=8, num_lbs=0),
        ClusterDef("8sg_4ac_12cbs_8lgs", num_sgs=8, num_acs=4, num_cbs=12, num_lgs=8, num_lbs=0),
        ClusterDef("8sg_8ac_3cbs_8lgs", num_sgs=8, num_acs=8, num_cbs=3, num_lgs=8, num_lbs=0),
        ClusterDef("8sg_8ac_6cbs_8lgs", num_sgs=8, num_acs=8, num_cbs=6, num_lgs=8, num_lbs=0),
        ClusterDef("8sg_12ac_3cbs_8lgs", num_sgs=8, num_acs=12, num_cbs=3, num_lgs=8, num_lbs=0),
        # 12 sync_gateways
        ClusterDef("12sg_4ac_6cbs_12lgs", num_sgs=12, num_acs=4, num_cbs=6, num_lgs=12, num_lbs=0),
        ClusterDef("12sg_4ac_12cbs_12lgs", num_sgs=12, num_acs=4, num_cbs=12, num_lgs=12, num_lbs=0),
        ClusterDef("12sg_8ac_6cbs_12lgs", num_sgs=12, num_acs=8, num_cbs=6, num_lgs=12, num_lbs=0),
        ClusterDef("12sg_8ac_12cbs_12lgs", num_sgs=12, num_acs=8, num_cbs=12, num_lgs=12, num_lbs=0),
        # 16 sync_gateways
        ClusterDef("16sg_4ac_3cbs_16lgs", num_sgs=16, num_acs=4, num_cbs=3, num_lgs=16, num_lbs=0),
        ClusterDef("16sg_4ac_6cbs_16lgs", num_sgs=16, num_acs=4, num_cbs=6, num_lgs=16, num_lbs=0),
        ClusterDef("16sg_4ac_12cbs_16lgs", num_sgs=16, num_acs=4, num_cbs=12, num_lgs=16, num_lbs=0),
        ClusterDef("16sg_8ac_3cbs_16lgs", num_sgs=16, num_acs=8, num_cbs=3, num_lgs=16, num_lbs=0),
        ClusterDef("16sg_8ac_6cbs_16lgs", num_sgs=16, num_acs=8, num_cbs=6, num_lgs=16, num_lbs=0),
        ClusterDef("16sg_8ac_12cbs_16lgs", num_sgs=16, num_acs=8, num_cbs=12, num_lgs=16, num_lbs=0),
        # End Perf Mini Matrix

        # Test Fest
        ClusterDef("1sg_2ac_3cbs", num_sgs=1, num_acs=2, num_cbs=3, num_lgs=0, num_lbs=0)
        # End Test Fest
    ]

    if not os.path.isfile(pool_file):
        print("Pool file not found in 'resources/'. Please modify the example to include your machines.")
        sys.exit(1)

    print("Using the following machines to run functional tests ... ")
    for host in get_hosts(pool_file):
        print(host)

    print("Generating 'resources/cluster_configs/'. Using docker: {}".format(use_docker))
    for cluster_conf in cluster_confs:
        write_config(cluster_conf, pool_file, use_docker, sg_windows, sg_accel_windows)


if __name__ == "__main__":
    usage = """
    usage:
    python generate_clusters_from_pool.py or
    python generate_clusters_from_pool.py --use-docker
    """

    parser = OptionParser(usage=usage)

    parser.add_option("", "--pool-file",
                      action="store", type="string", dest="pool_file", default="resources/pool.json",
                      help="path to pool.json file")

    parser.add_option("-d", "--use-docker", action="store_true", dest="use_docker", default=False, help="Use docker connection with ansible")

    parser.add_option("--sg-windows", action="store_true", dest="sg_windows", default=False, help="Use Windows Sync Gateway")

    parser.add_option("--sg-accel-windows", action="store_true", dest="sg_accel_windows", default=False, help="Use Windows Sync Gateway Accelerator")

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    generate_clusters_from_pool(opts.pool_file, opts.use_docker, opts.sg_windows, opts.sg_accel_windows)
