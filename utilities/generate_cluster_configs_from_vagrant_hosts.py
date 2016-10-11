import subprocess
import json

import vagrant
from keywords.exceptions import ProvisioningError
from optparse import OptionParser
import sys
import os

from libraries.utilities.generate_clusters_from_pool import generate_clusters_from_pool


def generate_cluster_configs_from_vagrant(private_network, public_network):
    """
    1. Gets the status for a running vagrant vm set.
    2. Uses the host name to look up the ip allocated to each vagrant vm instance
    3. Uses this IP list to build a pool.json file and generate the cluster configurations
    """

    if private_network and public_network:
        raise ProvisioningError("Invalid private_network and public_network flags")

    if not private_network and not public_network:
        raise ProvisioningError("Invalid private_network and public_network flags")

    v = vagrant.Vagrant()
    status = v.status()
    cwd = os.getcwd()

    # Change directory to where the appropriate Vagrantfile lives
    if private_network:
        os.chdir("vagrant/private_network")
    else:
        os.chdir("vagrant/public_network")

    # Get vagrant ips
    vagrant_ips = []
    print("Getting ip addresses from running vagrant vms ...")
    for stat in status:
        name = stat.name
        # Expected output: '10.0.2.15 192.168.0.61 2605:e000:9092:200:a00:27ff:fe7b:9bbf \r\n'
        # where second ip is the publicly routable ip
        output = subprocess.check_output('vagrant ssh {} -c "hostname -I"'.format(name), shell=True)
        cleaned_output = output.strip()
        ip_addresses = cleaned_output.split()
        if len(ip_addresses) < 2:
            raise ProvisioningError("Expected at least 2 ip addresses hostname -I result: {}".format(ip_addresses))
        public_ip = ip_addresses[1]
        print("host: {} ip: {}".format(name, public_ip))
        vagrant_ips.append(public_ip)

    # Restore previous directory
    os.chdir(cwd)

    # Write pool.json
    pool_file = "resources/pool.json"
    pool_def = {"ips": vagrant_ips}
    with open(pool_file, "w") as f:
        print("Writing 'resources/pool.json' ...")
        f.write(json.dumps(pool_def, indent=4))

    # Generate cluster configs
    print("Generating cluster_configs ...")
    generate_clusters_from_pool(pool_file)



if __name__ == "__main__":
    usage = """usage: generate_cluster_configs_from_vagrant_hosts.py
       --private-network

       or

       usage: python generate_cluster_configs_from_vagrant_hosts.py
       --public-network
       """

    parser = OptionParser(usage=usage)

    parser.add_option("", "--private-network",
                      action="store_true", dest="private_network", default=False,
                      help="Use Vagrant private network (NAT)")

    parser.add_option("", "--public-network",
                      action="store_true", dest="public_network", default=False,
                      help="Use Vagrant public network (Bridged)")

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    generate_cluster_configs_from_vagrant(opts.private_network, opts.public_network)
