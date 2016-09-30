import logging
import os
import shutil
from zipfile import ZipFile
import time
import subprocess
import re
import json
import pdb
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

from exceptions import LiteServError


def version_and_build(full_version):
    version_parts = full_version.split("-")
    assert len(version_parts) == 2
    return version_parts[0], version_parts[1]


class LiteServ:

    def __init__(self):
        self._session = Session()
        self._session.headers['Content-Type'] = 'application/json'

    def verify_platform(self, platform):
        """Verify that we are installing a supported platform"""

        if platform not in ["macosx", "android", "net", "ios"]:
            raise LiteServError("Unsupported platform: {}".format(platform))

    def verify_storage_engine(self, storage_engine):
        logging.info(storage_engine)
        if storage_engine not in ["SQLite", "SQLCipher", "ForestDB", "ForestDB+Encryption"]:
            raise LiteServError("Unsupported storage engine: {}".format(storage_engine))

    def get_download_package_name(self, platform, version_build, storage_engine):

        self.verify_platform(platform)
        self.verify_storage_engine(storage_engine)

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

        elif platform == "ios":
            # TODO: Needs to be looked at when https://github.com/couchbaselabs/liteserv-ios/issues/1 is fixed
            package_name = ""

        log_info("Download package(s): {}".format(package_name))

        return package_name

    def get_binary(self, platform, version_build, storage_engine):

        version, build = version_and_build(version_build)

        self.verify_platform(platform)
        self.verify_storage_engine(storage_engine)

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
        elif platform == "ios":
            expected_binary = "couchbase-lite-ios-liteserv-{}.app".format(version_build)

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
        elif platform == "ios":
            # TODO: Needs to be looked at when https://github.com/couchbaselabs/liteserv-ios/issues/1 is fixed
            url = ""

        log_info("Download url: {}".format(url))

        return url

    def download_liteserv(self, platform, version, storage_engine):

        self.verify_platform(platform)
        self.verify_storage_engine(storage_engine)

        expected_binary = self.get_binary(platform, version, storage_engine)

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
            raise LiteServError("Standalone binaries only avaiable for Mac OSX and .NET")

        return binary_path

    def install_apk(self, version_build, storage_engine):

        binary = self.get_binary("android", version_build, storage_engine)

        apk_path = "{}/{}".format(BINARY_DIR, binary)
        log_info("Installing: {}".format(apk_path))

        install_successful = False
        while not install_successful:
            output = subprocess.check_output(["adb", "install", apk_path])
            log_info(output)
            if "INSTALL_FAILED_ALREADY_EXISTS" in output or "INSTALL_FAILED_UPDATE_INCOMPATIBLE" in output:
                log_info("APK already exists. Removing and trying again ...")
                output = subprocess.check_output(["adb", "uninstall", "com.couchbase.liteservandroid"])
                log_info(output)
            else:
                install_successful = True

    def launch_activity(self, port, storage_engine):

        self.verify_storage_engine(storage_engine)

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

    def install_and_launch_ios_app(self, version_build, storage_engine):
        """Launches LiteServ on iOS device
        Warning: Only works with a single device at the moment
        """

        binary = self.get_binary("ios", version_build, storage_engine)
        app_path = "{}/{}".format(BINARY_DIR, binary)
        log_info("Installing: {}".format(app_path))

        # install app / launch app to connected device
        output = subprocess.check_output([
            "ios-deploy", "--uninstall", "--justlaunch", "--debug", "--bundle", app_path
        ])
        log_info(output)

    def install_liteserv(self, platform, version, storage_engine):
        """Bootstraps install of LiteServ app (Android). Noop for Desktop cmd apps (ex. Mac OSX, .NET)

        :param platform: LiteServ Platform to install
        :param version: LiteServ Version to install
        :param storage_engine: Storage Engine to use when running tests
        """

        log_info("Installing LiteServ ({}, {}, {})".format(platform, version, storage_engine))

        self.verify_platform(platform)
        self.verify_storage_engine(storage_engine)

        if platform == "android":
            self.install_apk(version_build=version, storage_engine=storage_engine)
        elif platform == "ios":
            self.install_and_launch_ios_app(version_build=version, storage_engine=storage_engine)
        else:
            log_info("No install necessary. Skipping ...")

    def start_liteserv(self, platform, version, host, port, storage_engine, logfile):
        """
        Starts LiteServ for a specific provided platform.
        Returns a tuple of the listserv_url and the process_handle
        """

        self.verify_platform(platform)
        self.verify_storage_engine(storage_engine)

        log_info("Starting LiteServ: {} {} {}:{} using {}".format(platform, version, host, port, storage_engine))
        if platform == "macosx":
            proc_handle = self.start_macosx_liteserv(
                version=version,
                port=port,
                storage_engine=storage_engine,
                logfile=logfile
            )
        elif platform == "android":
            proc_handle = self.start_android_liteserv(
                host=host,
                port=port,
                storage_engine=storage_engine, logfile=logfile
            )
        elif platform == "net":
            proc_handle = self.start_net_liteserv(
                version=version,
                port=port,
                storage_engine=storage_engine,
                logfile=logfile
            )
        elif platform == "ios":
            proc_handle = self.start_ios_liteserv(
                host=host,
                port=port,
                storage_engine=storage_engine,
                logfile=logfile
            )

        # Verify LiteServ is launched with proper version and build
        ls_url = self.verify_liteserv_launched(
            platform=platform,
            host=host,
            port=port,
            version_build=version
        )

        return ls_url, proc_handle

    def shutdown_liteserv(self, host, platform, process_handle, logfile):
        """Kill a running LiteServ using the process_handle (Desktop apps)

        If the platform is Android, kill the activity via adb, and kill the process handle
        which is the adb logcat in this case
        """
        self.verify_platform(platform)

        log_info("Shutting down LiteServ ({}) and closing {}".format(platform, logfile))

        if platform == "android":
            self.stop_activity()
        elif platform == "ios":
            self.stop_ios_liteserv(host)

        logfile.flush()
        logfile.close()
        process_handle.kill()
        process_handle.wait()

    def start_android_liteserv(self, host, port, storage_engine, logfile):
        """Starts adb logcat capture and launches an installed LiteServ activity

        :param host: Listserv host where apk is installed
        :param port: Port to launch LiteServ activity on device
        :param storage_engine: Storage engine to enable in LiteServ
        :param logfile: File object to write adb logcat output to
        :return: Process handle for adb logcat
        """

        # Clear adb buffer
        subprocess.check_call(["adb", "logcat", "-c"])

        # Start logcat capture
        p = subprocess.Popen(args=["adb", "logcat"], stdout=logfile)

        self.launch_activity(port=port, storage_engine=storage_engine)

        return p

    def start_ios_liteserv(self, host, port, storage_engine, logfile):
        """Starts capturing logging via idevicesyslog and starts the application
        """

        p = subprocess.Popen(args=["idevicesyslog"], stdout=logfile)

        # make sure to stop liteserv if it is running
        self.stop_ios_liteserv(host)

        liteserv_admin_url = "http://{}:59850".format(host)
        log_info("Starting LiteServ: {}".format(liteserv_admin_url))

        data = {
            "port": int(port)
        }

        resp = self._session.put("{}/start".format(liteserv_admin_url), data=json.dumps(data))
        log_r(resp)
        resp.raise_for_status()

        return p

    def stop_ios_liteserv(self, host):
        """Stops an iOS LiteServ running on 'host'"""

        liteserv_admin_url = "http://{}:59850".format(host)
        log_info("Stopping LiteServ: {}".format(liteserv_admin_url))
        resp = self._session.put("{}/stop".format(liteserv_admin_url))
        log_r(resp)
        resp.raise_for_status()

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
        log_info("Launching: {}".format(binary_path))

        process_args = [
            binary_path,
            "-Log", "YES",
            "-LogSync", "YES",
            "-LogSyncVerbose", "YES",
            "-LogCBLRouter", "YES",
            "-LogRemoteRequest", "YES",
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
        log_info("Launching: {}".format(binary_path))

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

    def verify_liteserv_launched(self, platform, host, port, version_build):
        """Verify that the LiteServ is running with the expected version and platform.

        The retry loop is neccessary to account for a non zero time for launching a ListServ.

        :param platform: Expected running LiteServ platform
        :param host: Host to target for verification
        :param port: Port to target for verification
        :param version_build: Expected running LiteServ version
        :return: the url of the verified / running LiteServ
        """

        url = "http://{}:{}".format(host, port)

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
            raise LiteServError("Could not connect to LiteServ")

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
            if not is_macosx:
                raise LiteServError("Expected macosx to be running on port. Other platform detected")
        elif platform == "android":
            if not is_android:
                raise LiteServError("Expected android to be running on port. Other platform detected")
        elif platform == "net":
            if not is_net:
                raise LiteServError("Expected android to be running on port. Other platform detected")

        # Validate that the version launched is the expected LiteServ version
        # Mac OSX - LiteServ: 1.2.1 (build 13)
        version, build = version_and_build(version_build)
        if is_macosx:
            expected_version = "{} (build {})".format(version, build)
            if lite_version != expected_version:
                raise LiteServError("Expected version does not match actual version: Expected={}  Actual={}".format(expected_version, lite_version))
        elif is_android:
            if version == "1.2.1":
                # released binaries do not have a build number
                if lite_version != version:
                    raise LiteServError("Expected version does not match actual version: Expected={}  Actual={}".format(version, lite_version))
            else:
                if lite_version != version_build:
                    raise LiteServError("Expected version does not match actual version: Expected={}  Actual={}".format(version_build, lite_version))
        elif is_net:
            running_version_parts = re.split("[ /-]", lite_version)
            version = running_version_parts[5]
            build = int(running_version_parts[6].strip("build"))
            running_version_composed = "{}-{}".format(version, build)
            if version_build != running_version_composed:
                raise LiteServError("Expected version does not match actual version: Expected={}  Actual={}".format(version_build, running_version_composed))
        else:
            raise LiteServError("Unexpected Listener platform")

        log_info("LiteServ: {} is running at {}".format(lite_version, url))

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
        raise LiteServError("There should be no service running on the port")

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