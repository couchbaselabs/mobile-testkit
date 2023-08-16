import json
import logging
import sys
import yaml
import getopt


def get_hosts(pool_file):
    with open(pool_file) as f:
        pool_dict = json.loads(f.read())
        ips = pool_dict["ips"]

    # Make sure there are no duplicate endpoints
    if len(ips) != len(set(ips)):
        logging.error("Duplicate endpoints found in 'resources/pools'. Make sure they are unique. Exiting ...")
        sys.exit(1)

    return ips


def generate_inventory_file(pool_file, inv_file):
    hosts = get_hosts(pool_file)

    inventory = {
        "master": {
            "hosts": {"master": ""}
        },
        "workers": {
            "hosts": {}
        }
    }

    inventory["master"]["hosts"]["master"] = {"ansible_host": hosts[0]}

    for i in range(0, len(hosts[1:])):
        name = f"worker_{i}"
        inventory["workers"]["hosts"][name] = {"ansible_host": hosts[i + 1]}

    with open(inv_file, "w") as file:
        yaml.dump(inventory, file, default_flow_style=False, allow_unicode=True)


if __name__ == "__main__":
    opts, args = getopt.getopt(sys.argv[1:], "i:o:")
    for o, a in opts:
        if o == "-i":
            pool_file = a
        elif o == "-o":
            inv_file = a
    generate_inventory_file(pool_file, inv_file)
