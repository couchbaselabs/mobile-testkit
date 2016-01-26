import os.path
import shutil
from provision.ansible_runner import run_ansible_playbook


def push_cbcollect_info_supportal():
    """
    1. Runs cbcollect_info on one of the couchbase server nodes
    2. Pushes to supportal.couchbase.com
    """
    run_ansible_playbook("push-cbcollect-info-supportal.yml")
    

if __name__ == "__main__":
    push_cbcollect_info_supportal()
