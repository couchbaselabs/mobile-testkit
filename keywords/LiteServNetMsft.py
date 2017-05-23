import os
import re

from keywords.LiteServBase import LiteServBase
from keywords.constants import LATEST_BUILDS
from keywords.constants import REGISTERED_CLIENT_DBS
from keywords.exceptions import LiteServError
from keywords.utils import version_and_build
from keywords.utils import log_info

from libraries.provision.ansible_runner import AnsibleRunner


class LiteServNetMsft(LiteServBase):

    def __init__(self, version_build, host, port, storage_engine):

        # Initialize baseclass properies
        super(LiteServNetMsft, self).__init__(version_build, host, port, storage_engine)

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

    def download(self):
        """
        1. Downloads the LiteServ.zip package from latestbuild to the remote Windows host to Desktop\LiteServ\
        2. Extracts the package and removes the zip
        """

        version, build = version_and_build(self.version_build)
        download_url = "{}/couchbase-lite-net/{}/{}/LiteServ.zip".format(LATEST_BUILDS, version, build)
        package_name = "couchbase-lite-net-msft-{}-liteserv".format(self.version_build)

        # Download LiteServ via Ansible on remote machine
        status = self.ansible_runner.run_ansible_playbook("download-liteserv-msft.yml", extra_vars={
            "download_url": download_url,
            "package_name": package_name
        })

        if status != 0:
            raise LiteServError("Failed to download LiteServ package on remote machine")

    def install(self):
        """
        Installs needed packages on Windows host and removes any existing service wrappers for LiteServ
        """
        # The package structure for LiteServ is different pre 1.4. Handle for this case
        retries = 2
        directory_path = "couchbase-lite-net-msft-{}-liteserv/LiteServ.exe".format(self.version_build)

        while retries > 0:
            status = self.ansible_runner.run_ansible_playbook("install-liteserv-windows.yml", extra_vars={
                "directory_path": directory_path
            })

            if status != 0:
                if retries > 0:
                    log_info("Failed to install Liteserv on Windows host, retrying...")
                    retries -= 1
                    directory_path = "couchbase-lite-net-msft-{}-liteserv/net45/LiteServ.exe".format(self.version_build)
                elif retries == 0:
                    raise LiteServError("Failed to install Liteserv on Windows host")
            else:
                break

    def remove(self):
        log_info("Removing windows server from: {}".format(self.host))
        status = self.ansible_runner.run_ansible_playbook("remove-liteserv-msft.yml")
        if status != 0:
            raise LiteServError("Failed to install Liteserv on Windows host")

    def start(self, logfile_name):
        """
        1. Starts a LiteServ with logging to provided logfile file object.
           The running LiteServ process will be stored in the self.process property.
        2. The method will poll on the endpoint to make sure LiteServ is available.
        3. The expected version will be compared with the version reported by http://<host>:<port>
        4. eturn the url of the running LiteServ
        """

        self._verify_not_running()

        self.logfile = logfile_name

        process_args = [
            "--port", str(self.port),
            "--dir", "."
        ]

        if self.storage_engine == "ForestDB" or self.storage_engine == "ForestDB+Encryption":
            process_args.append("--storage")
            process_args.append("ForestDB")
        else:
            process_args.append("--storage")
            process_args.append("SQLite")

        if self.storage_engine == "SQLCipher" or self.storage_engine == "ForestDB+Encryption":
            log_info("Using Encryption ...")
            db_flags = []
            for db_name in REGISTERED_CLIENT_DBS:
                db_flags.append("--dbpassword")
                db_flags.append("{}=pass".format(db_name))
            process_args.extend(db_flags)

        # The package structure for LiteServ is different pre 1.4. Handle for this case
        retries = 2
        binary_path = "couchbase-lite-net-msft-{}-liteserv/LiteServ.exe".format(self.version_build)

        while retries > 0:
            joined_args = " ".join(process_args)
            log_info("Starting LiteServ {} with: {}".format(binary_path, joined_args))

            # Start LiteServ via Ansible on remote machine
            status = self.ansible_runner.run_ansible_playbook(
                "start-liteserv-msft.yml",
                extra_vars={
                    "binary_path": binary_path,
                    "launch_args": joined_args,
                }
            )
            if status != 0:
                if retries > 0:
                    log_info("Could not start Liteserv, retrying...")
                    retries -= 1
                    binary_path = "couchbase-lite-net-msft-{}-liteserv/net45/LiteServ.exe".format(self.version_build)
                elif retries == 0:
                    raise LiteServError("Could not start Liteserv")
            else:
                break

        self._verify_launched()

        return "http://{}:{}".format(self.host, self.port)

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

        # The package structure for LiteServ is different pre 1.4. Handle for this case
        retries = 2
        binary_path = "couchbase-lite-net-msft-{}-liteserv/LiteServ.exe".format(self.version_build)

        while retries > 0:
            log_full_path = "{}/{}".format(os.getcwd(), self.logfile)

            log_info("Stopping {} on windows matching ...".format(binary_path))
            log_info("Pulling logs to {} ...".format(log_full_path))

            status = self.ansible_runner.run_ansible_playbook(
                "stop-liteserv-windows.yml",
                extra_vars={
                    "binary_path": binary_path,
                    "log_full_path": log_full_path
                }
            )
            if status != 0:
                if retries > 0:
                    log_info("Could not stop Liteserv, retrying...")
                    retries -= 1
                    binary_path = "couchbase-lite-net-msft-{}-liteserv/net45/LiteServ.exe".format(self.version_build)
                elif retries == 0:
                    raise LiteServError("Could not stop Liteserv")
            else:
                break
