import os.path
import shutil
from provision.ansible_runner import run_ansible_playbook


def fetch_sync_gateway_profile(folder_name):

    print("\n")

    print("Pulling sync_gateway profile ...")
    # fetch logs from sync_gateway instances
    run_ansible_playbook("fetch-sync-gateway-profile.yml")

    # zip logs and timestamp
    if os.path.isdir("/tmp/sync_gateway_profile"):

        # Move perf logs to performance_results
        shutil.move("/tmp/sync_gateway_profile", "performance_results/{}/".format(folder_name))

    print("\n")


if __name__ == "__main__":
    fetch_sync_gateway_profile()
