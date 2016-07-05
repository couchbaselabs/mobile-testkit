import os
from ansible_python_runner import Runner
from ansible import constants
import logging

PLAYBOOKS_HOME="libraries/provision/ansible/playbooks"

class AnsibleRunner:

    def __init__(self):
        self.provisiong_config = os.environ["CLUSTER_CONFIG"]

    def run_ansible_playbook(self, script_name, extra_vars={}, subset=constants.DEFAULT_SUBSET):

        inventory_filename = self.provisiong_config

        playbook_filename = "{}/{}".format(PLAYBOOKS_HOME, script_name)

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