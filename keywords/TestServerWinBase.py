import os

from keywords.exceptions import LiteServError
from keywords.TestServerBase import TestServerBase
from keywords.utils import log_info
from keywords.utils import version_and_build

from libraries.provision.ansible_runner import AnsibleRunner


class TestServerWinBase(TestServerBase):
    """Base class that each LiteServ platform need to inherit from.
    Look at LiteServMacOSX.py as an example of a plaform implementation
    of this. This class provides a few common functions as well as
    specifies the API that must be implemented in the subclass."""

    def __init__(self, version_build, host, port):
        # Initialize baseclass properies
        super(TestServerWinBase, self).__init__(version_build, host, port)

        if "LITESERV_MSFT_HOST_USER" not in os.environ:
            raise LiteServError(
                "Make sure you define 'LITESERV_MSFT_HOST_USER' as the windows user for the host you are targeting")

        if "LITESERV_MSFT_HOST_PASSWORD" not in os.environ:
            raise LiteServError(
                "Make sure you define 'LITESERV_MSFT_HOST_PASSWORD' as the windows user for the host you are targeting")

        # Create config for LiteServ Windows host
        ansible_liteserv_mfst_target_lines = [
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

        ansible_liteserv_mfst_target_string = "\n".join(ansible_liteserv_mfst_target_lines)
        log_info("Writing: {}".format(ansible_liteserv_mfst_target_string))
        config_location = "resources/liteserv_configs/net-msft"

        with open(config_location, "w") as f:
            f.write(ansible_liteserv_mfst_target_string)

        self.ansible_runner = AnsibleRunner(config=config_location)
        self.version_build = version_build
        self.version, self.build = version_and_build(self.version_build)

    def download(self, version_build):
        raise NotImplementedError()

    def download_oldVersion(self):
        raise NotImplementedError()

    def install(self):
        raise NotImplementedError()

    def start(self, logfile_name):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()

    def remove(self):
        raise NotImplementedError()

    def close_app(self):
        raise NotImplementedError()
