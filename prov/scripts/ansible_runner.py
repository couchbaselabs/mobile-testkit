import os
import sys
import subprocess

# TODO provide a way to specify inventory (perhaps local or private vm endpoints)


def run_ansible_playbook(script_name, extra_vars=""):

    # Need to cd here to pick up dynamic inventory
    os.chdir("../ansible/playbooks")

    if not os.path.isfile(script_name):
        print ("Could not locate ansible script {0} in {1}".format(script_name, os.getcwd()))
        sys.exit(1)

    if extra_vars != "":
        subprocess.call(["ansible-playbook", "-i", os.path.expandvars("$INVENTORY"), script_name, "--extra-vars", extra_vars])
    else:
        subprocess.call(["ansible-playbook", "-i", os.path.expandvars("$INVENTORY"), script_name])

    os.chdir("../../scripts")

