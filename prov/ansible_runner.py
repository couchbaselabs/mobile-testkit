import os
import sys
import subprocess

# TODO provide a way to specify inventory (perhaps local or private vm endpoints)


def run_ansible_playbook(script_name, extra_vars=None):

    # Need to cd here to pick up dynamic inventory
    os.chdir("prov/ansible/playbooks")

    if not os.path.isfile(script_name):
        print("Could not locate ansible script {0} in {1}".format(script_name, os.getcwd()))
        sys.exit(1)

    if extra_vars is not None:
        subprocess.call(["ansible-playbook", "-i", os.path.expandvars("$INVENTORY"), script_name, "--extra-vars", extra_vars])
    else:
        subprocess.call(["ansible-playbook", "-i", os.path.expandvars("$INVENTORY"), script_name])

    os.chdir("../../../")

def run_targeted_ansible_playbook(script_name, target_name, extra_vars=None):

    # Need to cd here to pick up dynamic inventory
    os.chdir("prov/ansible/playbooks")

    if not os.path.isfile(script_name):
        print("Could not locate ansible script {0} in {1}".format(script_name, os.getcwd()))
        sys.exit(1)

    if extra_vars is not None:
        subprocess.call(["ansible-playbook", "-i", os.path.expandvars("$INVENTORY"), script_name, "--extra-vars", extra_vars, "--limit", target_name])
    else:
        subprocess.call(["ansible-playbook", "-i", os.path.expandvars("$INVENTORY"), script_name, "--limit", target_name])

    os.chdir("../../../")


