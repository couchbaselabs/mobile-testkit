from libraries.provision.ansible_runner import AnsibleRunner

from subprocess import Popen, PIPE
import os.path
import shutil
import time
import pdb

from keywords.utils import log_info
from keywords.utils import log_warn
from keywords.utils import log_error
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

        zip_file_path = fetch_sync_gateway_logs(
            cluster_config=cluster_config,
            prefix=test_name
        )

        log_info("Analyzing: {}".format(zip_file_path))

        if self.detected_data_races(zip_file_path):
            log_error("Detected data races in logs: {}".format(zip_file_path))
        else:
            log_info("No 'DATA RACES' detected in sync_gateway logs")

        if self.detected_panics(zip_file_path):
            log_error("Detected panics in logs: {}".format(zip_file_path))
        else:
            log_info("No 'panics' detected in sync_gateway logs")

    def detected_data_races(self, zip_file_path):
        return self.detected_pattern("DATA RACE", zip_file_path)

    def detected_panics(self, zip_file_path):
        return self.detected_pattern("panic", zip_file_path)

    def detected_pattern(self, pattern, zip_file_path):

        if not zip_file_path:
            raise IOError("File not found")

        if not os.path.isfile(zip_file_path):
            log_error("Can't run zipgrep, cannot find zipfile: {}".format(zip_file_path))
            raise IOError("File not found")

        log_info("Looking for '{}' in {}".format(pattern, zip_file_path))
        process = Popen(["zipgrep", pattern, zip_file_path], stdout=PIPE)
        (output, err) = process.communicate()

        exit_code = process.wait()
        if exit_code == 0:
            log_info(output)
            log_info(err)
            log_info("Detected pattern {}: {}".format(pattern, output))
            raise RuntimeError("DATA RACE or panic found!")

        return False






