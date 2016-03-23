
from provision.ansible_runner import AnsibleRunner


def push_cbcollect_info_supportal():
    """
    1. Runs cbcollect_info on one of the couchbase server nodes
    2. Pushes to supportal.couchbase.com
    """
    ansible_runner = AnsibleRunner()
    ansible_runner.run_ansible_playbook("push-cbcollect-info-supportal.yml")
    

if __name__ == "__main__":
    push_cbcollect_info_supportal()
