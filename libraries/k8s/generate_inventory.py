import json
import logging
import sys
import yaml


def get_hosts(pool_file="../../resources/pool.json"):
    with open(pool_file) as f:
        pool_dict = json.loads(f.read())
        ips = pool_dict["ips"]

    # Make sure there are no duplicate endpoints
    if len(ips) != len(set(ips)):
        logging.error("Duplicate endpoints found in 'resources/pools'. Make sure they are unique. Exiting ...")
        sys.exit(1)

    return ips


def generate_inventory_file():
    hosts = get_hosts()

    inventory = {
        "master": {
            "hosts": {"master": ""}
        },
        "workers": {
            "hosts": {}
        }
    }

    inventory["master"]["hosts"]["master"] = hosts[0]

    for i in range(0, len(hosts[1:])):
        name = f"worker_{i}"
        inventory["workers"]["hosts"][name] = hosts[i + 1]

    with open("inventory.yaml", "w") as inv_file:
        yaml.dump(inventory, inv_file, default_flow_style=False, allow_unicode=True)


if __name__ == "__main__":
    generate_inventory_file()