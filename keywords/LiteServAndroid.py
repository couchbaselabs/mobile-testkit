import os
import subprocess
from zipfile import ZipFile

import requests

from keywords.LiteServBase import LiteServBase
from keywords.constants import LATEST_BUILDS
from keywords.constants import BINARY_DIR
from keywords.constants import RESULTS_DIR
from keywords.constants import REGISTERED_CLIENT_DBS
from keywords.exceptions import LiteServError
from keywords.utils import version_and_build
from keywords.utils import log_info


class LiteServAndroid(LiteServBase):

    def download(self):
        """
        1. Check to see if .apk is downloaded already. If so, return
        2. Download the LiteServ .apk from latest builds to 'deps/binaries'
        """

        version, build = version_and_build(self.version_build)

        if version == "1.2.1":
            package_name = "couchbase-lite-android-liteserv-SQLite-{}-debug.apk".format(self.version_build)
        else:
            if self.storage_engine == "SQLite":
                package_name = "couchbase-lite-android-liteserv-SQLite-{}-debug.apk".format(self.version_build)
            else:
                package_name = "couchbase-lite-android-liteserv-SQLCipher-ForestDB-Encryption-{}-debug.apk".format(self.version_build)

        expected_binary_path = "{}/{}".format(BINARY_DIR, package_name)
        if os.path.isfile(expected_binary_path):
            log_info("Package is already downloaded. Skipping.")
            return

        # Package not downloaded, proceed to download from latest builds
        if version == "1.2.1":
            url = "{}/couchbase-lite-android/release/{}/{}/{}".format(LATEST_BUILDS, version, self.version_build, package_name)
        else:
            url = "{}/couchbase-lite-android/{}/{}/{}".format(LATEST_BUILDS, version, self.version_build, package_name)

        log_info("Downloading {} -> {}/{}".format(url, BINARY_DIR, package_name))
        resp = requests.get(url)
        resp.raise_for_status()
        with open("{}/{}".format(BINARY_DIR, package_name), "wb") as f:
            f.write(resp.content)

    def install(self):
        """Install the apk to running Android device or emulator"""

        if self.storage_engine == "SQLite":
            apk_name = "couchbase-lite-android-liteserv-SQLite-{}-debug.apk".format(self.version_build)
        else:
            apk_name = "couchbase-lite-android-liteserv-SQLCipher-ForestDB-Encryption-{}-debug.apk".format(self.version_build)

        apk_path = "{}/{}".format(BINARY_DIR, apk_name)
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

    def start(self, logfile=None):
        """
        1. Starts a LiteServ with logging to provided logfile file object.
           The running LiteServ process will be stored in the self.process property.
        2. The method will poll on the endpoint to make sure LiteServ is available.
        3. The expected version will be compared with the version reported by http://<host>:<port>
        4. eturn the url of the running LiteServ
        """

        if not isinstance(logfile, file):
            raise LiteServError("logfile must be of type 'file'")

        self._verify_not_running()

        log_info("Using storage engine: {}".format(self.storage_engine))

        activity_name = "com.couchbase.liteservandroid/com.couchbase.liteservandroid.MainActivity"

        encryption_enabled = False
        if self.storage_engine == "SQLCipher" or self.storage_engine == "ForestDB+Encryption":
            encryption_enabled = True

        if encryption_enabled:
            log_info("Encryption enabled ...")
            db_passwords = self.build_name_passwords_for_registered_dbs("android")
            if self.storage_engine == "SQLCipher":
                output = subprocess.check_output([
                    "adb", "shell", "am", "start", "-n", activity_name,
                    "--es", "username", "none",
                    "--es", "password", "none",
                    "--ei", "listen_port", str(self.port),
                    "--es", "storage", "SQLite",
                    "--es", "dbpassword", db_passwords
                ])
                log_info(output)
            elif self.storage_engine == "ForestDB+Encryption":
                output = subprocess.check_output([
                    "adb", "shell", "am", "start", "-n", activity_name,
                    "--es", "username", "none",
                    "--es", "password", "none",
                    "--ei", "listen_port", str(self.port),
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
                "--ei", "listen_port", str(self.port),
                "--es", "storage", self.storage_engine,
            ])
            log_info(output)

        self._verify_launched()

        return "http://{}:{}".format(self.host, self.port)

    def _verify_launched(self):
        """ Poll on expected http://<host>:<port> until it is reachable
        Assert that the response contains the expected version information
        """
        resp_obj = self._wait_until_reachable()
        log_info(resp_obj)
        if resp_obj["version"] != self.version_build:
            raise LiteServError("Expected version: {} does not match running version: {}".format(self.version_build, resp_obj["version"]))

    def stop(self, logfile):
        """
        1. Flush and close the logfile capturing the LiteServ output
        2. Kill the LiteServ activity and clear the package data
        """
        if not isinstance(logfile, file):
            raise LiteServError("logfile must be of type 'file'")

        output = subprocess.check_output([
            "adb", "shell", "am", "force-stop", "com.couchbase.liteservandroid"
        ])
        log_info(output)

        # Clear package data
        output = subprocess.check_output([
            "adb", "shell", "pm", "clear", "com.couchbase.liteservandroid"
        ])
        log_info(output)

        self._verify_not_running()


