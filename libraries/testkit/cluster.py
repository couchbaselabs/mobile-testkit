import os
import re
import sys
import json
import time

from requests.exceptions import ConnectionError

from testkit.syncgateway import SyncGateway
from testkit.sgaccel import SgAccel
from testkit.server import Server
from testkit.admin import Admin
from testkit.config import Config
from testkit import settings
from provision.ansible_runner import AnsibleRunner

import keywords.CouchbaseServer
from keywords import utils

from keywords.utils import log_info


class Cluster:
    """
    An older remnant of first pass of Python API

    Before using or extending this, check keywords/ClusterKeywords.py to see if it already
    has this functionality
    """

    def __init__(self, config):

        self._cluster_config = config

        if not os.path.isfile(self._cluster_config):
            log_info("Cluster config not found in 'resources/cluster_configs/'")
            raise IOError("Cluster config not found in 'resources/cluster_configs/'")

        log_info(self._cluster_config)

        # Load resources/cluster_configs/<cluster_config>.json
        with open("{}.json".format(config)) as f:
            cluster = json.loads(f.read())

        cbs = [{"name": cbs["name"], "ip": cbs["ip"]} for cbs in cluster["couchbase_servers"]]
        sgs = [{"name": sg["name"], "ip": sg["ip"]} for sg in cluster["sync_gateways"]]
        acs = [{"name": ac["name"], "ip": ac["ip"]} for ac in cluster["sg_accels"]]

        log_info("cbs: {}".format(cbs))
        log_info("sgs: {}".format(sgs))
        log_info("acs: {}".format(acs))

        self.sync_gateways = [SyncGateway(cluster_config=self._cluster_config, target=sg) for sg in sgs]
        self.sg_accels = [SgAccel(cluster_config=self._cluster_config, target=ac) for ac in acs]
        self.servers = [Server(cluster_config=self._cluster_config, target=cb) for cb in cbs]
        self.sync_gateway_config = None  # will be set to Config object when reset() called

        # for integrating keywords
        self.server_keywords = keywords.CouchbaseServer.CouchbaseServer()

    def validate_cluster(self):

        # Validate sync gateways
        if len(self.sync_gateways) == 0:
            raise Exception("Functional tests require at least 1 index reader")        
        
    def reset(self, sg_config_path):

        self.validate_cluster()

        ansible_runner = AnsibleRunner(self._cluster_config)
        
        # Stop sync_gateways
        log_info(">>> Stopping sync_gateway")
        status = ansible_runner.run_ansible_playbook("stop-sync-gateway.yml")
        assert status == 0, "Failed to stop sync gateway"

        # Stop sync_gateways
        log_info(">>> Stopping sg_accel")
        status = ansible_runner.run_ansible_playbook("stop-sg-accel.yml")
        assert status == 0, "Failed to stop sg_accel"

        # Deleting sync_gateway artifacts
        log_info(">>> Deleting sync_gateway artifacts")
        status = ansible_runner.run_ansible_playbook("delete-sync-gateway-artifacts.yml")
        assert status == 0, "Failed to delete sync_gateway artifacts"

        # Deleting sg_accel artifacts
        log_info(">>> Deleting sg_accel artifacts")
        status = ansible_runner.run_ansible_playbook("delete-sg-accel-artifacts.yml")
        assert status == 0, "Failed to delete sg_accel artifacts"

        bucket_delete_create_max_retries = 3
        bucket_delete_create_attempt_num = 0
        while bucket_delete_create_attempt_num < bucket_delete_create_max_retries:
            try:
                log_info(">>> Deleting / Creating server buckets: Attempt {}".format(bucket_delete_create_attempt_num))
                # Delete buckets
                log_info(">>> Deleting buckets on: {}".format(self.servers[0].ip))
                status = self.servers[0].delete_buckets()
                assert status == 0
                log_info(">>> Bucket deletion status: {}".format(status))

                # Parse config and grab bucket names
                config_path_full = os.path.abspath(sg_config_path)
                config = Config(config_path_full)
                mode = config.get_mode()
                bucket_name_set = config.get_bucket_name_set()

                self.sync_gateway_config = config

                log_info(">>> Creating buckets on: {}".format(self.servers[0].ip))
                log_info(">>> Creating buckets {}".format(bucket_name_set))
                status = self.servers[0].create_buckets(bucket_name_set)
                assert status == 0
                log_info(">>> Bucket creation status: {}".format(status))

                # Wait for server to be in a warmup state to work around
                # https://github.com/couchbase/sync_gateway/issues/1745
                log_info(">>> Waiting for Server: {} to be in a healthy state".format(self.servers[0].url))
                self.server_keywords.wait_for_ready_state(self.servers[0].url)

                # Both steps are successful, break out of retry loop
                break
            except AssertionError as e:
                log_info("Failed to delete / create buckets. Trying again ...")
                bucket_delete_create_attempt_num += 1
                # Wait 3 sec before retry
                time.sleep(3)

        # Max tries to delete / create buckets
        if bucket_delete_create_attempt_num == bucket_delete_create_max_retries:
            raise RuntimeError("Max tries exceeded to delete / create buckets")

        log_info(">>> Starting sync_gateway with configuration: {}".format(config_path_full))
        utils.dump_file_contents_to_logs(config_path_full)

        # Start sync-gateway
        status = ansible_runner.run_ansible_playbook(
            "start-sync-gateway.yml",
            extra_vars={
                "sync_gateway_config_filepath": config_path_full
            }
        )
        assert status == 0, "Failed to start to Sync Gateway"

        # HACK - only enable sg_accel for distributed index tests
        # revise this with https://github.com/couchbaselabs/sync-gateway-testcluster/issues/222
        if mode == "distributed_index":
            # Start sg-accel
            status = ansible_runner.run_ansible_playbook(
                "start-sg-accel.yml",
                extra_vars={
                    "sync_gateway_config_filepath": config_path_full
                }
            )
            assert status == 0, "Failed to start sg_accel"

        # Validate CBGT
        if mode == "distributed_index":
            if not self.validate_cbgt_pindex_distribution_retry():
                self.save_cbgt_diagnostics()
                raise Exception("Failed to validate CBGT Pindex distribution")
            log_info(">>> Detected valid CBGT Pindex distribution")
        else:
            log_info(">>> Running in channel cache")

        return mode

    def save_cbgt_diagnostics(self):
        
        # CBGT REST Admin API endpoint
        for sync_gateway_writer in self.sg_accels:

            adminApi = Admin(sync_gateway_writer)
            cbgt_diagnostics = adminApi.get_cbgt_diagnostics()
            cbgt_cfg = adminApi.get_cbgt_cfg()
        
            # dump raw diagnostics
            pretty_print_json = json.dumps(cbgt_diagnostics, sort_keys=True, indent=4, separators=(',', ': '))
            log_info("SG {} CBGT diagnostic output: {}".format(sync_gateway_writer, pretty_print_json))
        
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
                log_info("Could not validate CBGT Pindex distribution.  Will retry after sleeping ..")
                time.sleep(5)

        return False 

    def validate_cbgt_pindex_distribution(self):

        # build a map of node -> num_pindexes
        node_defs_pindex_counts = {}

        # CBGT REST Admin API endpoint 
        adminApi = Admin(self.sg_accels[0])
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

        log_info("CBGT node to pindex counts: {}".format(node_defs_pindex_counts))
        
        # make sure number of unique node uuids is equal to the number of sync gateway writers
        if len(node_defs_pindex_counts) != len(self.sg_accels):
            log_info("CBGT len(unique_node_uuids) != len(self.sync_gateway_writers) ({} != {})".format(
                len(node_defs_pindex_counts),
                len(self.sg_accels)
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
                log_info("CBGT Sync Gateway node {} has {} pindexes, but other node has {} pindexes.".format(
                    node_def_uuid,
                    num_pindexes,
                    num_pindex_first_node
                ))
                return False
                
    
        return True

    def verify_alive(self, mode):
        errors = []
        for sg in self.sync_gateways:
            try:
                info = sg.info()
                log_info("sync_gateway: {}, info: {}".format(sg.url, info))
            except ConnectionError as e:
                log_info("sync_gateway down: {}".format(e))
                errors.append((sg, e))

        if mode == "distributed_index":
            for sa in self.sg_accels:
                try:
                    info = sa.info()
                    log_info("sg_accel: {}, info: {}".format(sa.url, info))
                except ConnectionError as e:
                    log_info("sg_accel down: {}".format(e))
                    errors.append((sa, e))

        return errors

    def __repr__(self):
        s = "\n\n"
        s += "Sync Gateways\n"
        for sg in self.sync_gateways:
            s += str(sg)
        s += "\nSync Gateway Accels\n"
        for sgw in self.sg_accels:
            s += str(sgw)
        s += "\nCouchbase Servers\n"
        for server in self.servers:
            s += str(server)
        s += "\nLoad Generators\n"
        for lg in self.load_generators:
            s += str(lg)
        s += "\n"
        return s
