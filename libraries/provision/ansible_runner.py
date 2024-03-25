from utilities.cluster_config_utils import get_sg_platform
from libraries.provision.ansible_python_runner import Runner
from ansible import constants
import logging
import os

PLAYBOOKS_HOME = "libraries/provision/ansible/playbooks"


class AnsibleRunner:

    def __init__(self, config):
        self.provisiong_config = config

    def run_ansible_playbook(self, script_name, extra_vars={}, subset=constants.DEFAULT_SUBSET):
        sg_platform = "debian"
        if os.path.isfile(self.provisiong_config + ".json"):
            sg_platform = get_sg_platform(self.provisiong_config)
        if "debian" in sg_platform.lower():
            extra_vars["ansible_distribution"] = sg_platform.capitalize()
            extra_vars["ansible_os_family"] = "Linux"
            extra_vars["ansible_python_interpreter"] = "/usr/bin/python3"
        inventory_filename = self.provisiong_config + ".json"

        playbook_filename = "{}/{}".format(PLAYBOOKS_HOME, script_name)

        runner = Runner(
            inventory_filename=inventory_filename,
            playbook=playbook_filename,
            extra_vars=extra_vars,
            verbosity=0,  # change this to a higher number for -vvv debugging (try 10),
            subset=subset
        )

        stats = runner.run()
        logging.info(stats)
        return len(stats.failures) + len(stats.dark)
