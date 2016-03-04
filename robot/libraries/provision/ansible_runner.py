import os
import sys
import subprocess


class AnsibleRunner:

    def __init__(self, provisioning_config):
        self.provisiong_config = provisioning_config

    def run_ansible_playbook(self, script_name, extra_vars=None, stop_on_fail=True):

        # Need to cd here to pick up dynamic inventory
        os.chdir("libraries/provision/ansible/playbooks")

        if not os.path.isfile(script_name):
            print("Could not locate ansible script {0} in {1}".format(script_name, os.getcwd()))
            sys.exit(1)

        if extra_vars is not None:
            status = subprocess.call(["ansible-playbook", "-i", "../../../../{}".format(self.provisiong_config), script_name, "--extra-vars", extra_vars])
        else:
            status = subprocess.call(["ansible-playbook", "-i", "../../../../{}".format(self.provisiong_config), script_name])

        if status != 0 and stop_on_fail:
            sys.exit(1)

        os.chdir("../../../../")

        return status

    def run_targeted_ansible_playbook(self, script_name, target_name, extra_vars=None, stop_on_fail=True):

        # Need to cd here to pick up dynamic inventory
        os.chdir("librarys/provision/ansible/playbooks")

        if not os.path.isfile(script_name):
            print("Could not locate ansible script {0} in {1}".format(script_name, os.getcwd()))
            sys.exit(1)

        if extra_vars is not None:
            status = subprocess.call(["ansible-playbook", "-i", "../../../../{}".format(self.provisiong_config), script_name, "--extra-vars", extra_vars, "--limit", target_name])
        else:
            status = subprocess.call(["ansible-playbook", "-i", "../../../../{}".format(self.provisiong_config), script_name, "--limit", target_name])

        if status != 0 and stop_on_fail:
            sys.exit(1)

        os.chdir("../../../../")

        return status


