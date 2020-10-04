import os
from keywords.TestServerBase import TestServerBase
from keywords.constants import LATEST_BUILDS, RELEASED_BUILDS
from keywords.exceptions import LiteServError
from keywords.utils import version_and_build
from keywords.utils import log_info
from libraries.provision.ansible_runner import AnsibleRunner


class TestServerJava(TestServerBase):

    def __init__(self, version_build, host, port, community_enabled=None, debug_mode=False, platform="java-centos"):
        super(TestServerJava, self).__init__(version_build, host, port)

        self.platform = platform
        self.released_version = {
            "2.7.0": 94
        }

        self.version_build = version_build
        self.version, self.build = version_and_build(self.version_build)

        if self.build is None:
            self.package_name = "CBLTestServer-Java-Desktop-{}-enterprise".format(self.version)
            self.download_url = "{}/couchbase-lite-java/{}/{}.zip".format(RELEASED_BUILDS, self.version, self.package_name)
        else:
            self.package_name = "CBLTestServer-Java-Desktop-{}-enterprise".format(self.version_build)
            self.download_url = "{}/couchbase-lite-java/{}/{}/{}.zip".format(LATEST_BUILDS, self.version, self.build, self.package_name)

        self.build_name = "TestServer-java-{}".format(self.version_build)

        log_info("package_name: {}".format(self.package_name))
        log_info("download_url: {}".format(self.download_url))
        log_info("build_name: {}".format(self.build_name))
        log_info("self.platform = {}".format(self.platform))

        '''
        generate ansible config file base on platform format
        '''
        if self.platform == "java-msft":
            # java desktop on Windows platform
            if "LITESERV_MSFT_HOST_USER" not in os.environ:
                raise LiteServError(
                    "Make sure you define 'LITESERV_MSFT_HOST_USER' as the windows user for the host you are targeting")

            if "LITESERV_MSFT_HOST_PASSWORD" not in os.environ:
                raise LiteServError(
                    "Make sure you define 'LITESERV_MSFT_HOST_PASSWORD' as the windows user for the host you are targeting")

            # Create config for LiteServ Windows host
            ansible_testserver_target_lines = [
                "[windows]",
                "win1 ansible_host={}".format(host),
                "[windows:vars]",
                "ansible_user={}".format(os.environ["LITESERV_MSFT_HOST_USER"]),
                "ansible_password={}".format(os.environ["LITESERV_MSFT_HOST_PASSWORD"]),
                "ansible_port=5985",
                "ansible_connection=winrm",
                "# The following is necessary for Python 2.7.9+ when using default WinRM self-signed certificates:",
                "ansible_winrm_server_cert_validation=ignore"
            ]
        else:
            # java desktop on non-Windows platform
            if "TESTSERVER_HOST_USER" not in os.environ:
                raise LiteServError(
                    "Make sure you define 'TESTSERVER_HOST_USER' as the user for the host you are targeting")

            if "TESTSERVER_HOST_PASSWORD" not in os.environ:
                raise LiteServError(
                    "Make sure you define 'TESTSERVER_HOST_PASSWORD' as the user for the host you are targeting")

            # Create config for TestServer non-Windows host
            ansible_testserver_target_lines = [
                "[testserver]",
                "testserver ansible_host={}".format(host),
                "[testserver:vars]",
                "ansible_user={}".format(os.environ["TESTSERVER_HOST_USER"]),
                "ansible_password={}".format(os.environ["TESTSERVER_HOST_PASSWORD"])
            ]

        ansible_config_content = "\n".join(ansible_testserver_target_lines)
        log_info("Writing: {}".format(ansible_config_content))
        config_location = "resources/liteserv_configs/{}".format(self.platform)

        with open(config_location, "w") as f:
            f.write(ansible_config_content)
        self.ansible_runner = AnsibleRunner(config=config_location)

    def download(self, version_build=None):
        """
        Downloads the TestServer-Java-Desktop-{version}-enterprise.jar package
        from latestbuild to the remote Linux or Windows machine
        :params: download_url, package_name, build_name
        :return: nothing
        """

        if self.platform == "java-msft":
            # download jar file to a remote Windows 10 machine
            status = self.ansible_runner.run_ansible_playbook("download-testserver-java-desktop-msft.yml", extra_vars={
                "download_url": self.download_url,
                "package_name": self.package_name,
                "build_name": self.build_name
            })
        else:
            # download jar file to a remote non-Windows machine
            status = self.ansible_runner.run_ansible_playbook("download-testserver-java-desktop.yml", extra_vars={
                "download_url": self.download_url,
                "package_name": self.package_name
            })

        if status == 0:
            return
        else:
            raise LiteServError("Failed to download Test server on remote machine")

    def install(self):
        if self.platform == "java-msft":
            # install jar file as a Windows service on Windows environment
            status = self.ansible_runner.run_ansible_playbook("install-testserver-java-desktop-msft.yml", extra_vars={
                "package_name": self.package_name,
                "build_name": self.build_name,
                "service_user": os.environ["LITESERV_MSFT_HOST_USER"],
                "service_pwd": os.environ["LITESERV_MSFT_HOST_PASSWORD"]
            })

            if status == 0:
                return
            else:
                raise LiteServError("Failed to install Test server on remote machine")
        else:
            log_info("{}: Nothing to install".format(self.platform))

    def remove(self):
        raise NotImplementedError()

    def start(self, logfile_name):
        if self.platform == "java-msft":
            # start  Tomcat Windows Service
            status = self.ansible_runner.run_ansible_playbook("manage-testserver-java-desktop-msft.yml", extra_vars={
                "service_status": "started"
            })
        elif self.platform == "java-macosx":
            # install jar file as a daemon service on macOS and start
            status = self.ansible_runner.run_ansible_playbook("install-testserver-java-desktop-macos.yml", extra_vars={
                "package_name": self.package_name,
                "java_home": os.environ["JAVA_HOME"],
                "jsvc_home": os.environ["JSVC_HOME"]
            })
        else:
            # install jar file as a daemon service on non-Windows environment and start
            status = self.ansible_runner.run_ansible_playbook("install-testserver-java-desktop.yml", extra_vars={
                "package_name": self.package_name,
            })

        if status == 0:
            return
        else:
            raise LiteServError("Failed to install Test server on remote machine")

    def _verify_launched(self):
        raise NotImplementedError()

    def stop(self):
        if self.platform == "java-msft":
            # stop TestServerJava Windows Service
            status = self.ansible_runner.run_ansible_playbook("manage-testserver-java-desktop-msft.yml", extra_vars={
                "service_status": "stopped"
            })
        elif self.platform == "java-macosx":
            # stop TestServerJava Daemon Service
            status = self.ansible_runner.run_ansible_playbook("manage-testserver-java-desktop-macos.yml", extra_vars={
                "service_status": "stop",
                "package_name": self.package_name,
                "java_home": os.environ["JAVA_HOME"],
                "jsvc_home": os.environ["JSVC_HOME"]
            })
        else:
            # stop TestServerJava Daemon Service
            status = self.ansible_runner.run_ansible_playbook("manage-testserver-java-desktop.yml", extra_vars={
                "service_status": "stop",
                "package_name": self.package_name
            })

        if status == 0:
            return
        else:
            raise LiteServError("Failed to stop TestServer service on remote machine")
