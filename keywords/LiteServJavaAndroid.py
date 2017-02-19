import os
import subprocess

import requests

from keywords.LiteServAndroid import LiteServAndroid
from keywords.constants import LATEST_BUILDS
from keywords.constants import BINARY_DIR
from keywords.constants import REGISTERED_CLIENT_DBS
from keywords.utils import version_and_build
from keywords.utils import log_info
from keywords.exceptions import LiteServError


class LiteServJavaAndroid(LiteServAndroid):
    activity_name = "com.couchbase.liteservandroid/com.couchbase.liteservandroid.MainActivity"

    def download(self):
        """
        1. Check to see if .apk is downloaded already. If so, return
        2. Download the LiteServ .apk from latest builds to 'deps/binaries'
        """

        version, _ = version_and_build(self.version_build)

        if version == "1.2.1":
            package_name = "couchbase-lite-android-liteserv-SQLite-{}-debug.apk".format(
                self.version_build)
        else:
            if self.storage_engine == "SQLite":
                package_name = "couchbase-lite-android-liteserv-SQLite-{}-debug.apk".format(
                    self.version_build)
            else:
                package_name = "couchbase-lite-android-liteserv-SQLCipher-\
                ForestDB-Encryption-{}-debug.apk".format(
                    self.version_build)

        expected_binary_path = "{}/{}".format(BINARY_DIR, package_name)
        if os.path.isfile(expected_binary_path):
            log_info("Package is already downloaded. Skipping.")
            return

        # Package not downloaded, proceed to download from latest builds
        if version == "1.2.1":
            url = "{}/couchbase-lite-android/release/{}/{}/{}".format(
                LATEST_BUILDS, version, self.version_build, package_name)
        else:
            url = "{}/couchbase-lite-android/{}/{}/{}".format(
                LATEST_BUILDS, version, self.version_build, package_name)

        log_info("Downloading {} -> {}/{}".format(url, BINARY_DIR, package_name))
        resp = requests.get(url)
        resp.raise_for_status()
        with open("{}/{}".format(BINARY_DIR, package_name), "wb") as f:
            f.write(resp.content)

    def install(self):
        if self.storage_engine == "SQLite":
            apk_name = "couchbase-lite-android-liteserv-SQLite-{}-debug.apk".format(
                self.version_build)
        else:
            apk_name = "couchbase-lite-android-liteserv-SQLCipher-\
            ForestDB-Encryption-{}-debug.apk".format(self.version_build)

        apk_path = "{}/{}".format(BINARY_DIR, apk_name)
        self.install_apk(apk_path, "com.couchbase.liteservandroid")

    def stop(self):
        self.stop_activity("com.couchbase.liteservandroid")

    def remove(self):
        self.remove_apk("com.couchbase.liteservandroid")

    def launch_and_verify(self):

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
                    "adb", "shell", "am", "start", "-n", self.activity_name,
                    "--es", "username", "none",
                    "--es", "password", "none",
                    "--ei", "listen_port", str(self.port),
                    "--es", "storage", "SQLite",
                    "--es", "dbpassword", db_flags
                ])
                log_info(output)
            elif self.storage_engine == "ForestDB+Encryption":
                output = subprocess.check_output([
                    "adb", "shell", "am", "start", "-n", self.activity_name,
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
                "adb", "shell", "am", "start", "-n", self.activity_name,
                "--es", "username", "none",
                "--es", "password", "none",
                "--ei", "listen_port", str(self.port),
                "--es", "storage", self.storage_engine,
            ])
            log_info(output)

            self._verify_launched()

    def _verify_launched(self):
        """ Poll on expected http://<host>:<port> until it is reachable
                Assert that the response contains the expected version information
                """
        resp_obj = self._wait_until_reachable()
        log_info(resp_obj)
        if resp_obj["version"] != self.version_build:
            raise LiteServError("Expected version: {} does not match running version: {}".format(
                self.version_build, resp_obj["version"]))
