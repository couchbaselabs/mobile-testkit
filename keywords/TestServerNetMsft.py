import os
import time

from keywords.TestServerWinBase import TestServerWinBase
from keywords.constants import LATEST_BUILDS, RELEASED_BUILDS
from keywords.exceptions import LiteServError
from keywords.utils import log_info


class TestServerNetMsft(TestServerWinBase):

    def __init__(self, version_build, host, port, community_enabled=None, platform="net-msft"):

        # Initialize baseclass properies
        super(TestServerNetMsft, self).__init__(version_build, host, port)

        self.platform = platform

        if version_build <= "2.1.0":
            raise Exception("No .net based app available to download for 2.1.0 or below at latestbuild. Use nuget package to create app.")
        if self.platform == "net-msft":
            if community_enabled:
                self.build_name = "TestServer-Net-community-{}".format(self.version_build)
                self.binary_path = "TestServer-Net-community-{}\\TestServer.NetCore.dll".format(self.version_build)
                self.package_name = "TestServer.NetCore-community.zip"
            else:
                self.build_name = "TestServer-Net-{}".format(self.version_build)
                self.binary_path = "TestServer-Net-{}\\TestServer.NetCore.dll".format(self.version_build)
                self.package_name = "TestServer.NetCore.zip"
            if self.build is None:
                self.download_url = "{}/couchbase-lite-net/{}/{}".format(RELEASED_BUILDS, self.version, self.package_name)
            else:
                self.download_url = "{}/couchbase-lite-net/{}/{}/{}".format(LATEST_BUILDS, self.version, self.build, self.package_name)
        else:
            self.binary_path = "TestServer-UWP-{}\\run.ps1".format(self.version_build)
            if self.build is None:
                self.download_url = "{}/couchbase-lite-net/{}/TestServer.UWP.zip".format(RELEASED_BUILDS, self.version)
            else:
                self.download_url = "{}/couchbase-lite-net/{}/{}/TestServer.UWP.zip".format(LATEST_BUILDS, self.version, self.build)
            self.package_name = "TestServer.UWP.zip"
            self.stop_binary_path = "TestServer-UWP-{}\\stop.ps1".format(self.version_build)
            self.build_name = "TestServer-UWP-{}".format(self.version_build)

    def download(self, version_build=None):
        """
        1. Downloads the LiteServ.zip package from latestbuild to the remote Windows host to Desktop\\LiteServ\\
        2. Extracts the package and removes the zip
        """
        if version_build is not None:
            self.version_build = version_build

        # Download LiteServ via Ansible on remote machine
        status = self.ansible_runner.run_ansible_playbook("download-testserver-msft.yml", extra_vars={
            "download_url": self.download_url,
            "package_name": self.package_name,
            "build_name": self.build_name
        })

        if status != 0:
            raise LiteServError("Failed to download Test server on remote machine")

    def install(self):
        log_info("{}: Nothing to install".format(self.platform))

    def remove(self):
        log_info("{}: Nothing to remove".format(self.platform))

    def start(self, logfile_name):
        """
        1. Starts a Testserver with logging to provided logfile file object.
           The running LiteServ process will be stored in the self.process property.
        2. The method will poll on the endpoint to make sure LiteServ is available.
        3. The expected version will be compared with the version reported by http://<host>:<port>
        4. eturn the url of the running LiteServ
        """
        if self.platform == "net-msft":
            self.logfile = logfile_name
            log_info("Starting Test server {}".format(self.binary_path))
            # Start Testserver via Ansible on remote machine
            status = self.ansible_runner.run_ansible_playbook(
                "start-testserver-msft.yml",
                extra_vars={
                    "binary_path": self.binary_path,
                    "version_build": self.version_build
                }
            )
        else:
            # net-uwp
            log_info("Starting Test server UWP {}".format(self.binary_path))
            # Start Testserver via Ansible on remote machine
            status = self.ansible_runner.run_ansible_playbook(
                "start-testserver-uwp.yml",
                extra_vars={
                    "binary_path": self.binary_path
                }
            )

        if status != 0:
            raise LiteServError("Could not start testserver")
        time.sleep(15)

    def _verify_launched(self):
        """Poll on expected http://<host>:<port> until it is reachable
        """
        resp_obj = self._wait_until_reachable()
        log_info(resp_obj)

    def stop(self):
        """
        Stops a .NET listener on a remote windows machine via ansible and pulls logs.
        """
        log_info("Stopping TestServer on windows ...")

        if self.platform == "net-msft":
            log_full_path = "{}/{}".format(os.getcwd(), self.logfile)
            log_info("Pulling logs to {} ...".format(log_full_path))
            status = self.ansible_runner.run_ansible_playbook(
                "stop-testserver-windows.yml",
                extra_vars={
                    "log_full_path": log_full_path
                }
            )
        else:
            # net-uwp
            status = self.ansible_runner.run_ansible_playbook(
                "stop-testserver-uwp.yml",
                extra_vars={
                    "binary_path": self.stop_binary_path
                }
            )

        if status != 0:
            raise LiteServError("Could not stop TestServer")
