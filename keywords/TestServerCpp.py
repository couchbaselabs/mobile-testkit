import os
import time

from keywords.TestServerBase import TestServerBase
from keywords.constants import LATEST_BUILDS, RELEASED_BUILDS
from keywords.exceptions import LiteServError
from keywords.utils import version_and_build
from keywords.utils import log_info
from libraries.provision.ansible_runner import AnsibleRunner


class TestServerCpp(TestServerBase):
    def __init__(self, version_build, host, port, debug_mode=None, platform="javaws-centos", community_enabled=None):
        self.platform = platform
        self.released_version = {
            "3.0.0": 94
        }

        self.version_build = version_build
        self.version, self.build = version_and_build(self.version_build)

        if community_enabled:
            self.build_type = "community"
        else:
            self.build_type = "enterprise"
        if self.build is None:
            self.package_name = "CBLTestServer-C-{}-{}".format(self.build_type, self.version)
            self.download_url = "{}/couchbase-lite-c/{}/{}.war".format(RELEASED_BUILDS, self.version, self.package_name)

        self.build_name = "TestServer-C-{}-{}".format(self.build_type, self.version_build)

        log_info("package_name: {}".format(self.package_name))
        log_info("download_url: {}".format(self.download_url))
        log_info("download_corelib_url: {}".format(self.download_corelib_url))
        log_info("build_name: {}".format(self.build_name))
        log_info("self.platform = {}".format(self.platform))


    def download(self, version_build=None):
        """
         TODO: once we know the steps add it
        """

        if self.platform == "c-msft":
            # download war file to a remote Windows server machine
            status = self.ansible_runner.run_ansible_playbook("download-testserver-c.yml", extra_vars={
                "testserver_download_url": self.download_url,
                "build_name": self.build_name
            })
        if status == 0:
            return
        else:
            raise LiteServError("Failed to download Test server on remote machine")

    def install(self):
        if self.platform == "c-macosx":
            # deploy jar/war files to Tomcat on macOS
            status = self.ansible_runner.run_ansible_playbook("install-testserver-c-macosx.yml", extra_vars={
                "binary_path": self.binary_path,
                "version_build": self.version_build
            })
        else:
            # deploy jar/war files to Tomcat on non-Windows
            status = self.ansible_runner.run_ansible_playbook("install-testserver-c-linux.yml", extra_vars={
                "binary_path": self.binary_path,
                "version_build": self.version_build
            })

        if status == 0:
            return
        else:
            raise LiteServError("Failed to install Test server on remote machine")

    def remove(self):
        raise NotImplementedError()

    def start(self, logfile_name):
        if self.platform == "c-macosx":
            status = self.ansible_runner.run_ansible_playbook("start-testserver-c-macosx.yml", extra_vars={
                "service_status": "start",
                "catalina_base": os.environ["CATALINA_BASE"]
            })

            status = self.ansible_runner.run_ansible_playbook("start-testserver-c-linux.yml", extra_vars={
                "service_status": "start"
            })

        time.sleep(15)

        if status == 0:
            return
        else:
            raise LiteServError("Failed to start Tomcat on remote machine")

    def _verify_launched(self):
        raise NotImplementedError()

    def stop(self):
        if self.platform == "c-macosx":
            # stop Tomcat Windows Service
            status = self.ansible_runner.run_ansible_playbook("stop-testserver--c-macos.yml", extra_vars={
                "service_status": "stopped"
            })
        else:
            # stop Tomcat Server
            status = self.ansible_runner.run_ansible_playbook("stop-testserver-c-linux.yml", extra_vars={
                "service_status": "stop"
            })

        if status == 0:
            return
        else:
            raise LiteServError("Failed to stop Tomcat on remote machine")
