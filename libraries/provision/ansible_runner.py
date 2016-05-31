import os
from ansible_python_runner import Runner
from ansible import constants
import logging

class AnsibleRunner:

    def __init__(self):
        self.provisiong_config = os.environ["CLUSTER_CONFIG"]

    def run_ansible_playbook(self, script_name, extra_vars={}, stop_on_fail=True, subset=constants.DEFAULT_SUBSET):

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
        logging.info(stats)

        return len(stats.failures)

    def run_targeted_ansible_playbook(self, script_name, target_name, extra_vars={}, stop_on_fail=True):

        return self.run_ansible_playbook(
            script_name=script_name,
            extra_vars=extra_vars,
            stop_on_fail=stop_on_fail,
            subset = target_name
        )




