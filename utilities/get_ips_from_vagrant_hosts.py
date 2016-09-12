import subprocess
import json

import vagrant

from libraries.utilities.generate_clusters_from_pool import generate_clusters_from_pool

def generate_cluster_configs_from_vagrant():
    """
    1. Gets the status for a running vagrant vm set.
    2. Uses the host name to look up the ip allocated to each vagrant vm instance
    3. Uses this IP list to build a pool.json file and generate the cluster configurations
    """

    v = vagrant.Vagrant()
    status = v.status()

    vagrant_ips = []
    print("Getting ip addresses from running vagrant vms ...")
    for stat in status:
        name = stat.name
        output = subprocess.check_output('vagrant ssh {} -c "hostname -I | cut -d\' \' -f2" 2> /dev/null'.format(name), shell=True)
        cleaned_output = output.strip()
        print("host: {} ip: {}".format(name, cleaned_output))
        vagrant_ips.append(cleaned_output)

    pool_file = "resources/pool.json"
    pool_def = {"ips": vagrant_ips}
    with open(pool_file, "w") as f:
        print("Writing 'resources/pool.json' ...")
        f.write(json.dumps(pool_def, indent=4))

    print("Generating cluster_configs ...")
    generate_clusters_from_pool(pool_file)

if __name__ == "__main__":
    usage = """usage: generate_cluster_configs_from_vagrant.py"""
    generate_cluster_configs_from_vagrant()
