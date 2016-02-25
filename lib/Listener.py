import subprocess
import requests
import os
import time
import json

from lib.debug import *

from lib import settings
import logging
log = logging.getLogger(settings.LOGGER)


# For use with any listener based application (Android only)
class Listener:
    def __init__(self, target_device, local_port, apk_path, activity):

        self.url = ""
        self.install_and_launch_app(target_device, local_port, apk_path, activity)

        if self.is_emulator(target_device):
            self.url = "http://{}:{}".format(self.get_host_ip(), local_port)
        else:
            self.url = "http://{}:{}".format(self.get_device_ip(target_device), 5984)

        log.info("Listener running at {} ...".format(self.url))

    def install_and_launch_app(self, target_device, local_port, apk_path, activity):
        monkey_output = subprocess.check_output([
            "monkeyrunner",
            "utilities/monkeyrunner.py",
            "--target-device={}".format(target_device),
            "--local-port={}".format(local_port),
            "--apk-path={}".format(apk_path),
            "--activity={}".format(activity)
        ])
        log.info("OUTPUT: {}".format(monkey_output))

    def is_emulator(self, target_device):
        return target_device.startswith("emulator")

    def get_host_ip(self):
        cmd_output = subprocess.check_output("ifconfig")
        en0_section = cmd_output.split("\n")[11]
        full_ip = en0_section.split()[1]
        ip = full_ip.split("/")[0]
        return ip

    def get_device_ip(self, target_device):
        log.info("Getting Device ip ...")
        result = subprocess.check_output(["adb", "-s", "{}".format(target_device), "shell", "netcfg"])
        log.info("RESULT: {}".format(result))
        ip_line = result.split('\n')[0]
        ip = ip_line.split()[2]
        ip = ip.split("/")[0]
        return ip

    def verify_launched(self):
        r = requests.get(self.url)
        log.info("GET {} ".format(r.url))
        r.raise_for_status()
        log.info("{}".format(r.text))

    def create_db(self, name):
        r = requests.put("{}/{}".format(self.url, name))
        log.info("PUT {} ".format(r.url))
        r.raise_for_status()
        return r.json()

    def delete_db(self, name):
        r = requests.delete("{}/{}".format(self.url, name))
        log_request(r)
        log_response(r)
        r.raise_for_status()
        return r.json()

    def get_dbs(self):
        r = requests.get("{}/_all_dbs".format(self.url))
        log.info("GET {}".format(r.url))
        r.raise_for_status()
        return r.json()

    def reset(self):
        dbs = self.get_dbs()
        for db in dbs:
            self.delete_db(db)

    def start_push_replication(self, target, db):
        data = {
            "source": "{}".format(db),
            "target": "{}/{}".format(target, db),
            "continuous": True
        }
        r = requests.post("{}/_replicate".format(self.url), data=json.dumps(data))
        log_request(r)
        log_response(r)
        r.raise_for_status()

    def start_pull_replication(self, target, db):
        data = {
            "source": "{}/{}".format(target, db),
            "target": "{}".format(db),
            "continuous": True
        }
        r = requests.post("{}/_replicate".format(self.url), data=json.dumps(data))
        log_request(r)
        log_response(r)
        r.raise_for_status()


