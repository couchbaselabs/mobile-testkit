import logging
import os

import requests

import libraries.testkit.settings
from libraries.provision.ansible_runner import AnsibleRunner
from utilities.cluster_config_utils import is_cbs_ssl_enabled
from utilities.cluster_config_utils import get_sg_version
from keywords.exceptions import ProvisioningError

log = logging.getLogger(libraries.testkit.settings.LOGGER)


class SgAccel:

    def __init__(self, cluster_config, target):
        self.ansible_runner = AnsibleRunner(cluster_config)
        self.ip = target["ip"]
        self.url = "http://{}:4985".format(target["ip"])
        self.hostname = target["name"]
        self.cluster_config = cluster_config
        self.server_port = 8091
        self.server_scheme = "http"

        if is_cbs_ssl_enabled(self.cluster_config):
            self.server_port = 18091
            self.server_scheme = "https"

    def info(self):
        r = requests.get(self.url)
        r.raise_for_status()
        return r.text

    def stop(self):
        status = self.ansible_runner.run_ansible_playbook(
            "stop-sg-accel.yml",
            subset=self.hostname
        )
        return status

    def start(self, config):
        conf_path = os.path.abspath(config)
        log.info(">>> Starting sg_accel with configuration: {}".format(conf_path))

        playbook_vars = {
            "sync_gateway_config_filepath": conf_path,
            "server_port": self.server_port,
            "server_scheme": self.server_scheme
        }
        if is_cbs_ssl_enabled(self.cluster_config) and get_sg_version(self.cluster_config) >= "1.5.0":
            playbook_vars["server_scheme"] = "couchbases"
            # playbook_vars["server_port"] = "11210"
            status = self.ansible_runner.run_ansible_playbook(
                "block-http-ports.yml"
            )
            if status != 0:
                raise ProvisioningError("Failed to install sync_gateway source")
        status = self.ansible_runner.run_ansible_playbook(
            "start-sg-accel.yml",
            extra_vars=playbook_vars,
            subset=self.hostname
        )
        return status

    def __repr__(self):
        return "SgAccel: {}:{}\n".format(self.hostname, self.ip)
