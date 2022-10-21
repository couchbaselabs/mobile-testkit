import os

from libraries.provision.ansible_runner import AnsibleRunner
from keywords.exceptions import ProvisioningError
from keywords.utils import log_info


def clean_cluster(cluster_config, skip_couchbase_provision=False, server_platform="centos"):

    log_info("Cleaning cluster: {}".format(cluster_config))
    ansible_runner = AnsibleRunner(config=cluster_config)
    if "centos" in server_platform:
        status = ansible_runner.run_ansible_playbook("remove-sg-centos.yml")
    else:
        status = ansible_runner.run_ansible_playbook("remove-previous-installs.yml")

    if status != 0:
        raise ProvisioningError("Failed to removed previous installs")

    # Clear firewall rules
    if not skip_couchbase_provision:
        status = ansible_runner.run_ansible_playbook("flush-cb-firewall.yml")
        if status != 0:
            raise ProvisioningError("Failed to flush firewall")

    # Clear firewall rules
    status = ansible_runner.run_ansible_playbook("flush-firewall.yml")
    if status != 0:
        raise ProvisioningError("Failed to flush firewall")

    # Reset to ntp time . Required for x509 tests to clock sync for couchbase server and sync gateway
    status = ansible_runner.run_ansible_playbook("reset-hosts.yml")
    if status != 0:
        raise ProvisioningError("Failed to reset hosts")

    if not skip_couchbase_provision:
        status = ansible_runner.run_ansible_playbook("reset-cb-hosts.yml")
        if status != 0:
            raise ProvisioningError("Failed to reset hosts")


def clear_firewall_rules(cluster_config):
    log_info("Flusing firewall before teardown: {}".format(cluster_config))

    ansible_runner = AnsibleRunner(config=cluster_config)
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
