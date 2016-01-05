import os.path
import shutil
import time
import logging
import lib.settings

log = logging.getLogger(lib.settings.LOGGER)

from provision.ansible_runner import run_ansible_playbook


def fetch_sync_gateway_logs(prefix, is_perf_run=False):

    print("\n\n\n")

    log.info("Pulling logs")
    # fetch logs from sync_gateway instances
    run_ansible_playbook("fetch-sync-gateway-logs.yml")

    # zip logs and timestamp
    if os.path.isdir("/tmp/sg_logs"):

        date_time = time.strftime("%Y-%m-%d-%H-%M-%S")

        if is_perf_run:
            name = "/tmp/{}-sglogs".format(prefix)
        else:
            name = "/tmp/{}-{}-sglogs".format(prefix, date_time)

        shutil.make_archive(name, "zip", "/tmp/sg_logs")

        shutil.rmtree("/tmp/sg_logs")
        log.info("sync_gateway logs copied here {}\n".format(name))

        print(name)

        if is_perf_run:
            # Move perf logs to performance_results
            shutil.copy("{}.zip".format(name), "performance_results/{}/".format(prefix))

    print("\n\n\n")


if __name__ == "__main__":
    fetch_sync_gateway_logs(prefix="snapshot")
