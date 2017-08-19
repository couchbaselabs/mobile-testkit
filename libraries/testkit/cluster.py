import json
import os
import time

from requests.exceptions import ConnectionError

import keywords.exceptions
from keywords.couchbaseserver import CouchbaseServer
from keywords.exceptions import ProvisioningError
from keywords.utils import log_info
from libraries.provision.ansible_runner import AnsibleRunner
from libraries.testkit.admin import Admin
from libraries.testkit.config import Config
from libraries.testkit.sgaccel import SgAccel
from libraries.testkit.syncgateway import SyncGateway
from utilities.cluster_config_utils import is_load_balancer_enabled
from utilities.cluster_config_utils import get_load_balancer_ip


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

        # Get load balancer IP
        lb_ip = None
        if is_load_balancer_enabled(self._cluster_config):
            # If load balancer is defined,
            # Switch all SG URLs to that of load balancer
            lb_ip = get_load_balancer_ip(self._cluster_config)

            sgs = [{"name": sg["name"], "ip": lb_ip} for sg in cluster["sync_gateways"]]
            log_info("Using load balancer IP as the SG IP: {}".format(sgs))
        else:
            sgs = [{"name": sg["name"], "ip": sg["ip"]} for sg in cluster["sync_gateways"]]

        acs = [{"name": ac["name"], "ip": ac["ip"]} for ac in cluster["sg_accels"]]

        self.cbs_ssl = cluster["environment"]["cbs_ssl_enabled"]
        self.xattrs = cluster["environment"]["xattrs_enabled"]

        if self.cbs_ssl:
            cbs_urls = ["https://{}:18091".format(cbs["ip"]) for cbs in cluster["couchbase_servers"]]
        else:
            cbs_urls = ["http://{}:8091".format(cbs["ip"]) for cbs in cluster["couchbase_servers"]]

        log_info("cbs: {}".format(cbs_urls))
        log_info("sgs: {}".format(sgs))
        log_info("acs: {}".format(acs))
        log_info("ssl: {}".format(self.cbs_ssl))

        self.sync_gateways = [SyncGateway(cluster_config=self._cluster_config, target=sg) for sg in sgs]
        self.sg_accels = [SgAccel(cluster_config=self._cluster_config, target=ac) for ac in acs]
        self.servers = [CouchbaseServer(url=cb_url) for cb_url in cbs_urls]
        self.sync_gateway_config = None  # will be set to Config object when reset() called

    def reset(self, sg_config_path):

        ansible_runner = AnsibleRunner(self._cluster_config)

        log_info(">>> Reseting cluster ...")
        log_info(">>> CBS SSL enabled: {}".format(self.cbs_ssl))
        log_info(">>> Using xattrs: {}".format(self.xattrs))

        # Stop sync_gateways
        log_info(">>> Stopping sync_gateway")
        status = ansible_runner.run_ansible_playbook("stop-sync-gateway.yml")
        assert status == 0, "Failed to stop sync gateway"

        # Stop sync_gateway accels
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

        # Delete buckets
        log_info(">>> Deleting buckets on: {}".format(self.servers[0].url))
        self.servers[0].delete_buckets()

        # Parse config and grab bucket names
        config_path_full = os.path.abspath(sg_config_path)
        config = Config(config_path_full)
        mode = config.get_mode()
        bucket_name_set = config.get_bucket_name_set()

        self.sync_gateway_config = config

        is_valid, reason = validate_cluster(self.sync_gateways, self.sg_accels, config)
        if not is_valid:
            raise ProvisioningError(reason)

        log_info(">>> Creating buckets on: {}".format(self.servers[0].url))
        log_info(">>> Creating buckets {}".format(bucket_name_set))
        self.servers[0].create_buckets(bucket_name_set)

        # Wait for server to be in a warmup state to work around
        # https://github.com/couchbase/sync_gateway/issues/1745
        log_info(">>> Waiting for Server: {} to be in a healthy state".format(self.servers[0].url))
        self.servers[0].wait_for_ready_state()

        log_info(">>> Starting sync_gateway with configuration: {}".format(config_path_full))

        server_port = 8091
        server_scheme = "http"

        if self.cbs_ssl:
            server_port = 18091
            server_scheme = "https"

        # Start sync-gateway
        playbook_vars = {
            "sync_gateway_config_filepath": config_path_full,
            "server_port": server_port,
            "server_scheme": server_scheme,
            "autoimport": "",
            "xattrs": ""
        }

        # Add configuration to run with xattrs
        if self.xattrs:
            playbook_vars["autoimport"] = '"import_docs": "continuous",'
            playbook_vars["xattrs"] = '"enable_shared_bucket_access": true,'

        status = ansible_runner.run_ansible_playbook(
            "start-sync-gateway.yml",
            extra_vars=playbook_vars
        )
        assert status == 0, "Failed to start to Sync Gateway"

        # HACK - only enable sg_accel for distributed index tests
        # revise this with https://github.com/couchbaselabs/sync-gateway-testcluster/issues/222
        if mode == "di":
            # Start sg-accel
            status = ansible_runner.run_ansible_playbook(
                "start-sg-accel.yml",
                extra_vars=playbook_vars
            )
            assert status == 0, "Failed to start sg_accel"

        # Validate CBGT
        if mode == "di":
            if not self.validate_cbgt_pindex_distribution_retry(len(self.sg_accels)):
                self.save_cbgt_diagnostics()
                raise Exception("Failed to validate CBGT Pindex distribution")
            log_info(">>> Detected valid CBGT Pindex distribution")
        else:
            log_info(">>> Running in channel cache")

        return mode

    def restart_services(self):
        ansible_runner = AnsibleRunner(self._cluster_config)
        status = ansible_runner.run_ansible_playbook(
            "restart-services.yml",
            extra_vars={}
        )
        assert status == 0, "Failed to restart services"

    def save_cbgt_diagnostics(self):

        # CBGT REST Admin API endpoint
        for sync_gateway_writer in self.sg_accels:

            adminApi = Admin(sync_gateway_writer)
            cbgt_diagnostics = adminApi.get_cbgt_diagnostics()
            adminApi.get_cbgt_config()

            # dump raw diagnostics
            pretty_print_json = json.dumps(cbgt_diagnostics, sort_keys=True, indent=4, separators=(',', ': '))
            log_info("SG {} CBGT diagnostic output: {}".format(sync_gateway_writer, pretty_print_json))

    def validate_cbgt_pindex_distribution_retry(self, num_running_sg_accels):
        """
        Validates the CBGT pindex distribution by looking for nodes that don't have
        any pindexes assigned to it
        """
        for i in xrange(10):
            is_valid = self.validate_cbgt_pindex_distribution(num_running_sg_accels)
            if is_valid:
                return True
            else:
                log_info("Could not validate CBGT Pindex distribution.  Will retry after sleeping ..")
                time.sleep(5)

        return False

    def validate_cbgt_pindex_distribution(self, num_running_sg_accels):

        if num_running_sg_accels < 1:
            raise keywords.exceptions.ClusterError("Need at least one sg_accel running to verify pindexes")

        # build a map of node -> num_pindexes
        node_defs_pindex_counts = {}

        # CBGT REST Admin API endpoint
        adminApi = Admin(self.sg_accels[0])
        cbgt_cfg = adminApi.get_cbgt_config()

        # loop over the planpindexes and update the count for the node where it lives
        # this will end up with a dictionary like:
        #  {'74c818f04b99b169': 32, '11886131c807a30e': 32}  (each node uuid has 32 pindexes)
        plan_pindexes = cbgt_cfg.p_indexes
        for data_bucket_key, data_bucket_val in plan_pindexes.iteritems():

            # get the nodes where this pindex lives
            nodes = data_bucket_val["nodes"]
            # it should only live on one node.  if not, abort.
            if len(nodes) > 1:
                raise Exception("Unexpected: a CBGT Pindex was assigned to more than one node")
            # loop over the nodes where this pindex lives and increment the count
            for node in nodes:

                # add a key for this node if we don't already have one
                if node not in node_defs_pindex_counts:
                    node_defs_pindex_counts[node] = 0

                current_pindex_count = node_defs_pindex_counts[node]
                current_pindex_count += 1
                node_defs_pindex_counts[node] = current_pindex_count

        log_info("CBGT node to pindex counts: {}".format(node_defs_pindex_counts))

        # make sure number of unique node uuids is equal to the number of sync gateway writers
        if len(node_defs_pindex_counts) != num_running_sg_accels:
            log_info("CBGT len(unique_node_uuids) != len(self.sync_gateway_writers) ({} != {})".format(
                len(node_defs_pindex_counts),
                num_running_sg_accels
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

        if mode == "di":
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
        s += "\n"
        return s


def validate_cluster(sync_gateways, sg_accels, config):

    # Validate sync gateways
    if len(sync_gateways) == 0:
        return False, "Functional tests require at least 1 index reader"

    # If we are using a Distributed Index config, make sure that we have sg-accels
    if config.mode == "di" and len(sg_accels) == 0:
        return False, "INVALID CONFIG: Running in Distributed Index mode but no sg_accels are defined."

    return True, ""
