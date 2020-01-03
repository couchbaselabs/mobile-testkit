import subprocess
import json

import vagrant
from keywords.exceptions import ProvisioningError
from optparse import OptionParser
import sys
import os

from libraries.utilities.generate_clusters_from_pool import generate_clusters_from_pool


def check_network_options(private_network, public_network, public_network_ethernet):
    # Check if only one of the options is set, private_network or public_network or public_network_ethernet
    if private_network and (public_network or public_network_ethernet):
        raise ProvisioningError("Invalid private_network and public_network/public_network_ethernet flags")
    elif public_network and (private_network or public_network_ethernet):
        raise ProvisioningError("Invalid public_network and private_network/public_network_ethernet flags")
    elif public_network_ethernet and (public_network or private_network):
        raise ProvisioningError("Invalid public_network_ethernet and public_network/private_network flags")

    # Check if none of the options are set
    if not private_network and not public_network and not public_network_ethernet:
        raise ProvisioningError("Invalid private_network, public_network and public_network_ethernet flags")


def generate_cluster_configs_from_vagrant(private_network, public_network,
                                          public_network_ethernet, ipv6,
                                          x509_certs):
    """
    1. Gets the status for a running vagrant vm set.
    2. Uses the host name to look up the ip allocated to each vagrant vm instance
    3. Uses this IP list to build a pool.json file and generate the cluster configurations
    """

    check_network_options(private_network, public_network, public_network_ethernet)

    cwd = os.getcwd()

    # Change directory to where the appropriate Vagrantfile lives
    if private_network:
        os.chdir("vagrant/private_network")
    elif public_network:
        os.chdir("vagrant/public_network")
    else:
        os.chdir("vagrant/public_network_ethernet")

    v = vagrant.Vagrant()
    status = v.status()

    # Get vagrant ips
    vagrant_ips = []
    print("Getting ip addresses from running vagrant vms ...")
    for stat in status:
        name = stat.name
        # Expected output: '10.0.2.15 192.168.0.61 2605:e000:9092:200:a00:27ff:fe7b:9bbf \r\n'
        # where second ip is the publicly routable ip
        output = subprocess.check_output('vagrant ssh {} -c "hostname -I" | grep -v warning '.format(name), shell=True)
        cleaned_output = output.strip()
        ip_addresses = cleaned_output.split()
        if len(ip_addresses) < 2:
            raise ProvisioningError("Expected at least 2 ip addresses hostname -I result: {}".format(ip_addresses))
        public_ip = ip_addresses[1]
        print(("host: {} ip: {}".format(name, public_ip)))
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
    generate_clusters_from_pool(pool_file, ipv6=ipv6, x509_certs=x509_certs)


if __name__ == "__main__":
    usage = """usage: generate_cluster_configs_from_vagrant_hosts.py
       --private-network

       or

       usage: python generate_cluster_configs_from_vagrant_hosts.py
       --public-network

       or

       usage: python generate_cluster_configs_from_vagrant_hosts.py
       --public-network-ethernet

       or
       usage: python generate_cluster_configs_from_vagrant_hosts.py
       --public-network --ipv6

       or
       python generate_cluster_configs_from_vagrant_hosts.py
       --public-network --x509-certs
       """

    parser = OptionParser(usage=usage)

    parser.add_option("", "--private-network",
                      action="store_true", dest="private_network", default=False,
                      help="Use Vagrant private network (NAT)")

    parser.add_option("", "--public-network",
                      action="store_true", dest="public_network", default=False,
                      help="Use Vagrant public network (Bridged)")

    parser.add_option("", "--public-network-ethernet",
                      action="store_true", dest="public_network_ethernet", default=False,
                      help="Use Vagrant public ethernet network (Bridged)")

    parser.add_option("--ipv6", action="store_true", default=False, help="Generate configs for IPv6")

    parser.add_option("--x509-certs",
                      action="store_true",
                      dest="x509_certs",
                      default=False,
                      help="Enable x509_certs authentication")

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    generate_cluster_configs_from_vagrant(opts.private_network,
                                          opts.public_network,
                                          opts.public_network_ethernet,
                                          opts.ipv6, opts.x509_certs)
