import os

from ansible_runner import AnsibleRunner


def clean_cluster():
    try:
        cluster_config = os.environ["CLUSTER_CONFIG"]
    except KeyError as ke:
        print ("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        raise KeyError("CLUSTER_CONFIG not defined. Unable to provision cluster.")

    print("Cleaning cluster: {}".format(cluster_config))

    ansible_runner = AnsibleRunner()
    status = ansible_runner.run_ansible_playbook("remove-previous-installs.yml", stop_on_fail=False)
    assert(status == 0)


if __name__ == "__main__":
    usage = "usage: python clean_cluster.py"
    clean_cluster()

