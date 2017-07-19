import json
import os

import requests
from requests.exceptions import ConnectionError

from keywords import couchbaseserver
from keywords.constants import CLUSTER_CONFIGS_DIR
from keywords.exceptions import ProvisioningError
from keywords.SyncGateway import (verify_sg_accel_version,
                                  verify_sync_gateway_version,
                                  verify_sg_accel_product_info,
                                  verify_sync_gateway_product_info)
from keywords.utils import (log_info, log_r, version_and_build,
                            version_is_binary, compare_versions)
from libraries.testkit.cluster import Cluster


class ClusterKeywords:

    def set_cluster_config(self, name):
        """Sets CLUSTER_CONFIG environment variable for provisioning

        Checks if CLUSTER_CONFIG is set, will fail if it is.
        Checks if cluster configuration file exists, will fail if it does not
        """

        if "CLUSTER_CONFIG" in os.environ:
            raise ProvisioningError("CLUSTER_CONFIG will be set by suite setup. Make sure it is unset.")

        path = "{}/{}".format(CLUSTER_CONFIGS_DIR, name)
        if not os.path.isfile(path):
            raise ProvisioningError("{} not found. Make sure you have generated your cluster configurations.")

        log_info("Setting CLUSTER_CONFIG: {}".format(path))
        os.environ["CLUSTER_CONFIG"] = path

    def unset_cluster_config(self):
        """Will unset the CLUSTER_CONFIG environment variable if it is set.

        Will fail if CLUSTER_CONFIG is not set
        """

        if "CLUSTER_CONFIG" not in os.environ:
            raise ProvisioningError("Trying to unset CLUSTER_CONFIG but it is not defined")

        log_info("Unsetting CLUSTER_CONFIG")
        del os.environ["CLUSTER_CONFIG"]

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
        lbs_urls = ["http://{}".format(lb["ip"]) for lb in cluster["load_balancers"]]

        server_port = 8091
        server_scheme = "http"

        if cluster["environment"]["cbs_ssl_enabled"]:
            server_port = 18091
            server_scheme = "https"

        cbs_urls = ["{}://{}:{}".format(server_scheme, cb["ip"], server_port) for cb in cluster["couchbase_servers"]]

        # Format into urls that robot keywords can consume easily
        formatted_cluster = {
            "sync_gateways": sg_urls,
            "sg_accels": ac_urls,
            "couchbase_servers": cbs_urls,
            "load_balancers": lbs_urls
        }

        log_info(cluster)

        return formatted_cluster

    def verfiy_no_running_services(self, cluster_config):

        with open("{}.json".format(cluster_config)) as f:
            cluster_obj = json.loads(f.read())

        server_port = 8091
        server_scheme = "http"

        if cluster_obj["cbs_ssl_enabled"]:
            server_port = 18091
            server_scheme = "https"

        running_services = []
        for host in cluster_obj["hosts"]:

            # Couchbase Server
            try:
                resp = requests.get("{}://Administrator:password@{}:{}/pools".format(server_scheme, host["ip"], server_port))
                log_r(resp)
                running_services.append(resp.url)
            except ConnectionError as he:
                log_info(he)

            # Sync Gateway
            try:
                resp = requests.get("http://{}:4984".format(host["ip"]))
                log_r(resp)
                running_services.append(resp.url)
            except ConnectionError as he:
                log_info(he)

            # Sg Accel
            try:
                resp = requests.get("http://{}:4985".format(host["ip"]))
                log_r(resp)
                running_services.append(resp.url)
            except ConnectionError as he:
                log_info(he)

        assert len(running_services) == 0, "Running Services Found: {}".format(running_services)

    def verify_cluster_versions(self, cluster_config, expected_server_version, expected_sync_gateway_version):

        log_info("Verfying versions for cluster: {}".format(cluster_config))

        with open("{}.json".format(cluster_config)) as f:
            cluster_obj = json.loads(f.read())

        cbs_ssl = False
        if cluster_obj["environment"]["cbs_ssl_enabled"]:
            cbs_ssl = True

        # Verify Server version
        for server in cluster_obj["couchbase_servers"]:
            couchbaseserver.verify_server_version(server["ip"], expected_server_version, cbs_ssl=cbs_ssl)

        # Verify sync_gateway versions
        for sg in cluster_obj["sync_gateways"]:
            verify_sync_gateway_product_info(sg["ip"])
            verify_sync_gateway_version(sg["ip"], expected_sync_gateway_version)

        # Verify sg_accel versions, use the same expected version for sync_gateway for now
        for ac in cluster_obj["sg_accels"]:
            if compare_versions(expected_sync_gateway_version, "1.5.0") >= 0:
                # Only verify the correct product naming after 1.5 since it was fixed in 1.5
                verify_sg_accel_product_info(ac["ip"])
            verify_sg_accel_version(ac["ip"], expected_sync_gateway_version)

    def reset_cluster(self, cluster_config, sync_gateway_config):
        """
        1. Stop sync_gateways
        2. Stop sg_accels
        3. Delete sync_gateway artifacts (logs, conf)
        4. Delete sg_accel artifacts (logs, conf)
        5. Delete all server buckets
        6. Create buckets from 'sync_gateway_config'
        7. Wait for server to be in 'healthy' state
        8. Deploy sync_gateway config and start
        9. Deploy sg_accel config and start (distributed index mode only)
        """

        cluster = Cluster(config=cluster_config)
        cluster.reset(sync_gateway_config)

    def provision_cluster(self, cluster_config, server_version, sync_gateway_version, sync_gateway_config, race_enabled=False, sg_platform="centos", sa_platform="centos"):

        if server_version is None or sync_gateway_version is None or sync_gateway_version is None:
            raise ProvisioningError("Please make sure you have server_version, sync_gateway_version, and sync_gateway_config are set")

        # Dirty hack -- these have to be put here in order to avoid circular imports
        from libraries.provision.install_couchbase_server import CouchbaseServerConfig
        from libraries.provision.provision_cluster import provision_cluster
        from libraries.provision.install_sync_gateway import SyncGatewayConfig

        cbs_config = CouchbaseServerConfig(server_version)

        if version_is_binary(sync_gateway_version):

            if race_enabled:
                raise ProvisioningError("Race should only be enabled for source builds")

            version, build = version_and_build(sync_gateway_version)
            sg_config = SyncGatewayConfig(
                commit=None,
                version_number=version,
                build_number=build,
                config_path=sync_gateway_config,
                build_flags="",
                skip_bucketcreation=False
            )
        else:

            build_flags = ""
            if race_enabled:
                build_flags = "-race"

            sg_config = SyncGatewayConfig(
                commit=sync_gateway_version,
                version_number=None,
                build_number=None,
                config_path=sync_gateway_config,
                build_flags=build_flags,
                skip_bucketcreation=False
            )

        provision_cluster(cluster_config, cbs_config, sg_config, sg_platform, sa_platform)

        # verify running services are the expected versions
        self.verify_cluster_versions(cluster_config, server_version, sync_gateway_version)
