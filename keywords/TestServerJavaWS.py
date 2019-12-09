import os
import subprocess

import requests

from keywords.TestServerBase import TestServerBase
from keywords.constants import LATEST_BUILDS, RELEASED_BUILDS
from keywords.exceptions import LiteServError
from keywords.utils import version_and_build
from keywords.utils import log_info
from libraries.provision.ansible_runner import AnsibleRunner


class TestServerJavaWS(TestServerBase):

    def __init__(self, version_build, host, port, community_enabled=None, debug_mode=False, platform="java"):
        super(TestServerJavaWS, self).__init__(version_build, host, port)
        self.platform = platform
        self.released_version = {
            "2.7.0": 188
        }

        self.version_build = version_build
        self.version, self.build = version_and_build(self.version_build)

        if self.build is None:
            self.package_name = "CBLTestServer-Java-WS-{}-enterprise-release.war".format(self.version)
            self.download_url = "{}/couchbase-lite-java/{}/{}".format(RELEASED_BUILDS, self.version, self.package_name)
        else:
            self.package_name = "CBLTestServer-Java-WS-{}-enterprise-release.war".format(self.version_build)
            self.download_url = "{}/couchbase-lite-java/{}/{}/{}".format(LATEST_BUILDS, self.version, self.build, self.package_name)

        self.build_name = "TestServer-java-WS-{}".format(self.version_build)

        # for debugging TODO: will be removed
        print("package_name: {}".format(self.package_name))
        print("download_url: {}".format(self.download_url))
        print("build_name: {}".format(self.build_name))
        print("version_build: {}".format(self.version_build))

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
        elif self.platform == "java-linux":
            # java web service
            # prepare java web service parameters TODO: remove this line after implementation
            print("self.platform = {}".format(self.platform))

    def download(self, version_build=None):
        """
        1. Downloads the TestServer-Java-WS.war package from latestbuild to the remote Linux or Windows machine
        2. Extracts the package and removes the zip
        :param version_build
        :return: nothing
        """

        if self.platform == "java-msft":
            # download jar file to a remote Windows 10 machine
            status = self.ansible_runner.run_ansible_playbook("download-testserver-msft.yml", extra_vars={
                "download_url": self.download_url,
                "package_name": self.package_name,
                "build_name": self.build_name
            })

            if status != 0:
                raise LiteServError("Failed to download Test server on remote machine")
        else:
            # download jar file to the current linux or macosx machine
            # 1. create a ~/testserver directory
            testserver_path = "~/testserver"
            try:
                os.mkdir(testserver_path)
            except OSError:
                log_info("Creation of the directory {} failed".format(testserver_path))
            else:
                log_info("Successfully created the directory {} ".format(testserver_path))

            # 2. download jar package under ~/testserver
            log_info("Downloading {} -> {}/{}".format(self.download_url, testserver_path, self.package_name))
            resp = requests.get(self.download_url, verify=False)
            resp.raise_for_status()
            with open("{}/{}".format(testserver_path, self.package_name), "wb") as f:
                f.write(resp.content)

                # 3. unpackage the war file
            status = subprocess.check_call("jar -xvf {}/{}".format(testserver_path, self.package_name))

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
