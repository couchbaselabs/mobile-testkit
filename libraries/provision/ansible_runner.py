import os
import sys
import subprocess
from ansible_python_runner import Runner
import re
import logging
from ansible import constants
from robot.api.logger import console
from ansible.utils.vars import load_extra_vars
from ansible.parsing.dataloader import DataLoader



class AnsibleRunner:

    def __init__(self):
        self.provisiong_config = os.environ["CLUSTER_CONFIG"]

    def run_ansible_playbook(self, script_name, extra_vars={}, stop_on_fail=True, subset=constants.DEFAULT_SUBSET):

        console("run_ansible_playbook called with playbook: {}".format(script_name))

        inventory_filename = self.provisiong_config

        playbook_filename = "libraries/provision/ansible/playbooks/{}".format(script_name)

        runner = Runner(
            inventory_filename=inventory_filename,
            playbook = playbook_filename,
            extra_vars = extra_vars,
            verbosity = 0,  # change this to a higher number for -vvv debugging (try 10),
            subset = subset
        )

        stats = runner.run()

        console(
            "stats.changed: {} stats.failures: {} stats.processed: {} stats.skipped: {} stats.ok: {}".format(
                stats.changed,
                stats.failures,
                stats.processed,
                stats.skipped,
                stats.ok
            )
        )

        # return a 0 exit code (success) if no failures, otherwise return non-zero exit code

        return len(stats.failures)

    def run_targeted_ansible_playbook(self, script_name, target_name, extra_vars={}, stop_on_fail=True):

        return self.run_ansible_playbook(
            script_name=script_name,
            extra_vars=extra_vars,
            stop_on_fail=stop_on_fail,
            subset = target_name
        )




