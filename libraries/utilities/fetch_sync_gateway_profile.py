import os.path
import shutil
import time
from libraries.provision.ansible_runner import AnsibleRunner
from keywords.utils import log_info


def fetch_sync_gateway_profile(cluster_config, folder_name):

    max_num_attempts = 20

    for attempt_number in range(max_num_attempts):

        try:

            ansible_runner = AnsibleRunner(config=cluster_config)

            print("\n")

            print("Pulling sync_gateway profile.  Attempt #{}".format(attempt_number))
            # fetch logs from sync_gateway instances
            status = ansible_runner.run_ansible_playbook("fetch-sync-gateway-profile.yml")
            if status != 0:
                raise Exception("Failed to fetch sync_gateway profile")

            # zip logs and timestamp
            if os.path.isdir("/tmp/sync_gateway_profile"):

                # Move perf logs to performance_results
                shutil.move("/tmp/sync_gateway_profile", "testsuites/syncgateway/performance/results/{}/".format(folder_name))

            print("\n")
            return

        except Exception as e:
            log_info("Exception trying to collect sync gateway profile: {}", e)
            if attempt_number < (max_num_attempts - 1):
                log_info("Going to retry.  So far {}/{} attempts".format(attempt_number, max_num_attempts))
                time.sleep(30)
            else:
                log_info("Exhausted attempts.  Giving up")

        attempt_number += 1
