import os

from ansible_runner import AnsibleRunner


if __name__ == "__main__":
    usage = "usage: python stop_telegraf.py"

    try:
        cluster_config = os.environ["CLUSTER_CONFIG"]
    except KeyError as ke:
        print ("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to run against")
        raise KeyError("CLUSTER_CONFIG not defined. Unable to stop telegraf collectors.")

    ansible_runner = AnsibleRunner(cluster_config)
    status = ansible_runner.run_ansible_playbook("stop-telegraf.yml")
    assert status == 0, "Failed to stop telegraf collectors"
