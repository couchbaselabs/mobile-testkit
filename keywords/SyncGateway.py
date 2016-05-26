import tarfile
import os
import shutil
import logging
import time
import re

from jinja2 import Template
import requests
from requests import Session
from requests import ConnectionError

from constants import *
from utils import version_and_build
from utils import hostname_for_url
from libraries.provision.ansible_runner import AnsibleRunner

class SyncGateway:

    def __init__(self):
        self._session = Session()

    def verify_sync_gateway_launched(self, host, port, admin_port):

        url = "http://{}:{}".format(host, port)
        admin_url = "http://{}:{}".format(host, admin_port)

        count = 0
        wait_time = 1
        while count < MAX_RETRIES:
            try:
                resp = self._session.get(url)
                # If request does not throw, exit retry loop
                break
            except ConnectionError as ce:
                logging.info("Sync Gateway may not be launched (Retrying): {}".format(ce))
                time.sleep(wait_time)
                count += 1
                wait_time *= 2

        if count == MAX_RETRIES:
            raise RuntimeError("Could not connect to Sync Gateway")

        # Get version from running sync_gateway and compare with expected version
        resp_json = resp.json()
        logging.info(resp_json)
        sync_gateway_version = resp_json["version"]
        resp_version_parts = re.split("[ /(;)]", sync_gateway_version)
        actual_version = "{}-{}".format(resp_version_parts[3], resp_version_parts[4])

        logging.info("Expected Version {}".format(self._version_build))
        logging.info("Actual Version {}".format(actual_version))

        assert (actual_version == self._version_build)

        logging.info("{} is running".format(sync_gateway_version))

        return url, admin_url

    def start_sync_gateway(self, url, config):
        target = hostname_for_url(url)
        logging.info("Starting sync_gateway on {} ...".format(target))
        ansible_runner = AnsibleRunner()
        config_path =  os.path.abspath(config)
        status = ansible_runner.run_targeted_ansible_playbook(
            "start-sync-gateway.yml",
            extra_vars={
                "sync_gateway_config_filepath": config_path
            },
            target_name=target,
            stop_on_fail=False
        )
        assert status == 0, "Could not start sync_gateway"

    def stop_sync_gateway(self, url):
        target = hostname_for_url(url)
        logging.info("Shutting down sync_gateway on {} ...".format(target))
        ansible_runner = AnsibleRunner()
        status = ansible_runner.run_targeted_ansible_playbook(
            "stop-sync-gateway.yml",
            target_name=target,
            stop_on_fail=False)
        assert status == 0, "Could not stop sync_gateway"
