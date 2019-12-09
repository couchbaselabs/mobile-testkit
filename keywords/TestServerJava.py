import os
from os.path import expanduser
import time
from shutil import copyfile, rmtree
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
        self.released_version = {
            "2.7.0": 56
        }

        self.version_build = version_build
        self.version, self.build = version_and_build(self.version_build)

        if self.build is None:
            self.package_name = "CBLTestServer-Java-Desktop-{}-enterprise.jar".format(self.version)
            self.download_url = "{}/couchbase-lite-java/{}/{}".format(RELEASED_BUILDS, self.version, self.package_name)
        else:
            self.package_name = "CBLTestServer-Java-Desktop-{}-enterprise.jar".format(self.version_build)
            self.download_url = "{}/couchbase-lite-java/{}/{}/{}".format(LATEST_BUILDS, self.version, self.build, self.package_name)

        self.build_name = "TestServer-java-desktop-{}".format(self.version_build)

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
        else:
            home = expanduser("~")
            self.testserver_path = "{}/javatestserver".format(home)
            # java web service
            # prepare java web service parameters TODO: remove this line after implementation
            print("self.platform = {}".format(self.platform))

    def download(self, version_build=None):
        """
        1. Downloads the TestServer-Java-Desktop.jar package from latestbuild to the remote Linux or Windows machine
        2. Extracts the package and removes the zip
        """

        if self.platform == "java-msft":
            # download jar file to a remote Windows 10 machine
            status = self.ansible_runner.run_ansible_playbook("download-testserver-java-desktop-msft.yml", extra_vars={
                "download_url": self.download_url,
                "package_name": self.package_name,
                "build_name": self.build_name
            })

            if status == 0:
                return
            else:
                raise LiteServError("Failed to download Test server on remote machine")

        # start download java package for non-Windows platforms
        expected_binary_path = "{}/{}".format(BINARY_DIR, self.package_name)
        if os.path.isfile(expected_binary_path):
            log_info("Package {} is already downloaded. Skipping.", self.package_name)
            return

        # download java package
        log_info("Downloading {} -> {}/{}".format(self.download_url, BINARY_DIR, self.package_name))

        resp = requests.get(self.download_url, verify=False)
        resp.raise_for_status()
        with open("{}/{}".format(BINARY_DIR, self.package_name), "wb") as f:
            f.write(resp.content)

    def install(self):
        if self.platform == "java-msft":
            log_info("there is nothing to install on windows platform")
            return

        # 1. cleanup ~/testserver directory if exist, create a new with same dir name
        try:
            if os.path.exists(self.testserver_path):
                rmtree(self.testserver_path)
            os.mkdir(self.testserver_path)
        except OSError:
            log_info("Creation of the directory {} failed".format(self.testserver_path))
        else:
            log_info("Successfully created the directory {} ".format(self.testserver_path))

        # 2. copy the jar package to this directory
        src = "{}/{}".format(BINARY_DIR, self.package_name)
        des = "{}/{}".format(self.testserver_path, self.package_name)
        copyfile(src, des)
        log_info("{} has been copied to ~/javatestserver directory".format(self.package_name))

    def remove(self):
        log_info("{}: Nothing to remove".format(self.platform))

    def start(self, logfile_name):
        """
        start the java standalone application by calling java -jar
        on non-Windows env, directly run on the current machine
        on Windows env, using ansible to launch the app on remote Windows machine
        """
        if self.platform == "java-msft":
            self.logfile = logfile_name
            log_info("Starting Test server {}".format(self.package_name))
            # Start Testserver via Ansible on remote machine
            status = self.ansible_runner.run_ansible_playbook(
                "start-testserver-java-desktop-msft.yml",
                extra_vars={
                    "package_name": self.package_name,
                    "version_build": self.version_build,
                    "build_name": self.build_name
                }
            )
            # sleep for some seconds
            time.sleep(10)

            if status != 0:
                raise LiteServError("Failed to launch Test server on windows machine")
        else:
            log_info("Starting Test server {} on {}".format(self.package_name, self.platform))
            work_dir = os.getcwd()
            os.chdir(self.testserver_path)
            print(self.testserver_path)
            self.java_proc = subprocess.Popen(
                ["java", "-jar", self.package_name],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            '''
            self.java_proc = subprocess.Popen(["java", "-jar", self.package_name])
            '''
            time.sleep(5)
            os.chdir(work_dir)

    def _verify_launched(self):
        raise NotImplementedError()

    def stop(self):
        log_info("Stopping JavaTestServer app")

        if self.platform != "net-msft":
            try:
                self.java_proc.terminate()
            except:
                log_info("Failed stopping JavaTestServer app")
