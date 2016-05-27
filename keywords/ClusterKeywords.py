import logging
import json
import requests
import re

from requests.exceptions import HTTPError
from requests.exceptions import ConnectionError

from utils import *

from CouchbaseServer import verify_server_version
from libraries.testkit.cluster import Cluster

class ClusterKeywords:

    def get_cluster_topology(self, cluster_config):
        """
        Returns a dictionary of cluster endpoints that will be consumable
          ${sg1} = cluster["sync_gateways"][0]["public"]
          ${sg1_admin} = cluster["sync_gateways"][0]["admin"]
          ${ac1} = cluster["sg_accels"][0]
          ${cbs} = cluster["couchbase_servers"][0]
        """

        with open("{}.json".format(cluster_config)) as f:
            cluster = json.loads(f.read())

        sg_urls = []

        for sg in cluster["sync_gateways"]:
            public = "http://{}:4984".format(sg["ip"])
            admin = "http://{}:4985".format(sg["ip"])
            sg_urls.append({"public": public, "admin": admin})

        ac_urls = ["http://{}:4985".format(sga["ip"]) for sga in cluster["sg_accels"]]
        cbs_urls = ["http://{}:8091".format(cb["ip"]) for cb in cluster["couchbase_servers"]]

        # Format into urls that robot keywords can consume easily
        formatted_cluster = {
            "sync_gateways" : sg_urls,
            "sg_accels": ac_urls,
            "couchbase_servers": cbs_urls
        }

        logging.info(cluster)

        return formatted_cluster

    def sync_gateway_version_is_binary(self, version):
        if len(version.split(".")) > 1:
            # ex 1.2.1 or 1.2.1-4
            return True
        else:
            return False

    def verfiy_no_running_services(self, cluster_config):

        with open("{}.json".format(cluster_config)) as f:
            cluster_obj = json.loads(f.read())

        running_services = []
        for host in cluster_obj["hosts"]:

            # Couchbase Server
            try:
                resp = requests.get("http://Administrator:password@{}:8091/pools".format(host["ip"]))
                log_r(resp)
                running_services.append(resp.url)
            except ConnectionError as he:
                logging.info(he)

            # Sync Gateway
            try:
                resp = requests.get("http://{}:4984".format(host["ip"]))
                log_r(resp)
                running_services.append(resp.url)
            except ConnectionError as he:
                logging.info(he)

            # Sg Accel
            try:
                resp = requests.get("http://{}:4985".format(host["ip"]))
                log_r(resp)
                running_services.append(resp.url)
            except ConnectionError as he:
                logging.info(he)

        assert len(running_services) == 0, "Running Services Found: {}".format(running_services)

    def get_sync_gateway_version(self, host):
        resp = requests.get("http://{}:4984".format(host))
        log_r(resp)
        resp.raise_for_status()
        resp_obj = resp.json()

        running_version = resp_obj["version"]
        running_version_parts = re.split("[ /(;)]", running_version)

        if running_version_parts[3] == "HEAD":
            running_version_formatted = running_version_parts[6]
        else:
            running_version_formatted = "{}-{}".format(running_version_parts[3], running_version_parts[4])

        # Returns the version as 338493 commit format or 1.2.1-4 version format
        return running_version_formatted

    def verify_sync_gateway_version(self, host, expected_sync_gateway_version):

        running_sg_version = self.get_sync_gateway_version(host)

        logging.info("Expected sync_gateway Version: {}".format(expected_sync_gateway_version))
        logging.info("Running sync_gateway Version: {}".format(running_sg_version))

        if self.sync_gateway_version_is_binary(expected_sync_gateway_version):
            # Example, 1.2.1-4
            if running_sg_version != expected_sync_gateway_version:
                raise ValueError("Unexpected sync_gateway version!! Expected: {} Actual: {}".format(expected_sync_gateway_version, running_sg_version))
        else:
            # Since sync_gateway does not return the full commit, verify the prefix
            if running_sg_version != expected_sync_gateway_version[:7]:
                raise ValueError("Unexpected sync_gateway version!! Expected: {} Actual: {}".format(expected_sync_gateway_version, running_sg_version))

    def get_sg_accel_version(self, host):
        resp = requests.get("http://{}:4985".format(host))
        log_r(resp)
        resp.raise_for_status()
        resp_obj = resp.json()

        running_version = resp_obj["version"]
        running_version_parts = re.split("[ /(;)]", running_version)

        if running_version_parts[3] == "HEAD":
            running_version_formatted = running_version_parts[6]
        else:
            running_version_formatted = "{}-{}".format(running_version_parts[3], running_version_parts[4])

        # Returns the version as 338493 commit format or 1.2.1-4 version format
        return running_version_formatted

    def verify_sg_accel_version(self, host, expected_sg_accel_version):

        running_ac_version = self.get_sg_accel_version(host)

        logging.info("Expected sg_accel Version: {}".format(expected_sg_accel_version))
        logging.info("Running sg_accel Version: {}".format(running_ac_version))

        if self.sync_gateway_version_is_binary(expected_sg_accel_version):
            # Example, 1.2.1-4
            if running_ac_version != expected_sg_accel_version:
                raise ValueError("Unexpected sync_gateway version!! Expected: {} Actual: {}".format(expected_sg_accel_version, running_ac_version))
        else:
            # Since sync_gateway does not return the full commit, verify the prefix
            if running_ac_version != expected_sg_accel_version[:7]:
                raise ValueError("Unexpected sync_gateway version!! Expected: {} Actual: {}".format(expected_sg_accel_version, running_ac_version))

    def verify_cluster_versions(self, cluster_config, expected_server_version, expected_sync_gateway_version):

        logging.info("Verfying versions for cluster: {}".format(cluster_config))

        with open("{}.json".format(cluster_config)) as f:
            cluster_obj = json.loads(f.read())

        # Verify Server version
        for server in cluster_obj["couchbase_servers"]:
            verify_server_version(server["ip"], expected_server_version)

        # Verify sync_gateway versions
        for sg in cluster_obj["sync_gateways"]:
            self.verify_sync_gateway_version(sg["ip"], expected_sync_gateway_version)

        # Verify sg_accel versions, use the same expected version for sync_gateway for now
        for ac in cluster_obj["sg_accels"]:
            self.verify_sg_accel_version(ac["ip"], expected_sync_gateway_version)

    def reset_cluster(self, sync_gateway_config):
        cluster = Cluster()
        cluster.reset(sync_gateway_config)

    def provision_cluster(self, server_version, sync_gateway_version, sync_gateway_config):

        # Dirty hack -- these have to be put here in order to avoid circular imports
        from libraries.provision.install_couchbase_server import CouchbaseServerConfig
        from libraries.provision.provision_cluster import provision_cluster
        from libraries.provision.install_sync_gateway import SyncGatewayConfig

        cbs_config = CouchbaseServerConfig(server_version)

        if self.sync_gateway_version_is_binary(sync_gateway_version):
            version, build = version_and_build(sync_gateway_version)
            sg_config = SyncGatewayConfig(None, version, build, sync_gateway_config, "", False)
        else:
            sg_config = SyncGatewayConfig(sync_gateway_version, None, None, sync_gateway_config, "", False)

        provision_cluster(cbs_config, sg_config, install_deps=False)


