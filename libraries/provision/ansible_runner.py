import os
import sys
import subprocess
from ansible_python_runner import Runner
import re
import logging
from ansible import constants
from robot.api.logger import console

class AnsibleRunner:

    def __init__(self):
        self.provisiong_config = os.environ["CLUSTER_CONFIG"]

    def run_ansible_playbook(self, script_name, extra_vars=None, stop_on_fail=True, subset=constants.DEFAULT_SUBSET):

        # parse key=value pairs into dictionary
        # shamelessly copied n pasted from http://bit.ly/1syhZ31
        run_data = {}
        if extra_vars is not None and len(extra_vars) > 0:
            run_data = dict(re.findall(r'(\S+)=(".*?"|\S+)', extra_vars))

        inventory_filename = self.provisiong_config

        playbook_filename = "libraries/provision/ansible/playbooks/{}".format(script_name)

        runner = Runner(
            inventory_filename=inventory_filename,
            playbook = playbook_filename,
            run_data = run_data,
            verbosity = 0,  # change this to a higher number for -vvv debugging (try 10),
            subset = subset
        )

        stats = runner.run()

        # return a 0 exit code (success) if no failures, otherwise return non-zero exit code
        return len(stats.failures)

    def run_targeted_ansible_playbook(self, script_name, target_name, extra_vars=None, stop_on_fail=True):

        return self.run_ansible_playbook(
            script_name=script_name,
            extra_vars=extra_vars,
            stop_on_fail=stop_on_fail,
            subset = target_name
        )




