import os

from ansible_runner import AnsibleRunner
from keywords.exceptions import ProvisioningError

from keywords.utils import log_info


def install_deps(cluster_config):

    log_info("Installing dependencies for cluster_config: {}".format(cluster_config))

    ansible_runner = AnsibleRunner(config=cluster_config)
    status = ansible_runner.run_ansible_playbook("os-level-modifications.yml")
    if status != 0:
        raise ProvisioningError("Failed to make os modifications")

    status = ansible_runner.run_ansible_playbook("install-common-tools.yml")
    if status != 0:
        raise ProvisioningError("Failed to install dependencies")
    
if __name__ == "__main__":
    usage = "usage: python install_deps.py"

    try:
        cluster_conf = os.environ["CLUSTER_CONFIG"]
    except KeyError as ke:
        print ("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        raise KeyError("CLUSTER_CONFIG not defined. Unable to provision cluster.")

    install_deps(cluster_conf)
