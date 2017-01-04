import os
import subprocess


def kill_gateload():
    os.chdir("performance_tests/ansible/playbooks")
    subprocess.call(["ansible-playbook", "-i", "../../../provisioning_config", "kill-gateload.yml"])


if __name__ == "__main__":
    kill_gateload()
