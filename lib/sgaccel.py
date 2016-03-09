import os
import requests

import lib.settings
import logging
log = logging.getLogger(lib.settings.LOGGER)

from provision.ansible_runner import run_targeted_ansible_playbook

class SgAccel:

    def __init__(self, target):
        self.ip = target["ip"]
        self.url = "http://{}:4985".format(target["ip"])
        self.hostname = target["name"]

    def info(self):
        r = requests.get(self.url)
        r.raise_for_status()
        return r.text

    def stop(self):
        status = run_targeted_ansible_playbook(
            "stop-sg-accel.yml",
            target_name=self.hostname,
            stop_on_fail=False,
        )
        return status

    def start(self, config):
        conf_path = os.path.abspath("conf/" + config)

        log.info(">>> Starting sg_accel with configuration: {}".format(conf_path))

        status = run_targeted_ansible_playbook(
            "start-sg-accel.yml",
            extra_vars="sync_gateway_config_filepath={0}".format(conf_path),
            target_name=self.hostname,
            stop_on_fail=False
        )
        return status

    def __repr__(self):
        return "SgAccel: {}:{}\n".format(self.hostname, self.ip)
