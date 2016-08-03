import os

from ansible_runner import AnsibleRunner


if __name__ == "__main__":
    usage = "usage: python install_deps.py"

    try:
        cluster_config = os.environ["CLUSTER_CONFIG"]
    except KeyError as ke:
        print ("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        raise KeyError("CLUSTER_CONFIG not defined. Unable to provision cluster.")

    ansible_runner = AnsibleRunner()
    status = ansible_runner.run_ansible_playbook("os-level-modifications.yml")
    assert status == 0, "Failed to make os modifications"

    status = ansible_runner.run_ansible_playbook("install-common-tools.yml")
    assert status == 0, "Failed to install dependencies"