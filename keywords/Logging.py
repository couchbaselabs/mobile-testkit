from libraries.provision.ansible_runner import AnsibleRunner

import os.path
import shutil
import time

from utilities import scan_logs
from keywords.utils import log_info
from keywords.exceptions import CollectionError
from keywords.constants import RESULTS_DIR


def fetch_sync_gateway_logs(cluster_config, prefix):
    ansible_runner = AnsibleRunner(cluster_config)

    log_info("Pulling sync_gateway / sg_accel logs")
    # fetch logs from sync_gateway instances
    status = ansible_runner.run_ansible_playbook("fetch-sync-gateway-logs.yml")
    if status != 0:
        raise CollectionError("Could not pull logs")

    # zip logs and timestamp
    if os.path.isdir("/tmp/sg_logs"):

        date_time = time.strftime("%Y-%m-%d-%H-%M-%S")
        temp_log_path = "/tmp/{}-{}-sglogs".format(prefix, date_time)
        shutil.make_archive(temp_log_path, "zip", "/tmp/sg_logs")
        shutil.rmtree("/tmp/sg_logs")

        # Copy logs to results dir
        zip_file_path = "{}.zip".format(temp_log_path)
        log_results_location = "{}/logs".format(RESULTS_DIR)
        shutil.copy(zip_file_path, log_results_location)

        zip_name = "{}-{}-sglogs.zip".format(prefix, date_time)
        result_zip = "{}/{}".format(log_results_location, zip_name)
        log_info("sync_gateway logs copied to {}".format(result_zip))

        return result_zip
    else:
        raise CollectionError("Error finding pulled logs at /tmp/sg_logs")


class Logging:

    def fetch_and_analyze_logs(self, cluster_config, test_name):

        # Replace '/' with '-' to avoid strange partial naming of file
        # when copying the file from /tmp/ to results/logs
        test_name = test_name.replace("/", "-")

        zip_file_path = fetch_sync_gateway_logs(
            cluster_config=cluster_config,
            prefix=test_name
        )

        # TODO: https://github.com/couchbaselabs/mobile-testkit/issues/707
        log_info("TODO: Running Analysis: {}".format(zip_file_path))
