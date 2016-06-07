import logging
import os
import shutil
from zipfile import ZipFile
import time
import subprocess
import re

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

    def __init__(self):
        self._session = Session()

    def get_download_package_name(self, platform, version_build):

        if platform == "macosx":
            package = "couchbase-lite-macosx-enterprise_{}.zip".format(version_build)
        elif platform == "android":
            version, build = version_and_build(version_build)
            if version == "1.2.1":
                package = "couchbase-lite-android-liteserv-SQLite-{}-debug.apk".format(version)
            else:
                package = "couchbase-lite-android-liteserv-SQLite-{}-debug.apk".format(version_build)
        elif platform == "net":
            package = "LiteServ.zip"
        else:
            raise ValueError("Unsupported platform")

        logging.info("Download package: {}".format(package))

        return package

    def get_extracted_package_name(self, platform, version_build):

        version, build = version_and_build(version_build)

        if platform == "macosx":
            extracted_file_name = "couchbase-lite-macosx-{}".format(version_build)
        elif platform == "android":
            if version == "1.2.1":
                extracted_file_name = "couchbase-lite-android-liteserv-SQLite-{}-debug.apk".format(version)
            else:
                extracted_file_name = "couchbase-lite-android-liteserv-SQLite-{}-debug.apk".format(version_build)
        elif platform == "net":
            extracted_file_name = "couchbase-lite-net-liteserv-{}".format(version_build)
        else:
            raise ValueError("Unsupported platform")

        logging.info("Extracted package: {}".format(extracted_file_name))

        return extracted_file_name

    def get_download_url(self, platform, version_build):
        logging.info("Downloading {} LiteServ, version: {}".format(platform, version_build))

        version, build = version_and_build(version_build)
        file_name = self.get_download_package_name(platform, version_build)

        if platform == "macosx":
            if version == "1.2.0":
                url = "{}/couchbase-lite-ios/release/{}/macosx/{}/{}".format(LATEST_BUILDS, version, version_build, file_name)
            else:
                url = "{}/couchbase-lite-ios/{}/macosx/{}/{}".format(LATEST_BUILDS, version, version_build, file_name)
        elif platform == "android":
            if version == "1.2.1":
                url = "{}/couchbase-lite-android/release/{}/{}/{}".format(LATEST_BUILDS, version, version_build, file_name)
            else:
                url = "{}/couchbase-lite-android/{}/{}/{}".format(LATEST_BUILDS, version, version_build, file_name)
        elif platform == "net":
            url = "{}/couchbase-lite-net/{}/{}/{}".format(LATEST_BUILDS, version, build, file_name)

        logging.info("Download url: {}".format(url))

        return url

    def download_liteserv(self, platform, version):

        supported_platforms = ["macosx", "android", "net"]
        if platform not in supported_platforms:
            raise ValueError("Unsupported version of LiteServ")

        extracted_file_name = self.get_extracted_package_name(platform, version)

        logging.info("{}/{}".format(BINARY_DIR, extracted_file_name))
        # Check if package is already downloaded and return if it is preset
        if os.path.isdir("{}/{}".format(BINARY_DIR, extracted_file_name)) or os.path.isfile("{}/{}".format(BINARY_DIR, extracted_file_name)):
            logging.info("Package exists: {}. Skipping download".format(extracted_file_name))
            return

        url = self.get_download_url(platform, version)
        file_name = self.get_download_package_name(platform, version)

        # Download the packages to binary directory
        print("Downloading: {}".format(url))
        resp = requests.get(url)
        resp.raise_for_status()
        with open("{}/{}".format(BINARY_DIR, file_name), "wb") as f:
            f.write(resp.content)

        if platform != "android":
            # Unzip the package
            with ZipFile("{}/{}".format(BINARY_DIR, file_name)) as zip_f:
                zip_f.extractall("{}/{}".format(BINARY_DIR, extracted_file_name))

            if platform == "macosx":
                # Make binary executable
                os.chmod("{}/{}/LiteServ".format(BINARY_DIR, extracted_file_name), 0755)

            # Remove .zip file
            os.remove("{}/{}".format(BINARY_DIR, file_name))

    def get_liteserv_binary_path(self, platform, version):

        extracted_file_name = self.get_extracted_package_name(platform, version)

        if platform == "macosx":
            binary_path = "{}/{}/LiteServ".format(BINARY_DIR, extracted_file_name)
        elif platform == "net":
            binary_path = "{}/{}/LiteServ.exe".format(BINARY_DIR, extracted_file_name)
        else:
            raise ValueError("Standalone binaries only avaiable for Mac OSX and .NET")

        logging.info(binary_path)
        return binary_path

    def install_apk(self, version_build):

        extracted_file_name = self.get_extracted_package_name("android", version_build)

        apk_path = "{}/{}".format(BINARY_DIR, extracted_file_name)
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

    def remove_liteserv(self, platform, version_build):
        logging.info("Removing {} LiteServ, version: {}".format(platform, version_build))
        os.chdir(BINARY_DIR)
        extracted_file_name = self.get_extracted_package_name(platform, version_build)
        shutil.rmtree(extracted_file_name)
        os.chdir("../..")

    def verify_liteserv_launched(self, host, port, version_build):

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
        version, build = version_and_build(version_build)
        if is_macosx:
            expected_version = "{} (build {})".format(version, build)
            assert lite_version == expected_version, "Expected version does not match actual version: Expected={}  Actual={}".format(expected_version, lite_version)
        elif is_android:
            if version == "1.2.1":
                # released binaries do not have a build number
                assert lite_version == version, "Expected version does not match actual version: Expected={}  Actual={}".format(version, lite_version)
            else:
                assert lite_version == version_build, "Expected version does not match actual version: Expected={}  Actual={}".format(version_build, lite_version)
        elif is_net:
            running_version_parts = re.split("[ /-]", lite_version)
            version = running_version_parts[5]
            build = int(running_version_parts[6].strip("build"))
            running_version_composed = "{}-{}".format(version, build)
            assert version_build == running_version_composed, "Expected version does not match actual version: Expected={}  Actual={}".format(version_build, running_version_composed)
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