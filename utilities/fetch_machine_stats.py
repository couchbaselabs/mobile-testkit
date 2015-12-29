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

        date_time = time.strftime("%Y-%m-%d-%H-%M-%S")
        name = "/tmp/{}-machine-stats".format(date_time)

        shutil.make_archive(name, "zip", "/tmp/perf_logs")

        shutil.rmtree("/tmp/perf_logs")
        log.info("perf_logs logs copied here {}\n".format(name))

        shutil.copy("{}.zip".format(name), "performance_results/{}/".format(folder_name))

    print("\n\n\n")


if __name__ == "__main__":
    fetch_machine_stats()
