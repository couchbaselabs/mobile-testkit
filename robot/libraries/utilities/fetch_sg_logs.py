import os.path
import shutil
import time

from provision.ansible_runner import AnsibleRunner

import logging
import testkit.settings
log = logging.getLogger(testkit.settings.LOGGER)

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
        print("sync_gateway logs copied here {}\n".format(name))

        zip_file_path = "{}.zip".format(name)
        if is_perf_run:
            # Move perf logs to performance_results
            shutil.copy(zip_file_path, "results/{}/".format(prefix))

        print("\n")
        
        return zip_file_path


if __name__ == "__main__":
    fetch_sync_gateway_logs(prefix="snapshot")
