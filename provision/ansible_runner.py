import os
import sys
import subprocess

# TODO provide a way to specify inventory (perhaps local or private vm endpoints)


def run_ansible_playbook(script_name, extra_vars=None):

    # Need to cd here to pick up dynamic inventory
    os.chdir("provision/ansible/playbooks")

    if not os.path.isfile(script_name):
        print("Could not locate ansible script {0} in {1}".format(script_name, os.getcwd()))
        sys.exit(1)

    if extra_vars is not None:
        status = subprocess.call(["ansible-playbook", "-i", "../../../provisioning_config", script_name, "--extra-vars", extra_vars])
    else:
        status = subprocess.call(["ansible-playbook", "-i", "../../../provisioning_config", script_name])

    if status != 0:
        sys.exit(1)

    os.chdir("../../../")

def run_targeted_ansible_playbook(script_name, target_name, extra_vars=None):

    # Need to cd here to pick up dynamic inventory
    os.chdir("provision/ansible/playbooks")

    if not os.path.isfile(script_name):
        print("Could not locate ansible script {0} in {1}".format(script_name, os.getcwd()))
        sys.exit(1)

    if extra_vars is not None:
        status = subprocess.call(["ansible-playbook", "-i", "../../../provisioning_config", script_name, "--extra-vars", extra_vars, "--limit", target_name])
    else:
        status = subprocess.call(["ansible-playbook", "-i", "../../../provisioning_config", script_name, "--limit", target_name])

    if status != 0:
        sys.exit(1)

    os.chdir("../../../")


