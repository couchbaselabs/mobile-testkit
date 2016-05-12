import subprocess
import shutil
import time
import os
from libraries.provision.ansible_runner import AnsibleRunner


class NetworkUtils:

    def list_connections(self):
        output = subprocess.check_output("netstat -ant | awk '{print $6}' | sort | uniq -c | sort -n", shell=True)
        print(output)

    def start_packet_capture(self):
        ansible_runner = AnsibleRunner()
        status = ansible_runner.run_ansible_playbook(
            "start-ngrep.yml",
            stop_on_fail=False
        )
        assert (status == 0)

    def stop_packet_capture(self):
        ansible_runner = AnsibleRunner()
        status = ansible_runner.run_ansible_playbook(
            "stop-ngrep.yml",
            stop_on_fail=False
        )
        assert (status == 0)

    def collect_packet_capture(self):
        ansible_runner = AnsibleRunner()
        status = ansible_runner.run_ansible_playbook(
            "collect-ngrep.yml",
            stop_on_fail=False
        )
        assert (status == 0)

        # zip logs and timestamp
        if os.path.isdir("/tmp/sg_logs"):
            date_time = time.strftime("%Y-%m-%d-%H-%M-%S")
            name = "/tmp/ngrep-{}-sglogs".format(date_time)
            shutil.make_archive(name, "zip", "/tmp/sg_logs")
            shutil.rmtree("/tmp/sg_logs")
            print("ngrep logs copied here {}.zip\n".format(name))
