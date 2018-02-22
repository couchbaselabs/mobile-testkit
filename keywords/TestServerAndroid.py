import os
import subprocess

import requests

from keywords.TestServerBase import TestServerBase
from keywords.constants import LATEST_BUILDS
from keywords.constants import BINARY_DIR
from keywords.exceptions import LiteServError
from keywords.utils import version_and_build
from keywords.utils import log_info


class TestServerAndroid(TestServerBase):

    def __init__(self, version_build, host, port, community_enabled=None):
        super(TestServerAndroid, self).__init__(version_build, host, port)
        if community_enabled:
            self.apk_name = "CBLTestServer-Android-{}-community-debug.apk".format(self.version_build)
        else:
            self.apk_name = "CBLTestServer-Android-{}-enterprise-debug.apk".format(self.version_build)
        self.package_name = self.apk_name

    def download(self, version_build=None):
        """
        1. Check to see if .apk is downloaded already. If so, return
        2. Download the Testserver .apk from latest builds to 'deps/binaries'
        """
        if(version_build is not None):
            self.version_build = version_build
        version, build = version_and_build(self.version_build)

        # package_name = "CBLTestServer-Android-{}-debug.apk".format(self.version_build)
        expected_binary_path = "{}/{}".format(BINARY_DIR, self.package_name)
        if os.path.isfile(expected_binary_path):
            log_info("Package is already downloaded. Skipping.")
            return

        # Package not downloaded, proceed to download from latest builds
        url = "{}/couchbase-lite-android/{}/{}/{}".format(LATEST_BUILDS, version, build, self.package_name)

        log_info("Downloading {} -> {}/{}".format(url, BINARY_DIR, self.package_name))
        resp = requests.get(url)
        resp.raise_for_status()
        with open("{}/{}".format(BINARY_DIR, self.package_name), "wb") as f:
            f.write(resp.content)

    def install(self):
        """Install the apk to running Android device or emulator"""

        # apk_name = "CBLTestServer-Android-{}-enterprise-debug.apk".format(self.version_build)

        apk_path = "{}/{}".format(BINARY_DIR, self.apk_name)

        # TODO: Remove following lines after testing next 2 lines
        # apk_name = "app-debug.apk"
        # apk_path = "/Users/sridevi.saragadam/workspace/CBL2-0/build-scripts/mobile-testkit/CBLClient/Apps/CBLTestServer-Android/app/build/outputs/apk/debug/app-debug.apk"
        log_info("Installing: {}".format(apk_path))

        # If and apk is installed, attempt to remove it and reinstall.
        # If that fails, raise an exception
        max_retries = 1
        count = 0
        while True:

            if count > max_retries:
                raise LiteServError(".apk install failed!")
            try:
                output = subprocess.check_output(["adb", "install", "-r", apk_path])
                break
            except Exception as e:
                if "INSTALL_FAILED_ALREADY_EXISTS" in e.message or "INSTALL_FAILED_UPDATE_INCOMPATIBLE" in e.message:
                    # Apk may be installed, remove and retry install
                    log_info("Trying to remove....")
                    self.remove()
                    count += 1
                    continue
                else:
                    # Install succeeded, continue
                    break

        output = subprocess.check_output(["adb", "shell", "pm", "list", "packages"])
        if "com.couchbase.TestServerApp" not in output:
            raise LiteServError("Failed to install package: {}".format(output))

        log_info("LiteServ installed to {}".format(self.host))

    def remove(self):
        """Removes the Test Server application from the running device
        """
        output = subprocess.check_output(["adb", "uninstall", "com.couchbase.TestServerApp"])
        if output.strip() != "Success":
            log_info(output)
            raise LiteServError("Error. Could not remove app.")

        output = subprocess.check_output(["adb", "shell", "pm", "list", "packages"])
        if "com.couchbase.TestServerApp" in output:
            raise LiteServError("Error uninstalling app!")

        log_info("Testserver app removed from {}".format(self.host))

    def start(self, logfile_name):
        """
        1. Starts a Test server app with adb logging to provided logfile file object.
            The adb process will be stored in the self.process property
        2. Start the Android activity with a launch dictionary
        2. The method will poll on the endpoint to make sure Test server is available.
        3. The expected version will be compared with the version reported by http://<host>:<port>
        4. Return the url of the running Test server app
        """

        # Clear adb buffer
        subprocess.check_call(["adb", "logcat", "-c"])

        # Start redirecting adb output to the logfile
        self.logfile = open(logfile_name, "w")
        self.process = subprocess.Popen(args=["adb", "logcat"], stdout=self.logfile)

        activity_name = "com.couchbase.TestServerApp/com.couchbase.CouchbaseLiteServ.MainActivity"
        output = subprocess.check_output([
            "adb", "shell", "am", "start", "-n", activity_name,
            "--es", "username", "none",
            "--es", "password", "none",
            "--ei", "listen_port", str(self.port),
        ])
        log_info(output)

        self._verify_launched()

        # return "http://{}:{}".format(self.host, self.port)

    def _verify_launched(self):
        """ Poll on expected http://<host>:<port> until it is reachable
        Assert that the response contains the expected version information
        """
        output = subprocess.check_output(["adb", "shell", "pidof", "com.couchbase.TestServerApp", "|", "wc", "-l"])
        log_info("output for running activity {}", format(output))
        if output is None:
            raise LiteServError("Err! App did not launched")

    def stop(self):
        """
        1. Flush and close the logfile capturing the LiteServ output
        2. Kill the LiteServ activity and clear the package data
        3. Kill the adb logcat process
        """

        log_info("Stopping LiteServ: http://{}:{}".format(self.host, self.port))

        output = subprocess.check_output([
            "adb", "shell", "am", "force-stop", "com.couchbase.TestServerApp"
        ])
        log_info(output)

        # Clear package data
        output = subprocess.check_output([
            "adb", "shell", "pm", "clear", "com.couchbase.TestServerApp"
        ])
        log_info(output)

        # self._verify_not_running()

        self.logfile.flush()
        self.logfile.close()
        self.process.kill()
        self.process.wait()

    def close_app(self):
        output = subprocess.check_output(["adb", "shell", "input", "keyevent ", "3"])
        log_info(output)
