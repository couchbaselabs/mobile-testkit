import os
import time

from keywords.TestServerBase import TestServerBase
from keywords.constants import LATEST_BUILDS, RELEASED_BUILDS
from keywords.exceptions import LiteServError
from keywords.utils import version_and_build
from keywords.constants import BINARY_DIR
from keywords.utils import log_info
from libraries.provision.ansible_runner import AnsibleRunner
from keywords.remoteexecutor import RemoteExecutor
import subprocess

class TestServerCpp(TestServerBase):
    def __init__(self, version_build, host, port, debug_mode=None, platform="c-debian", community_enabled=None):
        super(TestServerCpp, self).__init__(version_build, host, port)
        self.platform = platform
        self.host = host
        self.released_version = {
            "3.0.0": 94
        }

        self.version_build = version_build
        self.version, self.build = version_and_build(self.version_build)

        if community_enabled:
            self.build_type = "community"
        else:
            self.build_type = "enterprise"

        if self.platform == "c-macosx":
            self.package_name = "CBLTestServer_macos"
        elif self.platform == "c-debian":
            self.package_name = "testserver_debian9-x86_64"
        elif self.platform == "c-rpi":
            self.package_name = "testserver_raspios10-armhf"
        else:
            self.package_name = "testserver_ubuntu20.04-x86_64"

        self.build_name = self.package_name + "_" + self.build_type

        if self.build is None:
            self.download_url = "{}/couchbase-lite-c/{}/{}.zip".format(RELEASED_BUILDS, self.version, self.build_name)
        else:
            self.download_url = "{}/couchbase-lite-c/{}/{}/{}.zip".format(LATEST_BUILDS, self.version, self.build, self.build_name)
        self.binary_path = "{}/{}.exe".format(BINARY_DIR, self.package_name)


        log_info("package_name: {}".format(self.package_name))
        log_info("download_url: {}".format(self.download_url))
        log_info("build_name: {}".format(self.build_name))
        log_info("self.platform = {}".format(self.platform))

        '''
           generate ansible config file base on platform format
        '''
        if "TESTSERVER_HOST_USER" not in os.environ:
            raise LiteServError(
                "Make sure you define 'TESTSERVER_HOST_USER' as the user for the host you are targeting")

        if "TESTSERVER_HOST_PASSWORD" not in os.environ:
            raise LiteServError(
                "Make sure you define 'TESTSERVER_HOST_PASSWORD' as the user for the host you are targeting")
        if "TESTSERVER_HOST" not in os.environ:
            test_host = host
        else:
            test_host = os.environ["TESTSERVER_HOST"]

            # Create config for TestServer non-Windows host
        ansible_testserver_target_lines = [
            "[testserver]",
            "testserver ansible_host={}".format(test_host),
            "[testserver:vars]",
            "ansible_user={}".format(os.environ["TESTSERVER_HOST_USER"]),
            "ansible_password={}".format(os.environ["TESTSERVER_HOST_PASSWORD"])
            ]

        ansible_testserver_target_string = "\n".join(ansible_testserver_target_lines)
        log_info("Writing: {}".format(ansible_testserver_target_string))
        config_location = "resources/liteserv_configs/{}".format(self.platform)

        with open(config_location, "w") as f:
            f.write(ansible_testserver_target_string)
        self.ansible_runner = AnsibleRunner(config=config_location)

    def install(self):
        """
        Noop on Mac OSX. The LiteServ is a commandline binary
        """
        log_info("No install needed for C")

    def download(self, version_build=None):
        """
         TODO: once we know the steps add it
        """

        status = self.ansible_runner.run_ansible_playbook("download-testserver-c.yml", extra_vars={
            "testserver_download_url": self.download_url,
            "package_name": self.build_name
        })

        if status == 0:
            return
        else:
            raise LiteServError("Failed to download Test server on remote machine")

    def remove(self):
        raise NotImplementedError()

    def start(self, logfile_name):
        if self.platform == "c-macosx":
            # status = self.ansible_runner.run_ansible_playbook("start-testserver-c-macosx.yml", extra_vars={
            #     "binary_path": self.binary_path
            # })
            commd = self.binary_path
            subprocess.run([commd], shell=True)
        else:
            print("STOPPING THE TESTSERVER")
            remote_executor = RemoteExecutor(self.host, self.platform, os.environ["TESTSERVER_HOST_USER"],
                                             os.environ["TESTSERVER_HOST_PASSWORD"])
            remote_executor.execute("ps -ef | grep 'testserver' | awk '{print $2}' | xargs kill -9 $1")
            status = self.ansible_runner.run_ansible_playbook("start-testserver-c-linux.yml", extra_vars={
                "binary_path": self.binary_path
            })

        time.sleep(15)

        if status == 0:
            return
        else:
            raise LiteServError("Failed to start TestServer on remote machine")

    def _verify_launched(self):
        raise NotImplementedError()

    def stop(self):
        if self.platform == "c-macosx":
            # stop Tomcat Windows Service
            status = self.ansible_runner.run_ansible_playbook("stop-testserver-c-macos.yml", extra_vars={
                "service_status": "stopped"
            })
        else:
            print("STOPPING THE TESTSERVER")
            remote_executor = RemoteExecutor(self.host, self.platform, os.environ["TESTSERVER_HOST_USER"], os.environ["TESTSERVER_HOST_PASSWORD"])
            remote_executor.execute("ps -ef | grep 'testserver' | awk '{print $2}' | xargs kill -9 $1")

        if status == 0:
            return
        else:
            raise LiteServError("Failed to stop Testserver on remote machine")
