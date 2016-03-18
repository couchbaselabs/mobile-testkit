import os
import requests

import testkit.settings
import logging
log = logging.getLogger(testkit.settings.LOGGER)

from provision.ansible_runner import AnsibleRunner

class SyncGateway:

    def __init__(self, target):
        self.ansible_runner = AnsibleRunner()
        self.ip = target["ip"]
        self.url = "http://{}:4984".format(target["ip"])
        self.hostname = target["name"]

    def info(self):
        r = requests.get(self.url)
        r.raise_for_status()
        return r.text

    def stop(self):
        status = self.ansible_runner.run_targeted_ansible_playbook(
            "stop-sync-gateway.yml",
            target_name=self.hostname,
            stop_on_fail=False,
        )
        return status

    def start(self, config):

        conf_path = os.path.abspath(config)

        log.info(">>> Starting sync_gateway with configuration: {}".format(conf_path))

        status = self.ansible_runner.run_targeted_ansible_playbook(
            "start-sync-gateway.yml",
            extra_vars="sync_gateway_config_filepath={0}".format(conf_path),
            target_name=self.hostname,
            stop_on_fail=False
        )
        return status

    def restart(self, config):
        conf_path = os.path.abspath(config)

        log.info(">>> Restarting sync_gateway with configuration: {}".format(conf_path))

        status = self.ansible_runner.run_targeted_ansible_playbook(
            "reset-sync-gateway.yml",
            extra_vars="sync_gateway_config_filepath={0}".format(conf_path),
            target_name=self.hostname,
            stop_on_fail=False
        )
        return status

    def __repr__(self):
        return "SyncGateway: {}:{}\n".format(self.hostname, self.ip)
