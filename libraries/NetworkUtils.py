import subprocess
import shutil
import time
import os
from libraries.provision.ansible_runner import AnsibleRunner

from keywords.exceptions import ProvisioningError


class NetworkUtils:

    def list_connections(self):
        output = subprocess.check_output("netstat -ant | awk '{print $6}' | sort | uniq -c | sort -n", shell=True)
        print(output)

    def start_packet_capture(self, cluster_config):
        ansible_runner = AnsibleRunner(config=cluster_config)
        status = ansible_runner.run_ansible_playbook("start-ngrep.yml")
        if status != 0:
            raise ProvisioningError("Failed to start packet capture")

    def stop_packet_capture(self, cluster_config):
        ansible_runner = AnsibleRunner(config=cluster_config)
        status = ansible_runner.run_ansible_playbook("stop-ngrep.yml")
        if status != 0:
            raise ProvisioningError("Failed to stop packet capture")

    def collect_packet_capture(self, cluster_config, test_name):
        ansible_runner = AnsibleRunner(config=cluster_config)
        status = ansible_runner.run_ansible_playbook("collect-ngrep.yml")
        if status != 0:
            raise ProvisioningError("Failed to collect packet capture")

        # zip logs and timestamp
        if os.path.isdir("/tmp/sys-logs"):
            date_time = time.strftime("%Y-%m-%d-%H-%M-%S")
            name = "/tmp/ngrep-{}-{}-output".format(test_name, date_time)
            shutil.make_archive(name, "zip", "/tmp/sys-logs")
            shutil.rmtree("/tmp/sys-logs")
            print("ngrep logs copied here {}.zip\n".format(name))
