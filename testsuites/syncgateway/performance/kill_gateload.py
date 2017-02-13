import os
import subprocess
from libraries.provision.ansible_runner import AnsibleRunner
from keywords.exceptions import ProvisioningError

def kill_gateload():
    try:
        cluster_config = os.environ["CLUSTER_CONFIG"]
    except KeyError:
        print ("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        sys.exit(1)

    print("Running perf test against cluster: {}".format(cluster_config))
    ansible_runner = AnsibleRunner(cluster_config)

    status = ansible_runner.run_ansible_playbook("kill-gateload.yml")
    if status != 0:
        raise ProvisioningError("Failed to kill gatelaod")


if __name__ == "__main__":
    kill_gateload()
