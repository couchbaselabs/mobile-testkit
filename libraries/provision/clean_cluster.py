import os

from ansible_runner import AnsibleRunner
from keywords.exceptions import ProvisioningError
from keywords.utils import log_info


def clean_cluster(cluster_config):

    log_info("Cleaning cluster: {}".format(cluster_config))

    ansible_runner = AnsibleRunner(config=cluster_config)
    status = ansible_runner.run_ansible_playbook("remove-previous-installs.yml")
    if status != 0:
        raise ProvisioningError("Failed to removed previous installs")

    # Clear firewall rules
    status = ansible_runner.run_ansible_playbook("flush-firewall.yml")
    if status != 0:
        raise ProvisioningError("Failed to flush firewall")


if __name__ == "__main__":
    usage = "usage: python clean_cluster.py"

    try:
        cluster_conf = os.environ["CLUSTER_CONFIG"]
    except KeyError as ke:
        log_info("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        raise KeyError("CLUSTER_CONFIG not defined. Unable to provision cluster.")

    clean_cluster(cluster_config=cluster_conf)
