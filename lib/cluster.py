import os
import re
import sys
import json
import time

import jinja2
import ansible.inventory

from lib.syncgateway import SyncGateway
from lib.server import Server
from lib.admin import Admin
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

    def validate_cluster(self):

        # Validate sync gateways
        num_index_readers = len(self.sync_gateways) - len(self.sync_gateway_writers)
        if num_index_readers == 0:
            raise Exception("Functional tests require at least 1 index reader")

    def reset(self, config):

        self.validate_cluster()
        
        # Stop sync_gateways
        print(">>> Stopping sync_gateway")
        status = run_ansible_playbook("stop-sync-gateway.yml", stop_on_fail=False)
        assert(status == 0)

        # Deleting sync_gateway artifacts
        print(">>> Deleting sync_gateway artifacts")
        status = run_ansible_playbook("delete-sync-gateway-artifacts.yml", stop_on_fail=False)
        assert(status == 0)

        # Delete buckets
        print(">>> Deleting buckets on: {}".format(self.servers[0].ip))
        self.servers[0].delete_buckets()

        # Parse config and grab bucket names
        conf_path = os.path.abspath("conf/" + config)
        bucket_names_from_config = []

        is_distributed_index = False
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
                is_distributed_index = True
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

        print(">>> Creating buckets on: {}".format(self.servers[0].ip))
        print(">>> Creating buckets {}".format(bucket_name_set))
        self.servers[0].create_buckets(bucket_name_set)

        print(">>> Starting sync_gateway with configuration: {}".format(conf_path))

        # Start sync-gateway
        status = run_ansible_playbook(
            "start-sync-gateway.yml",
            extra_vars="sync_gateway_config_filepath={0}".format(conf_path),
            stop_on_fail=False
        )
        assert(status == 0)

        # Validate CBGT
        if is_distributed_index:
            if not self.validate_cbgt_pindex_distribution_retry(config):
                self.save_cbgt_diagnostics()
                raise Exception("Failed to validate CBGT Pindex distribution")
            print(">>> Detected valid CBGT Pindex distribution")
        else:
            print(">>> Running in channel cache")

    def save_cbgt_diagnostics(self):
        
        # CBGT REST Admin API endpoint
        for sync_gateway_writer in self.sync_gateway_writers:

            adminApi = Admin(sync_gateway_writer)
            cbgt_diagnostics = adminApi.get_cbgt_diagnostics()
            cbgt_cfg = adminApi.get_cbgt_cfg()
        
            # dump raw diagnostics
            pretty_print_json = json.dumps(cbgt_diagnostics, sort_keys=True, indent=4, separators=(',', ': '))
            print("SG {} CBGT diagnostic output: {}".format(sync_gateway_writer, pretty_print_json))
        
    def validate_cbgt_pindex_distribution_retry(self):
        """
        Validates the CBGT pindex distribution by looking for nodes that don't have
        any pindexes assigned to it
        """
        for i in xrange(10):
            is_valid = self.validate_cbgt_pindex_distribution()
            if is_valid:
               return True
            else:
                print("Could not validate CBGT Pindex distribution.  Will retry after sleeping ..")
                time.sleep(5)

        return False 

    def validate_cbgt_pindex_distribution(self):

        # build a map of node -> num_pindexes
        node_defs_pindex_counts = {}

        # CBGT REST Admin API endpoint 
        adminApi = Admin(self.sync_gateways[0])
        cbgt_cfg = adminApi.get_cbgt_cfg()

        # loop over the planpindexes and update the count for the node where it lives
        # this will end up with a dictionary like:
        #  {'74c818f04b99b169': 32, '11886131c807a30e': 32}  (each node uuid has 32 pindexes)
        plan_pindexes = cbgt_cfg["planPIndexes"]["planPIndexes"]
        for data_bucket_key, data_bucket_val in plan_pindexes.iteritems():

            # get the nodes where this pindex lives
            nodes = data_bucket_val["nodes"]
            # it should only live on one node.  if not, abort.
            if len(nodes) > 1:
                raise Exception("Unexpected: a CBGT Pindex was assigned to more than one node")
            # loop over the nodes where this pindex lives and increment the count
            for node in nodes:

                # add a key for this node if we don't already have one
                if not node_defs_pindex_counts.has_key(node):
                    node_defs_pindex_counts[node] = 0
                    
                current_pindex_count = node_defs_pindex_counts[node]
                current_pindex_count += 1
                node_defs_pindex_counts[node] = current_pindex_count


        print("CBGT node to pindex counts: {}".format(node_defs_pindex_counts))
        
        # make sure number of unique node uuids is equal to the number of sync gateway writers
        if len(node_defs_pindex_counts) != len(self.sync_gateway_writers):
            print("CBGT len(unique_node_uuids) != len(self.sync_gateway_writers) ({} != {})".format(
                len(node_defs_pindex_counts),
                len(self.sync_gateway_writers)
            ))
            return False 

        # make sure that all of the nodes have approx the same number of pindexes assigneed to them
        i = 0
        num_pindex_first_node = 0 
        for node_def_uuid, num_pindexes in node_defs_pindex_counts.iteritems():

            if i == 0:
                # it's the first node we've looked at, just record number of pindexes and continue 
                num_pindex_first_node = num_pindexes
                i += 1
                continue

            # ok, it's the 2nd+ node, make sure the delta with the first node is less than or equal to 1
            # (the reason we can't compare for equality is that sometimes the pindexes can't be
            # divided evenly across the cluster)
            delta = abs(num_pindex_first_node - num_pindexes)
            if delta > 1:
                print("CBGT Sync Gateway node {} has {} pindexes, but other node has {} pindexes.".format(
                    node_def_uuid,
                    num_pindexes,
                    num_pindex_first_node
                ))
                return False
                
    
        return True

    def __repr__(self):
        s = "\n\n"
        s += "Sync Gateways\n"
        for sg in self.sync_gateways:
            s += str(sg)
        s += "\nSync Gateway Writers\n"
        for sgw in self.sync_gateway_writers:
            s += str(sgw)
        s += "\nCouchbase Servers\n"
        for server in self.servers:
            s += str(server)
        s += "\nLoad Generators\n"
        for lg in self.load_generators:
            s += str(lg)
        s += "\n"
        return s
