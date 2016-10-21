import os
import subprocess

import requests

from keywords.LiteServBase import LiteServBase
from keywords.constants import LATEST_BUILDS
from keywords.constants import BINARY_DIR
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

        output = subprocess.check_output(["adb", "install", apk_path])
        if "INSTALL_FAILED_ALREADY_EXISTS" in output or "INSTALL_FAILED_UPDATE_INCOMPATIBLE" in output:
            raise LiteServError("Error. APK already exists.")

        output = subprocess.check_output(["adb", "shell", "pm", "list", "packages"])
        if "com.couchbase.liteservandroid" not in output:
            raise LiteServError("Failed to install package")

        log_info("LiteServ installed to {}".format(self.host))

    def remove(self):
        """Removes the LiteServ application from the running device
        """
        output = subprocess.check_output(["adb", "uninstall", "com.couchbase.liteservandroid"])
        if output.strip() != "Success":
            log_info(output)
            raise LiteServError("Error. Could not remove app.")

        output = subprocess.check_output(["adb", "shell", "pm", "list", "packages"])
        if "com.couchbase.liteservandroid" in output:
            raise LiteServError("Error uninstalling app!")

        log_info("LiteServ removed from {}".format(self.host))

    def start(self, logfile_name):
        """
        1. Starts a LiteServ with adb logging to provided logfile file object.
            The adb process will be stored in the self.process property
        2. Start the Android activity with a launch dictionary
        2. The method will poll on the endpoint to make sure LiteServ is available.
        3. The expected version will be compared with the version reported by http://<host>:<port>
        4. Return the url of the running LiteServ
        """

        self._verify_not_running()

        # Clear adb buffer
        subprocess.check_call(["adb", "logcat", "-c"])

        # Start redirecting adb output to the logfile
        self.logfile = open(logfile_name, "w")
        self.process = subprocess.Popen(args=["adb", "logcat"], stdout=self.logfile)

        log_info("Using storage engine: {}".format(self.storage_engine))

        activity_name = "com.couchbase.liteservandroid/com.couchbase.liteservandroid.MainActivity"

        encryption_enabled = False
        if self.storage_engine == "SQLCipher" or self.storage_engine == "ForestDB+Encryption":
            encryption_enabled = True

        if encryption_enabled:
            log_info("Encryption enabled ...")

            # Build list of dbs used in the tests and pass them to the activity
            # to make sure the dbs are encrypted during the tests
            db_flags = []
            for db_name in REGISTERED_CLIENT_DBS:
                db_flags.append("{}:pass".format(db_name))
            db_flags = ",".join(db_flags)

            log_info("Running with db_flags: {}".format(db_flags))

            if self.storage_engine == "SQLCipher":
                output = subprocess.check_output([
                    "adb", "shell", "am", "start", "-n", activity_name,
                    "--es", "username", "none",
                    "--es", "password", "none",
                    "--ei", "listen_port", str(self.port),
                    "--es", "storage", "SQLite",
                    "--es", "dbpassword", db_flags
                ])
                log_info(output)
            elif self.storage_engine == "ForestDB+Encryption":
                output = subprocess.check_output([
                    "adb", "shell", "am", "start", "-n", activity_name,
                    "--es", "username", "none",
                    "--es", "password", "none",
                    "--ei", "listen_port", str(self.port),
                    "--es", "storage", "ForestDB",
                    "--es", "dbpassword", db_flags
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

    def stop(self):
        """
        1. Flush and close the logfile capturing the LiteServ output
        2. Kill the LiteServ activity and clear the package data
        3. Kill the adb logcat process
        """

        log_info("Stopping LiteServ: http://{}:{}".format(self.host, self.port))

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

        self.logfile.flush()
        self.logfile.close()
        self.process.kill()
        self.process.wait()
