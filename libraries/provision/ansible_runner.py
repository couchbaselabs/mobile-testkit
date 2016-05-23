import os
import sys
import subprocess
from ansible_python_runner import Runner
import re
import logging

class AnsibleRunner:

    def __init__(self):
        self.provisiong_config = os.environ["CLUSTER_CONFIG"]

    def run_ansible_playbook(self, script_name, extra_vars=None, stop_on_fail=True):

        print "run_ansible_playbook called with script_name: {} extra_vars: {}".format(script_name, extra_vars)
        print "os.path.realpath(__file__): {}".format(os.path.realpath(__file__))

        # parse key=value pairs into dictionary
        # shamelessly copied n pasted from http://bit.ly/1syhZ31
        run_data = dict(re.findall(r'(\S+)=(".*?"|\S+)', extra_vars))

        print "extra_vars parsed into run_data: {}".format(run_data)

        # inventory_filename, playbook, run_data, verbosity = 0):
        # inventory_filename = "../../{}".format(self.provisiong_config)
        print "provisiong_config: {}".format(self.provisiong_config)
        inventory_filename = "/Users/tleyden/Development/mobile-testkit/{}".format(self.provisiong_config)

        playbook_filename = "/Users/tleyden/Development/mobile-testkit/libraries/provision/ansible/playbooks/{}".format(script_name)

        print("creating runner with inventory_filename: {}".format(inventory_filename))

        runner = Runner(
            inventory_filename=inventory_filename,
            playbook = playbook_filename,
            run_data = run_data,
            verbosity = 10
        )

        print("calling runner")
        stats = runner.run()

        """
        stats fields:

        self.processed = {}
        self.failures  = {}
        self.ok        = {}
        self.dark      = {}
        self.changed   = {}
        self.skipped   = {}
        """
        print("stats.processed: {}".format(stats.processed))
        print("stats.failures: {}".format(stats.failures))
        print("stats.ok: {}".format(stats.ok))
        print("stats.dark: {}".format(stats.dark))
        print("stats.changed: {}".format(stats.changed))
        print("stats.skipped: {}".format(stats.skipped))

        return 0  # TODO: if ansible command failed, return an error ..


    def run_targeted_ansible_playbook(self, script_name, target_name, extra_vars=None, stop_on_fail=True):

        # Need to cd here to pick up dynamic inventory
        os.chdir("libraries/provision/ansible/playbooks")

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


