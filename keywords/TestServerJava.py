import os
import subprocess

import requests

from keywords.TestServerBase import TestServerBase
from keywords.constants import LATEST_BUILDS, RELEASED_BUILDS
from keywords.constants import BINARY_DIR
from keywords.exceptions import LiteServError
from keywords.utils import version_and_build
from keywords.utils import log_info

from libraries.provision.ansible_runner import AnsibleRunner

class TestServerJava(TestServerBase):

    def __init__(self, version_build, host, port, community_enabled=None, debug_mode=False, platform="java-linux"):
        super(TestServerJava, self).__init__(version_build, host, port)
        self.platform = platform

        self.version_build = version_build
        self.version, self.build = version_and_build(self.version_build)

        if self.platform == "java-msft":
            # java desktop on Windows platform
            if "LITESERV_MSFT_HOST_USER" not in os.environ:
                raise LiteServError(
                    "Make sure you define 'LITESERV_MSFT_HOST_USER' as the windows user for the host you are targeting")

            if "LITESERV_MSFT_HOST_PASSWORD" not in os.environ:
                raise LiteServError(
                    "Make sure you define 'LITESERV_MSFT_HOST_PASSWORD' as the windows user for the host you are targeting")

            # Create config for LiteServ Windows host
            ansible_testserver_mfst_target_lines = [
                "[windows]",
                "win1 ansible_host={}".format(host),
                "[windows:vars]",
                "ansible_user={}".format(os.environ["LITESERV_MSFT_HOST_USER"]),
                "ansible_password={}".format(os.environ["LITESERV_MSFT_HOST_PASSWORD"]),
                "ansible_port=5985",
                "ansible_connection=winrm",
                "# The following is necessary for Python 2.7.9+ when using default WinRM self-signed certificates:",
                "ansible_winrm_server_cert_validation=ignore",
            ]

            ansible_testserver_mfst_target_string = "\n".join(ansible_testserver_mfst_target_lines)
            log_info("Writing: {}".format(ansible_testserver_mfst_target_string))
            config_location = "resources/liteserv_configs/java-msft"

            with open(config_location, "w") as f:
                f.write(ansible_testserver_mfst_target_string)

            self.ansible_runner = AnsibleRunner(config=config_location)


            # prepare java desktop parameters TODO: remove this line after implementation
            print("self.platform = {}".format(self.platform))
        elif self.platform == "java-ws":
            # java web service
            # prepare java web service parameters TODO: remove this line after implementation
            print("self.platform = {}".format(self.platform))

    def download(self, version_build=None):
        """
        1. Downloads the TestServer-Java-Desktop.jar package from latestbuild to the remote Linux or Windows machine
        2. Extracts the package and removes the zip
        :param version_build: 
        :return: 
        """
        raise NotImplementedError()

    def install(self):
        raise NotImplementedError()

    def remove(self):
        raise NotImplementedError()

    def start(self, logfile_name):
        raise NotImplementedError()

    def _verify_launched(self):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()
