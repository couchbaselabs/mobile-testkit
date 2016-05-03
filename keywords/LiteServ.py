import logging
import os
import shutil
from zipfile import ZipFile
import time
import subprocess

from requests.sessions import Session
from requests.exceptions import ConnectionError

from constants import *
import requests

def version_and_build(full_version):
    version_parts = full_version.split("-")
    assert (len(version_parts) == 2)
    return version_parts[0], version_parts[1]

class LiteServ:

    def __init__(self, platform, version_build):

        supported_platforms = ["macosx", "android", "net"]
        if platform not in supported_platforms:
            raise ValueError("Unsupported version of LiteServ")

        self._platform = platform
        self._version_build = version_build

        if self._platform == "macosx":
            self.extracted_file_name = "couchbase-lite-macosx-{}".format(self._version_build)
        elif self._platform == "android":
            self.extracted_file_name = "couchbase-lite-android-liteserv-{}".format(self._version_build)
        elif self._platform == "net":
            # TODO
            raise NotImplementedError("TODO")

        self._session = Session()

    def download_liteserv(self):

        logging.info("{}/{}".format(BINARY_DIR, self.extracted_file_name))

        # Check if package is already downloaded and return if it is preset
        if os.path.isdir("{}/{}".format(BINARY_DIR, self.extracted_file_name)):
            logging.info("Package exists: {}. Skipping download".format(self.extracted_file_name))
            return

        logging.info("Downloading {} LiteServ, version: {}".format(self._platform, self._version_build))
        if self._platform == "macosx":
            version, build = version_and_build(self._version_build)
            file_name = "couchbase-lite-macosx-enterprise_{}.zip".format(self._version_build)
            if version == "1.2.0":
                url = "{}/couchbase-lite-ios/release/{}/macosx/{}/{}".format(LATEST_BUILDS, version, self._version_build, file_name)
            else:
                url = "{}/couchbase-lite-ios/{}/macosx/{}/{}".format(LATEST_BUILDS, version, self._version_build, file_name)
        elif self._platform == "android":
            # TODO
            pass
        elif self._platform == "net":
            # TODO
            pass

        # Download the packages to binary directory
        print("Downloading: {}".format(url))
        resp = requests.get(url)
        resp.raise_for_status()
        with open("{}/{}".format(BINARY_DIR, file_name), "wb") as f:
            f.write(resp.content)

        # Unzip the package
        with ZipFile("{}/{}".format(BINARY_DIR, file_name)) as zip_f:
            zip_f.extractall("{}/{}".format(BINARY_DIR, self.extracted_file_name))

        # Make binary executable
        os.chmod("{}/{}/LiteServ".format(BINARY_DIR, self.extracted_file_name), 0755)

        # Remove .zip file
        os.remove("{}/{}".format(BINARY_DIR, file_name))

    def get_liteserv_binary_path(self):

        if self._platform == "macosx":
            binary_path = "{}/{}/LiteServ".format(BINARY_DIR, self.extracted_file_name)
        elif self._platform == "net":
            # TODO
            pass
        else:
            raise ValueError("Unsupported standalone LiteServ binary")

        return binary_path

    def install_apk(self):

        apk_path = "{}/{}/couchbase-lite-android-liteserv.apk".format(BINARY_DIR, self.extracted_file_name)
        logging.info(apk_path)

        install_successful = False
        while not install_successful:
            output = subprocess.check_output(["adb", "install", apk_path])
            logging.info(output)
            if "INSTALL_FAILED_ALREADY_EXISTS" in output:
                logging.error("APK already exists. Removing and trying again ...")
                output = subprocess.check_output(["adb", "shell", "pm", "uninstall", "com.couchbase.liteservandroid"])
                logging.info(output)
            else:
                install_successful = True


    def launch_activity(self, port):
        activity_name = "com.couchbase.liteservandroid/com.couchbase.liteservandroid.MainActivity"
        output = subprocess.check_output([
            "adb", "shell", "am", "start", "-n", activity_name,
            "--ei", "listen_port", port, "--es", "username", "none", "--es", "password", "none"
        ])
        logging.info(output)

    def remove_liteserv(self):
        logging.info("Removing {} LiteServ, version: {}".format(self._platform, self._version_build))
        os.chdir(BINARY_DIR)
        shutil.rmtree(self.extracted_file_name)
        os.chdir("../..")

    def verify_liteserv_launched(self, host, port):

        url = "http://{}:{}".format(host, port)
        logging.info("Verifying LiteServ running at {}".format(url))

        count = 0
        wait_time = 1
        while count < MAX_RETRIES:
            try:
                resp = self._session.get(url)
                # If request does not throw, exit retry loop
                break
            except ConnectionError as ce:
                logging.info("LiteServ may not be launched (Retrying): {}".format(ce))
                time.sleep(wait_time)
                count += 1
                wait_time *= 2

        if count == MAX_RETRIES:
            raise RuntimeError("Could not connect to LiteServ")

        resp_json = resp.json()
        lite_version = resp_json["vendor"]["version"]

        # Validate that the version launched is the expected LiteServ version
        # LiteServ: 1.2.1 (build 13)
        version, build = version_and_build(self._version_build)
        expected_version = "{} (build {})".format(version, build)
        if lite_version != expected_version:
            raise ValueError("Expected version does not match actual version: Expected={}  Actual={}".format(expected_version, lite_version))

        logging.info ("LiteServ: {} is running".format(lite_version))

        return url
