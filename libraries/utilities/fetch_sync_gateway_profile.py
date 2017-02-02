import os.path
import shutil
import sys

from libraries.provision.ansible_runner import AnsibleRunner


def fetch_sync_gateway_profile(cluster_config, folder_name):

    ansible_runner = AnsibleRunner(config=cluster_config)

    print("\n")

    print("Pulling sync_gateway profile ...")
    # fetch logs from sync_gateway instances
    status = ansible_runner.run_ansible_playbook("fetch-sync-gateway-profile.yml")
    assert status == 0, "Failed to fetch sync_gateway profile"

    # zip logs and timestamp
    if os.path.isdir("/tmp/sync_gateway_profile"):

        # Move perf logs to performance_results
        shutil.move("/tmp/sync_gateway_profile", "testsuites/syncgateway/performance/results/{}/".format(folder_name))

    print("\n")




if __name__ == "__main__":

    try:
        cluster_config = os.environ["CLUSTER_CONFIG"]
    except KeyError:
        print ("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        sys.exit(1)

    folder_name = "profile"  # TODO: not really sure what to use here..

    fetch_sync_gateway_profile(cluster_config, folder_name)