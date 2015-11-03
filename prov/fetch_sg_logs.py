import os.path
import shutil
import time

from ansible_runner import run_ansible_playbook


def fetch_sync_gateway_logs():

    # fetch logs from sync_gateway instances
    run_ansible_playbook("fetch-sync-gateway-logs.yml")

    # zip logs, rename, and copy to desktop
    if os.path.isdir("/tmp/sg_logs"):
        date_time = time.strftime("%Y-%m-%d-%H-%M-%S")
        name = "/tmp/{}-sglogs".format(date_time)

        shutil.make_archive(name, "zip", "/tmp/sg_logs")
        home = os.environ["HOME"]

        shutil.copy("{}.zip".format(name), "{}/Desktop".format(home))
        shutil.rmtree("/tmp/sg_logs")
        print(">>> Copied {}.zip to {}/Desktop".format(name, home))


if __name__ == "__main__":
    fetch_sync_gateway_logs()
