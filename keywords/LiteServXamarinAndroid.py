import subprocess
import time
import os
from zipfile import ZipFile

import requests
from requests.exceptions import ConnectionError
from keywords.LiteServAndroid import LiteServAndroid
from keywords.LiteServBase import LiteServError
from keywords.constants import LATEST_BUILDS
from keywords.constants import BINARY_DIR
from keywords.constants import REGISTERED_CLIENT_DBS
from keywords.constants import MAX_RETRIES
from keywords.utils import version_and_build
from keywords.utils import log_info


class LiteServXamarinAndroid(LiteServAndroid):

    activity_name = "com.couchbase.liteserv/com.couchbase.liteserv.MainActivity"

    def download(self):
        """
        1. Check to see if .apk is downloaded already. If so, return
        2. Download the LiteServ .apk from latest builds to 'deps/binaries'
        """

        version, build = version_and_build(self.version_build)

        package_name = "LiteServ.zip"
        downloaded_package_zip_name = "{}/{}".format(BINARY_DIR, package_name)
        extracted_directory_name = downloaded_package_zip_name.replace(
            ".zip", "-{}-{}".format(version, build))
        expected_binary_path = "{}/Android/LiteServ.apk".format(
            extracted_directory_name)
        log_info(expected_binary_path)
        if os.path.isfile(expected_binary_path):
            log_info("Package is already downloaded. Skipping.")
            return

        # Package not downloaded, proceed to download from latest builds
        url = "{}/couchbase-lite-net/{}/{}/{}".format(LATEST_BUILDS, version, build, package_name)

        log_info("Downloading {} -> {}/{}".format(url, BINARY_DIR, package_name))
        resp = requests.get(url)
        resp.raise_for_status()
        with open("{}/{}".format(BINARY_DIR, package_name), "wb") as fout:
            fout.write(resp.content)

        with ZipFile("{}".format(downloaded_package_zip_name)) as zip_f:
            zip_f.extractall("{}".format(extracted_directory_name))

        # Remove .zip
        os.remove("{}".format(downloaded_package_zip_name))

    def install(self):
        version, build = version_and_build(self.version_build)
        apk_name = "LiteServ.apk"
        folder_name = "LiteServ-{}-{}/Android".format(version, build)
        apk_path = "{}/{}/{}".format(BINARY_DIR, folder_name, apk_name)

        self.install_apk(apk_path, "com.couchbase.liteserv")

    def stop(self):
        self.stop_activity("com.couchbase.liteserv")

    def remove(self):
        self.remove_apk("com.couchbase.liteserv")

    def launch_and_verify(self):
        output = subprocess.check_output([
            "adb", "shell", "am", "start", "-n", self.activity_name,
        ])
        log_info(output)

    def start(self, logfile_name):
        ret_val = super(LiteServXamarinAndroid, self).start(logfile_name)
        encryption_enabled = False
        if self.storage_engine == "SQLCipher" or self.storage_engine == "ForestDB+Encryption":
            encryption_enabled = True

        post_data = {
            "port": self.port
        }

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
                post_data["dbpassword"] = db_flags
            elif self.storage_engine == "ForestDB+Encryption":
                post_data["dbpassword"] = db_flags
                post_data["storage"] = "ForestDB"

        self._send_initial_request(post_data)
        self._verify_launched()

        return ret_val

    def _send_initial_request(self, post_data):
        url = "http://{}:59840/test".format(self.host)
        count = 0
        while count < MAX_RETRIES:
            try:
                self.session.post(url, json=post_data)
                # If request does not throw, exit retry loop
                break
            except ConnectionError:
                log_info("LiteServ may not be launched (Retrying) ...")
                time.sleep(1)
                count += 1

        if count == MAX_RETRIES:
            raise LiteServError("Could not send initial request to LiteServ")

    def _verify_launched(self):
        """ Poll on expected http://<host>:<port> until it is reachable
        Assert that the response contains the expected version information
        """
        resp_obj = self._wait_until_reachable()
        log_info(resp_obj)

        # Version format - 'version': '.NET LGE Nexus 5 API23/armeabi-v7a 1.4-b044/3ba174e'
        version_info = resp_obj["version"].split()[-1]

        # 1.4-b044/3ba174e
        resp_version_build = version_info.split("/")[0]

        # 1.4-b044
        version_build_parts = resp_version_build.split("-")
        version = version_build_parts[0]

        # Strip b and leading 0's
        build = str(int(version_build_parts[1].replace("b", "")))

        # Format as 1.4-44
        running_version_build = "{}-{}".format(version, build)

        if running_version_build != self.version_build:
            raise LiteServError("Expected version: {} does not match running version: {}".format(
                self.version_build, running_version_build))
