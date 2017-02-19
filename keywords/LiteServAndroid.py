import subprocess

from keywords.LiteServBase import LiteServBase
from keywords.exceptions import LiteServError
from keywords.utils import log_info


class LiteServAndroid(LiteServBase):

    def install_apk(self, apk_path, apk_id):
        """Install the apk to running Android device or emulator"""
        log_info("Installing: {}".format(apk_path))

        # If and apk is installed, attempt to remove it and reinstall.
        # If that fails, raise an exception
        max_retries = 1
        count = 0
        while True:

            if count > max_retries:
                raise LiteServError(".apk install failed!")

            output = subprocess.check_output(["adb", "install", apk_path], stderr=subprocess.STDOUT)
            if "INSTALL_FAILED_ALREADY_EXISTS" in output or \
               "INSTALL_FAILED_UPDATE_INCOMPATIBLE" in output:
                # Apk may be installed, remove and retry install
                self.remove()
                count += 1
                continue
            else:
                # Install succeeded, continue
                break

        output = subprocess.check_output(["adb", "shell", "pm", "list", "packages"])
        if apk_id not in output:
            raise LiteServError("Failed to install package")

        log_info("LiteServ installed to {}".format(self.host))

    def remove_apk(self, apk_id):
        """Removes the LiteServ application from the running device
        """
        output = subprocess.check_output(["adb", "uninstall", apk_id])
        if output.strip() != "Success":
            log_info(output)
            raise LiteServError("Error. Could not remove app.")

        output = subprocess.check_output(["adb", "shell", "pm", "list", "packages"])
        if apk_id in output:
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
        self.launch_and_verify()

        return "http://{}:{}".format(self.host, self.port)

    def launch_and_verify(self):
        raise NotImplementedError()

    def _verify_launched(self):
        """ Poll on expected http://<host>:<port> until it is reachable
        Assert that the response contains the expected version information
        """
        resp_obj = self._wait_until_reachable()
        log_info(resp_obj)
        if resp_obj["version"] != self.version_build:
            raise LiteServError("Expected version: {} does not match running version: {}".format(
                self.version_build, resp_obj["version"]))

    def stop_activity(self, apk_id):
        """
        1. Flush and close the logfile capturing the LiteServ output
        2. Kill the LiteServ activity and clear the package data
        3. Kill the adb logcat process
        """

        log_info("Stopping LiteServ: http://{}:{}".format(self.host, self.port))

        output = subprocess.check_output([
            "adb", "shell", "am", "force-stop", apk_id
        ])
        log_info(output)

        # Clear package data
        output = subprocess.check_output([
            "adb", "shell", "pm", "clear", apk_id
        ])
        log_info(output)

        self._verify_not_running()

        self.logfile.flush()
        self.logfile.close()
        self.process.kill()
        self.process.wait()
