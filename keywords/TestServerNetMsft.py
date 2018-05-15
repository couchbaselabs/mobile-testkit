import os
import re

from keywords.TestServerBase import TestServerBase
from keywords.constants import LATEST_BUILDS
from keywords.exceptions import LiteServError
from keywords.utils import version_and_build
from keywords.utils import log_info

from libraries.provision.ansible_runner import AnsibleRunner


class TestServerNetMsft(TestServerBase):

    def __init__(self, version_build, host, port, community_enabled=None):

        # Initialize baseclass properies
        super(TestServerNetMsft, self).__init__(version_build, host, port)

        if "LITESERV_MSFT_HOST_USER" not in os.environ:
            raise LiteServError("Make sure you define 'LITESERV_MSFT_HOST_USER' as the windows user for the host you are targeting")

        if "LITESERV_MSFT_HOST_PASSWORD" not in os.environ:
            raise LiteServError("Make sure you define 'LITESERV_MSFT_HOST_PASSWORD' as the windows user for the host you are targeting")

        # Create config for LiteServ Windows host
        ansible_liteserv_mfst_target_lines = [
            "[windows]",
            "win1 ansible_host={}".format(host),
            "[windows:vars]",
            "ansible_user={}".format(os.environ["LITESERV_MSFT_HOST_USER"]),
            "ansible_password={}".format(os.environ["LITESERV_MSFT_HOST_PASSWORD"]),
            "ansible_port=5986",
            "ansible_connection=winrm",
            "# The following is necessary for Python 2.7.9+ when using default WinRM self-signed certificates:",
            "ansible_winrm_server_cert_validation=ignore",
        ]

        ansible_liteserv_mfst_target_string = "\n".join(ansible_liteserv_mfst_target_lines)
        log_info("Writing: {}".format(ansible_liteserv_mfst_target_string))
        config_location = "resources/liteserv_configs/net-msft"

        with open(config_location, "w") as f:
            f.write(ansible_liteserv_mfst_target_string)

        self.ansible_runner = AnsibleRunner(config=config_location)
        self.version_build = version_build

    def download(self, version_build=None):
        """
        1. Downloads the LiteServ.zip package from latestbuild to the remote Windows host to Desktop\LiteServ\
        2. Extracts the package and removes the zip
        """
        if version_build is not None:
            self.version_build = version_build
        version, build = version_and_build(self.version_build)
        # download_url = "{}/couchbase-lite-net/{}/{}/TestServer.zip".format(LATEST_BUILDS, version, build)
        # TODO: this is only for testing, remove download_url below line and uncomment later after testing don
        download_url = "{}/couchbase-lite-net/{}/{}/TestServer.NetCore.zip".format(LATEST_BUILDS, version, build)
        package_name = "TestServer.NetCore.zip"
        build_name = "TestServer-Net-{}".format(self.version_build)

        # Download LiteServ via Ansible on remote machine
        status = self.ansible_runner.run_ansible_playbook("download-testserver-msft.yml", extra_vars={
            "download_url": download_url,
            "package_name": package_name,
            "build_name": build_name
        })

        if status != 0:
            raise LiteServError("Failed to download Test server on remote machine")

    def install(self):
        """
        Installs needed packages on Windows host and removes any existing service wrappers for LiteServ
        """
        """ TODO nothing to install for .net  Remove it later
        # The package structure for LiteServ is different pre 1.4. Handle for this case
        if has_dot_net4_dot_5(self.version_build):
            directory_path = "couchbase-lite-net-msft-{}-liteserv/net45/LiteServ.exe".format(self.version_build)
        else:
            directory_path = "couchbase-lite-net-msft-{}-liteserv/LiteServ.exe".format(self.version_build)

        status = self.ansible_runner.run_ansible_playbook("install-liteserv-windows.yml", extra_vars={
            "directory_path": directory_path
        })

        if status != 0:
            raise LiteServError("Failed to install Liteserv on Windows host")
        """
    def remove(self):
        log_info("Removing windows server from: {}".format(self.host))
        status = self.ansible_runner.run_ansible_playbook("remove-liteserv-msft.yml")
        if status != 0:
            raise LiteServError("Failed to install Liteserv on Windows host")

    def start(self, logfile_name):
        """
        1. Starts a Testserver with logging to provided logfile file object.
           The running LiteServ process will be stored in the self.process property.
        2. The method will poll on the endpoint to make sure LiteServ is available.
        3. The expected version will be compared with the version reported by http://<host>:<port>
        4. eturn the url of the running LiteServ
        """
        self.logfile = logfile_name
        binary_path = "TestServer-Net-{}\\TestServer.NetCore.dll".format(self.version_build)
        log_info("Starting Test server {}".format(binary_path))
        # Start Testserver via Ansible on remote machine
        status = self.ansible_runner.run_ansible_playbook(
            "start-testserver-msft.yml",
            extra_vars={
                "binary_path": binary_path
            }
        )
        print "status of start test server msft is ", status
        if status != 0:
            raise LiteServError("Could not start testserver")

    def _verify_launched(self):
        """Poll on expected http://<host>:<port> until it is reachable
        Assert that the response contains the expected version information
        """

        resp_obj = self._wait_until_reachable()
        log_info(resp_obj)

        # .NET Microsoft Windows 10.12/x86_64 1.3.1-build0013/5d1553d
        running_version = resp_obj["vendor"]["version"]

        if not running_version.startswith(".NET Microsoft Windows"):
            raise LiteServError("Invalid platform running!")

        #  ['.NET', 'Microsoft', 'Windows', '10', 'Enterprise', 'x64', '1.4.0', 'build0043', '5cfe25b']
        running_version_parts = re.split("[ /-]", running_version)
        running_version = running_version_parts[6]
        running_build = int(running_version_parts[7].strip("build"))
        running_version_composed = "{}-{}".format(running_version, running_build)

        if self.version_build != running_version_composed:
            raise LiteServError("Expected version does not match actual version: Expected={}  Actual={}".format(
                self.version_build,
                running_version_composed)
            )

    def stop(self):
        """
        Stops a .NET listener on a remote windows machine via ansible and pulls logs.
        """

        log_full_path = "{}/{}".format(os.getcwd(), self.logfile)

        log_info("Stopping TestServer on windows matching ...")
        log_info("Pulling logs to {} ...".format(log_full_path))

        status = self.ansible_runner.run_ansible_playbook(
            "stop-TestServer-windows.yml",
            extra_vars={
                "log_full_path": log_full_path
            }
        )
        if status != 0:
            raise LiteServError("Could not stop TestServer")
