import subprocess
import json

import vagrant
from keywords.exceptions import ProvisioningError

from libraries.utilities.generate_clusters_from_pool import generate_clusters_from_pool


def generate_cluster_configs_from_vagrant():
    """
    1. Gets the status for a running vagrant vm set.
    2. Uses the host name to look up the ip allocated to each vagrant vm instance
    3. Uses this IP list to build a pool.json file and generate the cluster configurations
    """

    v = vagrant.Vagrant()
    status = v.status()

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
            raise ProvisioningError("Expected at least 2 ip addresses in {}".format(ip_addresses))
        public_ip = ip_addresses[1]
        print("host: {} ip: {}".format(name, public_ip))
        vagrant_ips.append(public_ip)

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
    usage = """usage: generate_cluster_configs_from_vagrant_hosts.py"""
    generate_cluster_configs_from_vagrant()
