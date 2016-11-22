import os

from libraries.provision.ansible_runner import AnsibleRunner

from keywords.utils import log_info


def push_cbcollect_info_supportal(cluster_config):
    """
    1. Runs cbcollect_info on one of the couchbase server nodes
    2. Pushes to supportal.couchbase.com
    """
    ansible_runner = AnsibleRunner(config=cluster_config)
    status = ansible_runner.run_ansible_playbook("push-cbcollect-info-supportal.yml")
    assert status == 0, "Failed to push cbcollect info"


if __name__ == "__main__":

    try:
        cluster_conf = os.environ["CLUSTER_CONFIG"]
    except KeyError as ke:
        log_info("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        raise KeyError("CLUSTER_CONFIG not defined. Unable to provision cluster.")

    push_cbcollect_info_supportal(cluster_conf)
