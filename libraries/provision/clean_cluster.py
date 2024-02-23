import os

from libraries.provision.ansible_runner import AnsibleRunner
from keywords.exceptions import ProvisioningError
from keywords.utils import log_info


def clean_cluster(cluster_config, skip_couchbase_provision=False, sg_platform="centos"):

    log_info("Cleaning cluster: {}".format(cluster_config))
    ansible_runner = AnsibleRunner(config=cluster_config)
    if "centos" in sg_platform:
        status = ansible_runner.run_ansible_playbook("remove-sg-centos.yml")
    else:
        extra_vars = {
            "ansible_python_interpreter": "/usr/bin/python3"
        }
        if "debian" in sg_platform.lower():
            extra_vars["ansible_distribution"] = sg_platform.capitalize()
            extra_vars["ansible_os_family"] = "Linux"
        status = ansible_runner.run_ansible_playbook("remove-previous-installs.yml", extra_vars)

    if status != 0:
        raise ProvisioningError("Failed to removed previous installs")

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
    except KeyError:
        log_info("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        raise KeyError("CLUSTER_CONFIG not defined. Unable to provision cluster.")

    clean_cluster(cluster_config=cluster_conf)
