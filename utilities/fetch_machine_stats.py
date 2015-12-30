import os.path
import shutil
import time
import logging
import lib.settings

log = logging.getLogger(lib.settings.LOGGER)

from provision.ansible_runner import run_ansible_playbook


def fetch_machine_stats(folder_name):

    print("\n\n\n")

    log.info("Pulling logs")
    # fetch logs from sync_gateway instances
    run_ansible_playbook("fetch-machine-stats.yml")

    # zip logs and timestamp
    if os.path.isdir("/tmp/perf_logs"):

        # Move perf logs to performance_results
        shutil.move("/tmp/perf_logs", "performance_results/{}/".format(folder_name))

    print("\n\n\n")


if __name__ == "__main__":
    fetch_machine_stats()
