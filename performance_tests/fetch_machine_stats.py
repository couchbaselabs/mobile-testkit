import os
import subprocess


def fetch_machine_stats():
    os.chdir("performance_tests/ansible/playbooks")
    subprocess.call(["ansible-playbook", "-i", "../../../provisioning_config", "fetch-machine-stats.yml"])

if __name__ == "__main__":
    fetch_machine_stats()