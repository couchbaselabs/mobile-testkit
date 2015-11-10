import os
import requests

from provision.ansible_runner import run_targeted_ansible_playbook

class SyncGateway:

    def __init__(self, target):
        self.ip = target["ip"]
        self.url = "http://{}:4984".format(target["ip"])
        self.hostname = target["name"]

    def info(self):
        r = requests.get(self.url)
        r.raise_for_status()
        return r.text

    def stop(self):
        run_targeted_ansible_playbook(
            "stop-sync-gateway.yml",
            target_name=self.hostname
        )

    def start(self, config):
        conf_path = os.path.abspath("conf/" + config)

        print(">>> Starting sync_gateway with configuration: {}".format(conf_path))

        run_targeted_ansible_playbook(
            "start-sync-gateway.yml",
            extra_vars="sync_gateway_config_filepath={0}".format(conf_path),
            target_name=self.hostname
        )

    def restart(self, config):
        conf_path = os.path.abspath("conf/" + config)

        print(">>> Restarting sync_gateway with configuration: {}".format(conf_path))

        run_targeted_ansible_playbook(
            "reset-sync-gateway.yml",
            extra_vars="sync_gateway_config_filepath={0}".format(conf_path),
            target_name=self.hostname
        )

    def __repr__(self):
        return "SyncGateway: {}:{}\n".format(self.host_name, self.ip)
