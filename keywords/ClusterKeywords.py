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

    def verify_cluster_versions(self, cluster_config, expected_server_version, expected_sync_gateway_version):

        logging.info("Verfying versions for cluster: {}".format(cluster_config))

        with open("{}.json".format(cluster_config)) as f:
            cluster_obj = json.loads(f.read())

        logging.info(cluster_obj)

        sync_gateways = cluster_obj["sync_gateways"]
        sg_accels = cluster_obj["sg_accels"]

        # Verify Server version
        for server in cluster_obj["couchbase_servers"]:
            resp = requests.get("http://{}:8091/pools".format(server["ip"]))
            log_r(resp)
            resp.raise_for_status()
            resp_obj = resp.json()

            # Actual version is the following format 4.1.1-5914-enterprise
            running_server_version = resp_obj["implementationVersion"]
            running_server_version_parts = running_server_version.split("-")

            expected_server_version_parts = expected_server_version.split("-")

            # Check both version parts if expected version contains a build
            if len(expected_server_version_parts) == 2:
                # 4.1.1-5487
                expected_server = "{}-{}".format(expected_server_version_parts[0], expected_server_version_parts[1])
                running_server = "{}-{}".format(running_server_version_parts[0], running_server_version_parts[1])
                logging.info("Expected Server Version: {}".format(expected_server))
                logging.info("Running Server Version: {}".format(running_server))
                if  expected_server != running_server:
                    raise ValueError("Unexpected server version!! Expected: {} Actual: {}".format(expected_server, running_server))
            elif len(expected_server_version_parts) == 1:
                # 4.1.1
                logging.info("Expected Server Version: {}".format(expected_server_version))
                logging.info("Running Server Version: {}".format(expected_server_version_parts[0]))
                if expected_server_version != running_server_version_parts[0]:
                    raise ValueError("Unexpected server version!! Expected: {} Actual: {}".format(expected_server, running_server))

        # Verify sync_gateway versions
        for sg in cluster_obj["sync_gateways"]:
            resp = requests.get("http://{}:4984".format(sg["ip"]))
            log_r(resp)
            resp.raise_for_status()
            resp_obj = resp.json()

            running_sg_version = resp_obj["version"]
            running_sg_version_parts = re.split("[ /(;)]", running_sg_version)
            running_sg_version_formatted = "{}-{}".format(running_sg_version_parts[3], running_sg_version_parts[4])

            logging.info("Expected sync_gateway Version: {}".format(expected_sync_gateway_version))
            logging.info("Running sync_gateway Version: {}".format(running_sg_version_formatted))

            if running_sg_version_formatted != expected_sync_gateway_version:
                raise ValueError("Unexpected sync_gateway version!! Expected: {} Actual: {}".format(expected_sync_gateway_version, running_sg_version_formatted))

        # Verify sg_accel versions
        for ac in cluster_obj["sg_accels"]:
            resp = requests.get("http://{}:4985".format(ac["ip"]))
            log_r(resp)
            resp.raise_for_status()
            resp_obj = resp.json()

            running_ac_version = resp_obj["version"]
            running_ac_version_parts = re.split("[ /(;)]", running_ac_version)
            running_ac_version_formatted = "{}-{}".format(running_ac_version_parts[3], running_ac_version_parts[4])

            logging.info("Expected sync_gateway Version: {}".format(expected_sync_gateway_version))
            logging.info("Running sync_gateway Version: {}".format(running_ac_version_formatted))

            if running_ac_version_formatted != expected_sync_gateway_version:
                raise ValueError("Unexpected sg_accell version!! Expected: {} Actual: {}".format(expected_sync_gateway_version, running_ac_version_formatted))




