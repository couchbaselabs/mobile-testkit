import testkit.settings

from libraries.provision.ansible_runner import AnsibleRunner

from subprocess import Popen, PIPE
import os.path
import shutil
import time

import logging
import testkit.settings
log = logging.getLogger(testkit.settings.LOGGER)

from constants import *

def fetch_sync_gateway_logs(prefix, is_perf_run=False):
    ansible_runner = AnsibleRunner()

    print("\n")

    print("Pulling logs")
    # fetch logs from sync_gateway instances
    status = ansible_runner.run_ansible_playbook("fetch-sync-gateway-logs.yml", stop_on_fail=False)
    if status != 0:
        log.error("Error pulling logs")

    # zip logs and timestamp
    if os.path.isdir("/tmp/sg_logs"):

        date_time = time.strftime("%Y-%m-%d-%H-%M-%S")

        if is_perf_run:
            name = "/tmp/{}-sglogs".format(prefix)
        else:
            name = "/tmp/{}-{}-sglogs".format(prefix, date_time)

        shutil.make_archive(name, "zip", "/tmp/sg_logs")

        shutil.rmtree("/tmp/sg_logs")

        # Copy logs to results dir
        zip_file_path = "{}.zip".format(name)
        shutil.copy(zip_file_path, "{}/".format(RESULTS_DIR))

        print("sync_gateway logs copied to {}/\n".format(RESULTS_DIR))

        if is_perf_run:
            # Move perf logs to performance_results
            shutil.copy(zip_file_path, "testsuites/syncgateway/performance/results/{}/".format(prefix))

        print("\n")

        return zip_file_path


class Logging:

    def fetch_and_analyze_logs(self, test_name):

        zip_file_path = fetch_sync_gateway_logs(test_name)

        if self.detected_data_races(zip_file_path):
            log.error("Detected data races in logs: {}".format(zip_file_path))
        else:
            log.info("No 'DATA RACES' detected in sync_gateway logs")

        if self.detected_panics(zip_file_path):
            log.error("Detected panics in logs: {}".format(zip_file_path))
        else:
            log.info("No 'panics' detected in sync_gateway logs")

    def detected_data_races(self, zip_file_path):
        return self.detected_pattern("DATA RACE", zip_file_path)

    def detected_panics(self, zip_file_path):
        return self.detected_pattern("panic", zip_file_path)

    def detected_pattern(self, pattern, zip_file_path):

        if not zip_file_path:
            return False

        try:
            if not os.path.isfile(zip_file_path):
                log.error("Can't run zipgrep, cannot find zipfile: {}".format(zip_file_path))
                return False

            process = Popen(["zipgrep", pattern, zip_file_path], stdout=PIPE)
            (output, err) = process.communicate()

            exit_code = process.wait()
            if exit_code != 0:
                logging.info(output)
                logging.info(err)
                log.info("Detected pattern {}: {}".format(pattern, output))
                return True

            return False

        except Exception as e:
            log.warn("Exception in detected_pattern(): {}".format(e))





