import os
import subprocess

import requests

from keywords.TestServerBase import TestServerBase
from keywords.constants import LATEST_BUILDS, RELEASED_BUILDS
from keywords.constants import BINARY_DIR
from keywords.exceptions import LiteServError
from keywords.utils import version_and_build
from keywords.utils import log_info


class TestServerAndroid(TestServerBase):

    def __init__(self, version_build, host, port, community_enabled=None, debug_mode=False, platform="android"):
        super(TestServerAndroid, self).__init__(version_build, host, port)
        self.platform = platform

        if self.platform == "android":
            self.download_source = "couchbase-lite-android"
            if community_enabled:
                apk_name_prefix = "CBLTestServer-Android-{}-community".format(self.version_build)
            else:
                apk_name_prefix = "CBLTestServer-Android-{}-enterprise".format(self.version_build)
            if debug_mode:
                self.apk_name = "{}-debug.apk".format(apk_name_prefix)
            else:
                self.apk_name = "{}-release.apk".format(apk_name_prefix)
            self.package_name = self.apk_name
            self.device_enabled = False
            self.installed_package_name = "com.couchbase.TestServerApp"
            self.activity_name = self.installed_package_name + "/com.couchbase.CouchbaseLiteServ.MainActivity"
        elif self.platform == "c-android":
            # Cpp-android
            self.package_name = self.apk_name = "TestServer.Android.C.apk"
            self.installed_package_name = "TestServer.Android.C"
            self.activity_name = self.installed_package_name + "/com.couchbase.CouchbaseLiteServ.MainActivity"
        else:
            # Xamarin-android
            self.package_name = self.apk_name = "TestServer.Android.apk"
            self.installed_package_name = "TestServer.Android"
            self.activity_name = self.installed_package_name + "/md53466f247b9f9d18ced632d20bd2e0d5c.MainActivity"

        self.device_option = "-e"

    def download(self, version_build=None):
        """
        1. Check to see if .apk is downloaded already. If so, return
        2. Download the Testserver .apk from latest builds to 'deps/binaries'
        """
        if(version_build is not None):
            self.version_build = version_build
        version, build = version_and_build(self.version_build)

        if version < "2.1.2":
            raise Exception("No Android app available to download for version below 2.1.2 at latestbuild. Use maven to create app.")
        expected_binary_path = "{}/{}".format(BINARY_DIR, self.package_name)
        if os.path.isfile(expected_binary_path):
            log_info("Package is already downloaded. Skipping.")
            return

        # Package not downloaded, proceed to download from latest builds
        if self.platform == "android":
            if build is None:
                url = "{}/{}/{}/{}".format(RELEASED_BUILDS, self.download_source, version, self.package_name)
            else:
                url = "{}/{}/{}/{}/{}".format(LATEST_BUILDS, self.download_source, version, build, self.package_name)
        else:
            url = "{}/couchbase-lite-net/{}/{}/{}".format(LATEST_BUILDS, version, build, self.package_name)

        log_info("Downloading {} -> {}/{}".format(url, BINARY_DIR, self.package_name))
        resp = requests.get(url, verify=False)
        resp.raise_for_status()
        with open("{}/{}".format(BINARY_DIR, self.package_name), "wb") as f:
            f.write(resp.content)

    def install(self):
        """Install the apk to running Android device or emulator"""

        apk_path = "{}/{}".format(BINARY_DIR, self.apk_name)
        self.device_enabled = False

        try:
            log_info("remove the app before install, to ensure sandbox gets cleaned.")
            self.remove()
        except Exception as e:
            log_info("remove the app before install didn't go success, but still continue ......")

        log_info("Installing: {}".format(apk_path))

        # If and apk is installed, attempt to remove it and reinstall.
        # If that fails, raise an exception
        max_retries = 1
        count = 0
        while True:
            if count > max_retries:
                raise LiteServError(".apk install failed!")
            try:
                output = subprocess.check_output(["adb", "-e", "install", "-r", apk_path])
                break
            except Exception as e:
                if "INSTALL_FAILED_ALREADY_EXISTS" in str(e) or "INSTALL_FAILED_UPDATE_INCOMPATIBLE" in str(e):

                    # Apk may be installed, remove and retry install
                    log_info("Trying to remove....")
                    self.remove()
                    count += 1
                    continue
                else:
                    # Install succeeded, continue
                    break

        output = subprocess.check_output(["adb", "-e", "shell", "pm", "list", "packages"])

        if str(self.installed_package_name) not in str(output):
            raise LiteServError("Failed to install package: {}".format(output))

        log_info("LiteServ installed to {}".format(self.host))

    def install_device(self):
        """Install the apk to running Android device or emulator"""

        self.device_enabled = True
        self.device_option = "-d"
        apk_path = "{}/{}".format(BINARY_DIR, self.apk_name)

        try:
            log_info("remove the app on device before install, to ensure sandbox gets cleaned.")
            self.remove()
        except Exception as e:
            log_info("remove the app before install didn't go success, but still continue ......")

        log_info("Installing: {}".format(apk_path))

        # If and apk is installed, attempt to remove it and reinstall.
        # If that fails, raise an exception
        max_retries = 1
        count = 0
        while True:

            if count > max_retries:
                raise LiteServError(".apk install failed!")
            try:
                output = subprocess.check_output(["adb", "-d", "install", "-r", apk_path])
                break
            except Exception as e:
                if "INSTALL_FAILED_ALREADY_EXISTS" in e.args[0] or "INSTALL_FAILED_UPDATE_INCOMPATIBLE" in e.message:
                    # Apk may be installed, remove and retry install
                    log_info("Trying to remove....")
                    self.remove()
                    count += 1
                    continue
                else:
                    # Install succeeded, continue
                    break

        output = subprocess.check_output(["adb", "-d", "shell", "pm", "list", "packages"])
        if self.installed_package_name not in output.decode():
            raise LiteServError("Failed to install package: {}".format(output))

        log_info("LiteServ installed to {}".format(self.host))

    def remove(self):
        """Removes the Test Server application from the running device
        """
        output = subprocess.check_output(["adb", "uninstall", self.installed_package_name])
        if output.strip() != "Success" and output.strip() != b"Success":
            log_info(output)
            raise LiteServError("Error. Could not remove app.")

        output = subprocess.check_output(["adb", "shell", "pm", "list", "packages"])
        if self.installed_package_name in output.decode():
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
        subprocess.check_call(["adb", "-e", "logcat", "-c"])

        # Start redirecting adb output to the logfile
        self.logfile = open(logfile_name, "w+")
        self.process = subprocess.Popen(args=["adb", "logcat"], stdout=self.logfile)

        output = subprocess.check_output([
            "adb", "-e", "shell", "am", "start", "-n", self.activity_name,
            "--es", "username", "none",
            "--es", "password", "none",
            "--ei", "listen_port", str(self.port),
        ])
        log_info(output)
        self._wait_until_reachable(port=self.port)
        self._verify_launched()

        # return "http://{}:{}".format(self.host, self.port)

    def start_device(self, logfile_name):
        """
        1. Starts a Test server app with adb logging to provided logfile file object.
            The adb process will be stored in the self.process property
        2. Start the Android activity with a launch dictionary
        2. The method will poll on the endpoint to make sure Test server is available.
        3. The expected version will be compared with the version reported by http://<host>:<port>
        4. Return the url of the running Test server app
        """

        # Clear adb buffer
        subprocess.check_call(["adb", "-d", "logcat", "-c"])

        # Start redirecting adb output to the logfile
        self.logfile = open(logfile_name, "w+")
        self.process = subprocess.Popen(args=["adb", "-d", "logcat"], stdout=self.logfile)

        output = subprocess.check_output([
            "adb", "-d", "shell", "am", "start", "-n", self.activity_name,
            "--es", "username", "none",
            "--es", "password", "none",
            "--ei", "listen_port", str(self.port),
        ])
        log_info(output)
        self._wait_until_reachable(port=self.port)
        self._verify_launched()

    def _verify_launched(self):
        """ Verify that app is launched with adb command
        """
        if self.device_enabled:
            output = subprocess.check_output(["adb", "-d", "shell", "pidof", self.installed_package_name, "|", "wc", "-l"])
        else:
            output = subprocess.check_output(["adb", "-e", "shell", "pidof", self.installed_package_name, "|", "wc", "-l"])
        log_info("output for running activity {}".format(output))
        if output is None:
            raise LiteServError("Err! App did not launched")

    def stop(self):
        """
        1. Flush and close the logfile capturing the LiteServ output
        2. Kill the LiteServ activity and clear the package data
        3. Kill the adb logcat process
        """

        log_info("Stopping LiteServ: http://{}:{}".format(self.host, self.port))
        output = subprocess.check_output(["adb", self.device_option, "shell", "am", "force-stop", self.installed_package_name])
        log_info(output)

        # Clear package data
        output = subprocess.check_output(["adb", self.device_option, "shell", "pm", "clear", self.installed_package_name])
        log_info(output)

        # self._verify_not_running()

        self.logfile.flush()
        self.logfile.close()
        self.process.kill()
        self.process.wait()

    def close_app(self):
        if self.device_enabled:
            output = subprocess.check_output(["adb", "-d", "shell", "input", "keyevent ", "3"])
        else:
            output = subprocess.check_output(["adb", "-e", "shell", "input", "keyevent ", "3"])
        log_info(output)

    def open_app(self):
        if self.device_enabled:
            output = subprocess.check_output([
                "adb", "-d", "shell", "am", "start", "-n", self.activity_name,
                "--es", "username", "none", "--es", "password", "none", "--ei",
                "listen_port",
                str(self.port)
            ])
        else:
            output = subprocess.check_output([
                "adb", "-e", "shell", "am", "start", "-n", self.activity_name,
                "--es", "username", "none", "--es", "password", "none", "--ei",
                "listen_port",
                str(self.port)
            ])
        log_info(output)
        log_info(output)
        self._wait_until_reachable(port=self.port)
        self._verify_launched()
