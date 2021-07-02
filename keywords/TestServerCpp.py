import os
import time

from keywords.TestServerBase import TestServerBase
from keywords.constants import LATEST_BUILDS, RELEASED_BUILDS
from keywords.exceptions import LiteServError
from keywords.utils import version_and_build
from keywords.utils import log_info
from keywords.constants import BINARY_DIR
from zipfile import ZipFile
import requests
import subprocess

class TestServerCpp(TestServerBase):
    def __init__(self, version_build, host, port, debug_mode=None, platform="c-linux", community_enabled=None):
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
        #if self.build is None:
        self.package_name = "CBLTestServer_macosx_x64"
                # "CBLTestServer_macosx-{}-{}".format(self.build_type, self.version)
        self.download_url = "{}/couchbase-lite-c/{}/{}.zip".format(RELEASED_BUILDS, self.version, self.package_name)
        self.binary_path = "{}/{}.exe".format(BINARY_DIR, self.package_name)

        self.build_name = "TestServer-C-{}-{}".format(self.build_type, self.version_build)

        log_info("package_name: {}".format(self.package_name))
        log_info("download_url: {}".format(self.download_url))
        log_info("build_name: {}".format(self.build_name))
        log_info("self.platform = {}".format(self.platform))

    def install(self):
        """
        Noop on Mac OSX. The LiteServ is a commandline binary
        """
        log_info("No install needed for macosx")


    def download(self, version_build=None):
        """
         TODO: once we know the steps add it
        """
        if version_build is not None:
            self.version_build = version_build
        app_name = self.package_name
        expected_binary_path = "{}/{}/{}".format(BINARY_DIR, self.app_dir, app_name)
        if os.path.exists(expected_binary_path):
            log_info("Package is already downloaded. Skipping.")
            return
        # Package not downloaded, proceed to download from latest builds
        downloaded_package_zip_name = "{}/{}".format(BINARY_DIR, self.package_name)
        self.version, self.build = version_and_build(self.version_build)
        if self.build is None:
            url = "{}/couchbase-lite-c/{}/{}".format(RELEASED_BUILDS, self.version, self.package_name)
        else:
            url = "{}/couchbase-lite-c/{}/{}/{}".format(LATEST_BUILDS, self.version, self.build, self.package_name)
        log_info("Downloading {} -> {}/{}".format(url, BINARY_DIR, self.package_name))

        resp = requests.get(url, verify=False)
        resp.raise_for_status()
        if self.platform == "c-macosx" or "c-linux":
            resp = requests.get(self.download_url, verify=False)
            resp.raise_for_status()
            with open("{}/{}".format(BINARY_DIR, self.package_name), "wb") as f:
                f.write(resp.content)
            extracted_directory_name = self.binary_path.replace(".zip", "")
            with ZipFile("{}".format(self.binary_path)) as zip_f:
                zip_f.extractall("{}".format(extracted_directory_name))

            # Remove .zip
            os.remove("{}".format(self.binary_path))

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
            status = self.ansible_runner.run_ansible_playbook("start-testserver-c-linux.yml", extra_vars={
                "binary_path": self.binary_path
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
            status = self.ansible_runner.run_ansible_playbook("stop-testserver-c-macos.yml", extra_vars={
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
