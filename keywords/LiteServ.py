import logging
import os
import shutil
from zipfile import ZipFile
import time
import subprocess
import re
import pytest

from keywords.constants import RESULTS_DIR

import requests
from requests.sessions import Session
from requests.exceptions import ConnectionError

from constants import BINARY_DIR
from constants import LATEST_BUILDS
from constants import MAX_RETRIES
from constants import REGISTERED_CLIENT_DBS
from constants import RESULTS_DIR

from utils import log_info
from utils import log_r

def version_and_build(full_version):
    version_parts = full_version.split("-")
    assert len(version_parts) == 2
    return version_parts[0], version_parts[1]

class LiteServ:

    def __init__(self):
        self._session = Session()

    def valid_storage_engine(self, storage_engine):
        logging.info(storage_engine)
        if storage_engine in ["SQLite", "SQLCipher", "ForestDB", "ForestDB+Encryption"]:
            return True
        else:
            return False

    def get_download_package_name(self, platform, version_build, storage_engine):

        if platform == "macosx":
            package_name = "couchbase-lite-macosx-enterprise_{}.zip".format(version_build)
        elif platform == "android":
            version, build = version_and_build(version_build)
            if version == "1.2.1":
                package_name = "couchbase-lite-android-liteserv-SQLite-{}-debug.apk".format(version)
            else:
                if storage_engine == "SQLite":
                    package_name = "couchbase-lite-android-liteserv-SQLite-{}-debug.apk".format(version_build)
                else:
                    package_name = "couchbase-lite-android-liteserv-SQLCipher-ForestDB-Encryption-{}-debug.apk".format(version_build)
        elif platform == "net":
            package_name = "LiteServ.zip"
        else:
            raise ValueError("Unsupported platform")

        log_info("Download package(s): {}".format(package_name))

        return package_name

    def get_binary(self, platform, version_build, storage_engine):

        version, build = version_and_build(version_build)

        if platform == "macosx":
            expected_binary = "couchbase-lite-macosx-enterprise_{}/LiteServ".format(version_build)
        elif platform == "android":
            if version == "1.2.1":
                expected_binary = "couchbase-lite-android-liteserv-SQLite-{}-debug.apk".format(version)
            else:
                if storage_engine == "SQLite":
                    expected_binary = "couchbase-lite-android-liteserv-SQLite-{}-debug.apk".format(version_build)
                else:
                    expected_binary = "couchbase-lite-android-liteserv-SQLCipher-ForestDB-Encryption-{}-debug.apk".format(version_build)
        elif platform == "net":
            expected_binary = "couchbase-lite-net-{}-liteserv/LiteServ.exe".format(version_build)
        else:
            raise ValueError("Unsupported platform")

        log_info("Binary: {}".format(expected_binary))

        return expected_binary

    def get_download_url(self, platform, version_build, storage_engine):
        log_info("Downloading {} LiteServ, version: {}".format(platform, version_build))

        version, build = version_and_build(version_build)
        file_name = self.get_download_package_name(platform, version_build, storage_engine)

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

        log_info("Download url: {}".format(url))

        return url

    def download_liteserv(self, platform, version, storage_engine):

        if platform not in ["macosx", "android", "net"]:
            raise ValueError("Unsupported platform of LiteServ: ".format(platform))

        if storage_engine not in ["SQLite", "SQLCipher", "ForestDB", "ForestDB+Encryption"]:
            raise ValueError("Unsupported storage engine for LiteServ: {}".format(storage_engine))

        expected_binary = self.get_binary(platform, version, storage_engine)
        log_info("{}/{}".format(BINARY_DIR, expected_binary))

        # Check if package is already downloaded and return if it is preset
        packages_present = True
        binary_path = "{}/{}".format(BINARY_DIR, expected_binary)
        if not os.path.isfile(binary_path):
            packages_present = False
            log_info("Package does not exists: {}. Downloading ...".format(binary_path))
        else:
            log_info("Found package: {}".format(binary_path))

        if packages_present:
            # All expected packages have already been downloaded. Short circuit.
            log_info("Found packages. Skipping download!!")
            return

        # Download the packages to binary directory
        url = self.get_download_url(platform, version, storage_engine)
        file_name = url.split("/")[-1]
        log_info("Downloading {} -> {}/{}".format(url, BINARY_DIR, file_name))
        resp = requests.get(url)
        resp.raise_for_status()
        with open("{}/{}".format(BINARY_DIR, file_name), "wb") as f:
            f.write(resp.content)

        if platform != "android":
            # Unzip the package
            if platform == "net":
                # hack to get unzip the net 'LiteServ.zip' into a folder name that has the
                # that has more information (version, etc)
                # http://latestbuilds.hq.couchbase.com/couchbase-lite-net/1.3.0/41/LiteServ.zip
                url_parts = url.split("/")
                directory_name = "{}-{}-{}-liteserv".format(url_parts[3], url_parts[4], url_parts[5])
            else:
                directory_name = file_name.replace(".zip", "")

            with ZipFile("{}/{}".format(BINARY_DIR, file_name)) as zip_f:
                zip_f.extractall("{}/{}".format(BINARY_DIR, directory_name))

            if platform == "macosx":
                # Make binary executable
                os.chmod("{}/{}/LiteServ".format(BINARY_DIR, directory_name), 0755)
            elif platform == "net":
                # Remove x64 and x86 HACK - To get around https://github.com/couchbase/couchbase-lite-net/issues/672
                # Need to remove once the issue is resolved
                shutil.rmtree("{}/{}/x64".format(BINARY_DIR, directory_name))
                shutil.rmtree("{}/{}/x86".format(BINARY_DIR, directory_name))

                # Remove .zip file
                os.remove("{}/{}".format(BINARY_DIR, file_name))

    def get_liteserv_binary_path(self, platform, version, storage_engine):

        binary_name = self.get_binary(platform, version, storage_engine)

        if platform == "macosx" or platform == "net":
            binary_path = "{}/{}".format(BINARY_DIR, binary_name)
        else:
            raise ValueError("Standalone binaries only avaiable for Mac OSX and .NET")

        log_info("Launching binary: {}".format(binary_path))
        return binary_path

    def install_apk(self, version_build, storage_engine):

        binary = self.get_binary("android", version_build, storage_engine)

        apk_path = "{}/{}".format(BINARY_DIR, binary)
        log_info("Installing: {}".format(apk_path))
        log_info(apk_path)

        install_successful = False
        while not install_successful:
            output = subprocess.check_output(["adb", "install", apk_path])
            log_info(output)
            if "INSTALL_FAILED_ALREADY_EXISTS" in output or "INSTALL_FAILED_UPDATE_INCOMPATIBLE" in output:
                logging.error("APK already exists. Removing and trying again ...")
                output = subprocess.check_output(["adb", "uninstall", "com.couchbase.liteservandroid"])
                log_info(output)
            else:
                install_successful = True

    def launch_activity(self, port, storage_engine):

        valid_storage_engines = [
            "SQLite",
            "SQLCipher",
            "ForestDB",
            "ForestDB+Encryption"
        ]

        assert storage_engine in valid_storage_engines, "Make sure the storage engine you provided is in: {}".format(valid_storage_engines)

        log_info("Using storage engine: {}".format(storage_engine))

        activity_name = "com.couchbase.liteservandroid/com.couchbase.liteservandroid.MainActivity"

        encryption_enabled = False
        if storage_engine == "SQLCipher" or storage_engine == "ForestDB+Encryption":
            encryption_enabled = True

        if encryption_enabled:
            log_info("Encryption enabled ...")
            db_passwords = self.build_name_passwords_for_registered_dbs("android")
            if storage_engine == "SQLCipher":
                output = subprocess.check_output([
                    "adb", "shell", "am", "start", "-n", activity_name,
                    "--es", "username", "none",
                    "--es", "password", "none",
                    "--ei", "listen_port", port,
                    "--es", "storage", "SQLite",
                    "--es", "dbpassword", db_passwords
                ])
                log_info(output)
            elif storage_engine == "ForestDB+Encryption":
                output = subprocess.check_output([
                    "adb", "shell", "am", "start", "-n", activity_name,
                    "--es", "username", "none",
                    "--es", "password", "none",
                    "--ei", "listen_port", port,
                    "--es", "storage", "ForestDB",
                    "--es", "dbpassword", db_passwords
                ])
                log_info(output)
        else:
            log_info("No encryption ...")
            output = subprocess.check_output([
                "adb", "shell", "am", "start", "-n", activity_name,
                "--es", "username", "none",
                "--es", "password", "none",
                "--ei", "listen_port", port,
                "--es", "storage", storage_engine,
            ])
            log_info(output)

    def start_liteserv(self, platform, version, host, port, storage_engine, logfile):
        """
        Starts LiteServ for a specific provided platform.
        Returns a tuple of the listserv_url and the process_handle
        """

        if not self.valid_storage_engine(storage_engine):
            raise ValueError("Invalid Storage Engine: {}".format(storage_engine))

        logging.info("Starting LiteServ: {} {} {}:{} using {}".format(platform, version, host, port, storage_engine))
        if platform == "macosx":
            proc_handle = self.start_macosx_liteserv(
                version=version,
                port=port,
                storage_engine=storage_engine,
                logfile=logfile
            )
        elif platform == "android":
            raise NotImplementedError("Unsupported LiteServ Platform")
        elif platform == "net":
            proc_handle = self.start_net_liteserv(
                version=version,
                port=port,
                storage_engine=storage_engine,
                logfile=logfile
            )
        else:
            raise NotImplementedError("Unsupported LiteServ Platform")

        ls_url = self.verify_liteserv_launched(
            platform=platform,
            host=host,
            port=port,
            version_build=version
        )

        return ls_url, proc_handle

    def shutdown_liteserv(self, process_handle, logfile):
        logfile.flush()
        logfile.close()
        process_handle.kill()
        process_handle.wait()

    def start_macosx_liteserv(self, version, port, storage_engine, logfile):
        """
        Launches a Mac OSX LiteServ listener on the machine running the tests bound to localhost:<port>

        :param version: Version (ex. 1.3.1-6) of LiteServ to launch
        :param port: The localhost port to bind to
        :param storage_engine: The storage engine to launch LiteServ with
        :param logfile: file to log the process output to
        :return: the process handle
        """

        binary_path = self.get_liteserv_binary_path(
            "macosx",
            version=version,
            storage_engine=storage_engine
        )
        process_args = [
            binary_path,
            "--port", port,
            "--dir", "{}/dbs/macosx/".format(RESULTS_DIR)
        ]

        if storage_engine == "ForestDB" or storage_engine == "ForestDB+Encryption":
            process_args.append("--storage")
            process_args.append("ForestDB")
        else:
            process_args.append("--storage")
            process_args.append("SQLite")

        if storage_engine == "SQLCipher" or storage_engine == "ForestDB+Encryption":
            logging.info("Using Encryption ...")
            db_name_passwords = self.build_name_passwords_for_registered_dbs(platform="macosx")
            process_args.extend(db_name_passwords)

        p = subprocess.Popen(args=process_args, stderr=logfile)
        return p

    def start_net_liteserv(self, version, port, storage_engine, logfile):
        """
        Launches a Mac OSX .NET LiteServ listener on the machine running the tests bound to localhost:<port>

        :param version: Version (ex. 1.3.1-13) of LiteServ to launch
        :param port: The localhost port to bind to
        :param storage_engine: The storage engine to launch LiteServ with
        :param logfile: file to log the process output to
        :return: the process handle
        """

        binary_path = self.get_liteserv_binary_path(
            "net",
            version=version,
            storage_engine=storage_engine
        )
        process_args = [
            "mono",
            binary_path,
            "--port", port,
            "--dir", "{}/dbs/net/".format(RESULTS_DIR)
        ]

        if storage_engine == "ForestDB" or storage_engine == "ForestDB+Encryption":
            process_args.append("--storage")
            process_args.append("ForestDB")
        else:
            process_args.append("--storage")
            process_args.append("SQLite")

        if storage_engine == "SQLCipher" or storage_engine == "ForestDB+Encryption":
            logging.info("Using Encryption ...")
            db_name_passwords = self.build_name_passwords_for_registered_dbs(platform="macosx")
            process_args.extend(db_name_passwords)

        p = subprocess.Popen(args=process_args, stdout=logfile)
        return p

    def stop_activity(self):
        # Stop LiteServ Activity
        output = subprocess.check_output([
            "adb", "shell", "am", "force-stop", "com.couchbase.liteservandroid"
        ])
        log_info(output)

        # Clear package data
        output = subprocess.check_output([
            "adb", "shell", "pm", "clear", "com.couchbase.liteservandroid"
        ])
        log_info(output)

    def remove_liteserv(self, platform, version_build):
        log_info("Removing {} LiteServ, version: {}".format(platform, version_build))
        os.chdir(BINARY_DIR)
        extracted_file_name = self.get_extracted_package_name(platform, version_build)
        shutil.rmtree(extracted_file_name)
        os.chdir("../..")

    def verify_liteserv_launched(self, platform, host, port, version_build):

        url = "http://{}:{}".format(host, port)
        log_info("Verifying LiteServ running at {}".format(url))

        count = 0
        while count < MAX_RETRIES:
            try:
                resp = self._session.get(url)
                # If request does not throw, exit retry loop
                break
            except ConnectionError as ce:
                log_info("LiteServ may not be launched (Retrying): {}".format(ce))
                time.sleep(1)
                count += 1

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

        # Validate the running platform is the expected platform
        if platform == "macosx":
            assert is_macosx, "Tried to run macosx but different platform running on {}:{} ...".format(host, port)
        elif platform == "android":
            assert is_android, "Tried to run android but different platform running on {}:{} ...".format(host, port)
        elif platform == "net":
            assert is_net, "Tried to run net but different platform running on {}:{} ...".format(host, port)
        else:
            raise ValueError("Unsupported platform: {}".format(platform))

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

        log_info("LiteServ: {} is running".format(lite_version))

        return url

    def verify_liteserv_not_running(self, host, port):
        """
        Verifys that the endpoint does not return a 200 from a running service
        """
        try:
            resp = self._session.get("http://{}:{}/".format(host, port))
        except ConnectionError as e:
            # Expecting connection error if LiteServ is not running on the port
            return

        log_r(resp)
        raise AssertionError("There should be no service running on the port")


    def build_name_passwords_for_registered_dbs(self, platform):
        """
        Returns a list of name=password for each db in registered dbs
        to allow the db to be encrypted for Mac OSX / .NET LiteServ
        """

        db_flags = []
        for db_name in REGISTERED_CLIENT_DBS:
            if platform == "macosx" or platform == "net":
                db_flags.append("--dbpassword")
                db_flags.append("{}=pass".format(db_name))
            elif platform == "android":
                db_flags.append("{}:pass".format(db_name))

        if platform == "android":
            db_flags = ",".join(db_flags)

        log_info("Launching LiteServ ({}) with dbpassword flags: {}".format(platform, db_flags))

        return db_flags