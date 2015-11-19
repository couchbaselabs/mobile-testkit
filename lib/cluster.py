import os
import re
import sys
import json

import jinja2
import ansible.inventory

from lib.syncgateway import SyncGateway
from lib.server import Server
from provision.ansible_runner import run_ansible_playbook


class Cluster:

    def __init__(self):

        # get hosts
        cbs_host_vars = self._hosts_for_tag("couchbase_servers")
        sgs_host_vars = self._hosts_for_tag("sync_gateways")
        sgsw_host_vars = self._hosts_for_tag("sync_gateway_index_writers")
        lds_host_vars = self._hosts_for_tag("load_generators")

        # provide simple consumable dictionaries to functional framwork
        cbs = [{"name": cbsv["inventory_hostname"], "ip": cbsv["ansible_ssh_host"]} for cbsv in cbs_host_vars]
        sgs = [{"name": sgv["inventory_hostname"], "ip": sgv["ansible_ssh_host"]} for sgv in sgs_host_vars]
        sgsw = [{"name": sgwv["inventory_hostname"], "ip": sgwv["ansible_ssh_host"]} for sgwv in sgsw_host_vars]
        lds = [{"name": ldv["inventory_hostname"], "ip": ldv["ansible_ssh_host"]} for ldv in lds_host_vars]

        self.sync_gateways = [SyncGateway(sg) for sg in sgs]
        self.sync_gateway_writers = [SyncGateway(sgw) for sgw in sgsw]
        self.servers = [Server(cb) for cb in cbs]
        self.load_generators = lds

    def _hosts_for_tag(self, tag):
        hostfile = "provisioning_config"

        if not os.path.isfile(hostfile):
            print("File 'provisioning_config' not found at {}".format(os.getcwd()))
            sys.exit(1)

        i = ansible.inventory.Inventory(host_list=hostfile)
        group = i.get_group(tag)
        if group is None:
            return []
        hosts = group.get_hosts()
        return [host.get_variables() for host in hosts]

    def reset(self, config):
        # Delete buckets
        print(">>> Deleting buckets on: {}".format(self.servers[0].ip))
        self.servers[0].delete_buckets()

        # Parse config and grab bucket names
        conf_path = os.path.abspath("conf/" + config)
        bucket_names_from_config = []

        with open(conf_path, "r") as config:
            data = config.read()

            # HACK: Strip out invalid json from config to allow it to be loaded
            #       and parsed for bucket names

            # strip out templated variables {{ ... }}
            data = re.sub("({{.*}})", "0", data)

            # strip out sync functions `function ... }`
            data = re.sub("(`function.*\n)(.*\n)+(.*}`)", "0", data)

            # Find all bucket names in config's databases: {}
            conf_obj = json.loads(data)

            # Add CBGT buckets
            if "cluster_config" in conf_obj.keys():
                bucket_names_from_config.append(conf_obj["cluster_config"]["bucket"])

            dbs = conf_obj["databases"]
            for key, val in dbs.iteritems():
                # Add data buckets
                bucket_names_from_config.append(val["bucket"])
                if "channel_index" in val:
                    # index buckets
                    bucket_names_from_config.append(val["channel_index"]["bucket"])

        # Buckets may be shared for different functionality
        bucket_name_set = list(set(bucket_names_from_config))

        print(">>> Creating buckets {} on: {}".format(bucket_name_set, self.servers[0].ip))
        self.servers[0].create_buckets(bucket_name_set)

        print(">>> Restarting sync_gateway with configuration: {}".format(conf_path))

        run_ansible_playbook(
            "reset-sync-gateway.yml",
            extra_vars="sync_gateway_config_filepath={0}".format(conf_path)
        )

    def __repr__(self):
        s = "\n\n"
        s += "Sync Gateways\n"
        for sg in self.sync_gateways:
            s += str(sg)
        s += "Sync Gateway Writers\n"
        for sgw in self.sync_gateway_writers:
            s += str(sgw)
        s += "Couchbase Servers\n"
        for server in self.servers:
            s += str(server)
        s += "Load Generators\n"
        for lg in self.load_generators:
            s += str(lg)
        s += "\n"
        return s
