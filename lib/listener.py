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
    def __init__(self, target, local_port, apk_path, activity, reinstall):

        self.target = target
        self.local_port = local_port

        self.url = ""
        self.install_and_launch_app(target, local_port, apk_path, activity, reinstall)

        if self.is_emulator(target):
            self.url = "http://{}:{}".format(self.get_host_ip(), local_port)
        else:
            self.url = "http://{}:{}".format(self.get_device_ip(target), 5984)

        log.info("Listener running at {} ...".format(self.url))

    def install_and_launch_app(self, target, local_port, apk_path, activity, reinstall):

        # Build monkeyrunner install cmd
        cmd_args = [
            "monkeyrunner",
            "/Users/sethrosetter/Code/sync-gateway-testcluster/utilities/monkeyrunner.py",
            "--target={}".format(target),
            "--apk-path={}".format(apk_path),
            "--activity={}".format(activity),
        ]

        if self.is_emulator(target):
            cmd_args.append("--local-port={}".format(local_port))

        if reinstall:
            cmd_args.append("--reinstall")

        # Execute monkeyrunner install
        monkey_output = subprocess.check_output(cmd_args)
        log.info("OUTPUT: {}".format(monkey_output))

    def is_emulator(self, target):
        return target.startswith("emulator") or target.startswith("192.168")

    def get_host_ip(self):
        cmd_output = subprocess.check_output("ifconfig")
        en0_section = cmd_output.split("\n")[11]
        full_ip = en0_section.split()[1]
        ip = full_ip.split("/")[0]
        return ip

    def get_device_ip(self, target):
        log.info("Getting Device ip ...")
        result = subprocess.check_output(["adb", "-s", "{}".format(target), "shell", "netcfg"])
        log.info("RESULT: {}".format(result))
        ip_line = result.split('\n')[0]
        ip = ip_line.split()[2]
        ip = ip.split("/")[0]
        return ip

    def verify_launched(self):
        r = requests.get(self.url)
        log.info("GET {} ".format(r.url))
        log.info("{}".format(r.text))
        r.raise_for_status()

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

    def stop_push_replication(self, target, db):
        data = {
            "source": "{}".format(db),
            "target": "{}/{}".format(target, db),
            "cancel": True
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

    def stop_pull_replication(self, target, db):
        data = {
            "source": "{}/{}".format(target, db),
            "target": "{}".format(db),
            "cancel": True
        }
        r = requests.post("{}/_replicate".format(self.url), data=json.dumps(data))
        log_request(r)
        log_response(r)
        r.raise_for_status()

    def get_num_docs(self, db):
        r = requests.get("{}/{}/_all_docs".format(self.url, db))
        log_request(r)
        log_response(r)
        r.raise_for_status()
        resp_data = r.json()
        return resp_data["total_rows"]

    def kill_port_forwarding(self):
        log.info("Killing forwarding rule for {} on port: {}".format(self.target, self.local_port))
        subprocess.call(['adb', '-s', self.target, 'forward', '--remove', 'tcp:{}'.format(self.local_port)])

    def setup_port_forwarding(self):
        log.info("Setup forwarding rule for {} on port: {}".format(self.target, self.local_port))
        subprocess.call(['adb', '-s', self.target, 'forward', 'tcp:{}'.format(self.local_port), 'tcp:5984'])



