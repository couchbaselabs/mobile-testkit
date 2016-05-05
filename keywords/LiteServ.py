import logging
import os
import shutil
from zipfile import ZipFile
import time
import subprocess

import requests
from requests.sessions import Session
from requests.exceptions import ConnectionError

from robot.api.logger import console

from constants import *


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
            # TODO package with version and build
            self.extracted_file_name = "couchbase-lite-net-listenerconsole-{}".format(self._version_build)

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
            # TODO, requires package to be published via latestbuilds.
            # https://github.com/couchbase/couchbase-lite-net/issues/639
            pass
        elif self._platform == "net":
            # TODO, requires package to be published via latestbuilds.
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
            binary_path = "{}/{}/Listener.exe".format(BINARY_DIR, self.extracted_file_name)
        else:
            raise ValueError("Unsupported standalone LiteServ binary")

        logging.info(binary_path)
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

    def stop_activity(self):
        # Stop LiteServ Activity
        output = subprocess.check_output([
            "adb", "shell", "am", "force-stop", "com.couchbase.liteservandroid"
        ])
        logging.info(output)

        # Clear package data
        output = subprocess.check_output([
            "adb", "shell", "pm", "clear", "com.couchbase.liteservandroid"
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
        is_macosx = False
        is_net = False
        is_android = False
        try:
            # Mac OSX
            lite_version = resp_json["vendor"]["version"]
            if resp_json["vendor"]["name"] == "Couchbase Lite (Objective-C)":
                is_macosx = True
            elif resp_json["vendor"]["name"] == "Couchbase Lite (C#)":
                is_net = True
        except KeyError as e:
            # Android
            lite_version = resp_json["version"]
            is_android = True

        # Validate that the version launched is the expected LiteServ version
        # Mac OSX - LiteServ: 1.2.1 (build 13)
        version, build = version_and_build(self._version_build)
        if is_macosx:
            expected_version = "{} (build {})".format(version, build)
            assert lite_version == expected_version, "Expected version does not match actual version: Expected={}  Actual={}".format(expected_version, lite_version)
        elif is_android:
            expected_version = version
            assert lite_version == expected_version, "Expected version does not match actual version: Expected={}  Actual={}".format(expected_version, lite_version)
        elif is_net:
            pass
            #running_version = lite_version.split()[-1]
            # TODO Get version / build instead of just version
            #assert self._version_build == "", "Expected version does not match actual version: Expected={}  Actual={}".format(self._version_build, running_version_stripped)
        else:
            raise ValueError("Unexpected Listener platform")

        logging.info ("LiteServ: {} is running".format(lite_version))

        return url

    def start_mono_process(self, path, port):
        logging.info("Starting mono process: {}".format(path))
        self._mono_process = subprocess.Popen(["mono", path, "--port={}".format(port)])

    def kill_mono_process(self):
        self._mono_process.kill()
        self._mono_process.wait()
        logging.info(self._mono_process.returncode)