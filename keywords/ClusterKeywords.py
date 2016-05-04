import logging
import json
import requests
import re

def log_r(request):
    logging.info("{0} {1} {2}".format(
            request.request.method,
            request.request.url,
            request.status_code
        )
    )
    logging.debug("{0} {1}\nHEADERS = {2}\nBODY = {3}".format(
            request.request.method,
            request.request.url,
            request.request.headers,
            request.request.body,
        )
    )
    logging.debug("{}".format(request.text))

class ClusterKeywords:

    def sync_gateway_version_is_binary(self, version):
        if len(version.split(".")) > 1:
            # ex 1.2.1 or 1.2.1-4
            return True
        else:
            return False

    def get_server_version(self, host):
        resp = requests.get("http://{}:8091/pools".format(host))
        log_r(resp)
        resp.raise_for_status()
        resp_obj = resp.json()

        # Actual version is the following format 4.1.1-5914-enterprise
        running_server_version = resp_obj["implementationVersion"]
        running_server_version_parts = running_server_version.split("-")

        # Return version in the formatt 4.1.1-5487
        return "{}-{}".format(running_server_version_parts[0], running_server_version_parts[1])

    def verify_server_version(self, host, expected_server_version):

        running_server_version = self.get_server_version(host)
        expected_server_version_parts = expected_server_version.split("-")

        # Check both version parts if expected version contains a build
        if len(expected_server_version_parts) == 2:
            # 4.1.1-5487
            logging.info("Expected Server Version: {}".format(expected_server_version))
            logging.info("Running Server Version: {}".format(running_server_version))
            if running_server_version != expected_server_version:
                raise ValueError("Unexpected server version!! Expected: {} Actual: {}".format(expected_server_version, running_server_version))
        elif len(expected_server_version_parts) == 1:
            # 4.1.1
            running_server_version_parts = running_server_version.split("-")
            logging.info("Expected Server Version: {}".format(expected_server_version))
            logging.info("Running Server Version: {}".format(running_server_version_parts[0]))
            if expected_server_version != running_server_version_parts[0]:
                raise ValueError("Unexpected server version!! Expected: {} Actual: {}".format(expected_server_version, running_server_version_parts[0]))
        else:
            raise ValueError("Unsupported version format")

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
            self.verify_server_version(server["ip"], expected_server_version)

        # Verify sync_gateway versions
        for sg in cluster_obj["sync_gateways"]:
            self.verify_sync_gateway_version(sg["ip"], expected_sync_gateway_version)

        # Verify sg_accel versions, use the same expected version for sync_gateway for now
        for ac in cluster_obj["sg_accels"]:
            self.verify_sg_accel_version(ac["ip"], expected_sync_gateway_version)
