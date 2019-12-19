import subprocess
import os
import re
import time
from zipfile import ZipFile
from shutil import copyfile
import requests

from keywords.TestServerBase import TestServerBase
from keywords.constants import BINARY_DIR
from keywords.constants import RELEASED_BUILDS
from keywords.constants import LATEST_BUILDS
from keywords.exceptions import LiteServError
from keywords.utils import version_and_build
from keywords.utils import log_info
from keywords.constants import CLIENT_REQUEST_TIMEOUT
from requests.exceptions import ConnectionError


class TestServeriOS(TestServerBase):

    def __init__(self, version_build, host, port, community_enabled=None, debug_mode=False, platform="ios"):
        super(TestServeriOS, self).__init__(version_build, host, port)
        self.liteserv_admin_url = "http://{}:59850".format(self.host)
        self.logfile_name = None
        self.device_id = None
        self.device = "iPhone-8-Plus"
        self.debug_mode = False
        self.app_path = ""
        self.app_name = ""
        self.platform = platform
        self.bundle_id = ""
        self.released_version = {
            "2.0.0": 806,
            "2.1.0": 263,
            "2.1.1": 10,
            "2.1.2": 11,
            "2.5.0": 272,
            "2.5.2": 3
        }

        if self.version_build == "2.1.0":
            raise Exception("No iOS app available to download for 2.1.0 at latestbuild. Use xcode to create app.")
        if debug_mode:
            self.debug_mode = True

        if self.platform == "ios":
            if community_enabled:
                self.app_dir = "CBLTestServer-iOS-community-{}".format(version_build)
                self.package_name = "CBLTestServer-iOS-community-{}.zip".format(version_build)
                self.app = "CBLTestServer-iOS"
            else:
                if version_build == "2.1.1":
                    self.package_name = "CBLTestServer-iOS-enterprise-{}-{}.zip".format(version_build, self.released_version[version_build])
                    self.app_dir = "CBLTestServer-iOS-enterprise-{}-{}".format(version_build, self.released_version[version_build])
                else:
                    self.package_name = "CBLTestServer-iOS-enterprise-{}.zip".format(version_build)
                    self.app_dir = "CBLTestServer-iOS-enterprise-{}".format(version_build)
                self.app = "CBLTestServer-iOS-EE"

            self.bundle_id = "com.couchbase.CBLTestServer-iOS"
        else:
            # Xamarin-ios
            self.app_dir = "TestServer.iOS"
            self.package_name = "TestServer.iOS.zip"
            self.app = "TestServer.iOS"
            self.bundle_id = "com.couchbase.TestServer.iOS"

    def download(self, version_build=None):
        """
        1. Check to see if package is downloaded already. If so, return
        2. Download the LiteServ package from latest builds to 'deps/binaries'
        3. Unzip the packages and make the binary executable
        """
        if version_build is not None:
            self.version_build = version_build
        self.version, self.build = version_and_build(self.version_build)
        if self.platform == "ios":
            if self.build is None:
                app_name = "{}-{}-{}.app".format(self.app, self.version,
                                                 self.released_version[self.version])
                self.version_build = self.released_version[self.version]
            else:
                app_name = "{}-{}.app".format(self.app, self.version_build)
        else:
            app_name = self.app

        expected_binary_path = "{}/{}/{}".format(BINARY_DIR, self.app_dir, app_name)
        if os.path.exists(expected_binary_path):
            log_info("Package is already downloaded. Skipping.")
            return

        # Package not downloaded, proceed to download from latest builds
        downloaded_package_zip_name = "{}/{}".format(BINARY_DIR, self.package_name)
        if self.platform == "ios":
            if self.build is None:
                if self.version < "2.0.2":
                    url = "{}/couchbase-lite/ios/{}/{}".format(RELEASED_BUILDS, self.version, self.package_name)
                else:
                    url = "{}/couchbase-lite-ios/{}/{}".format(RELEASED_BUILDS, self.version, self.package_name)
            else:
                url = "{}/couchbase-lite-ios/{}/{}/{}".format(LATEST_BUILDS, self.version, self.build, self.package_name)
        else:
            if self.build is None:
                url = "{}/couchbase-lite-net/{}/{}".format(RELEASED_BUILDS, self.version, self.package_name)
            else:
                url = "{}/couchbase-lite-net/{}/{}/{}".format(LATEST_BUILDS, self.version, self.build, self.package_name)

        log_info("Downloading {} -> {}/{}".format(url, BINARY_DIR, self.package_name))
        resp = requests.get(url, verify=False)
        resp.raise_for_status()
        with open("{}/{}".format(BINARY_DIR, self.package_name), "wb") as f:
            f.write(resp.content)
        extracted_directory_name = downloaded_package_zip_name.replace(".zip", "")
        with ZipFile("{}".format(downloaded_package_zip_name)) as zip_f:
            zip_f.extractall("{}".format(extracted_directory_name))

        # Remove .zip
        os.remove("{}".format(downloaded_package_zip_name))

    def install_device(self):
        """Installs / launches CBLTestServer on iOS device
        Warning: Only works with a single device at the moment
        """
        if self.platform == "ios":
            if self.debug_mode:
                self.app_name = "{}-{}-Device-debug.app".format(self.app, self.version_build)
            else:
                self.app_name = "{}-{}-Device.app".format(self.app, self.version_build)
        else:
            self.app_name = "{}-Device.app".format(self.app)

        self.app_path = "{}/{}/{}".format(BINARY_DIR, self.app_dir, self.app_name)
        log_info("Installing: {}".format(self.app_path))

        # install app / launch app to connected device
        output = subprocess.check_output([
            "ios-deploy", "--justlaunch", "--bundle", self.app_path
        ])
        log_info(output)

        output = subprocess.check_output(["ios-deploy", "--list_bundle_id"])
        log_info(output)

        if self.bundle_id not in output.decode():
            raise LiteServError("Could not install CBLTestServer-iOS")

        self.stop()

    def install(self):
        """Installs / launches CBLTestServer on iOS simulator
        """
        if self.platform == "ios":
            if self.debug_mode:
                if self.build is None:
                    self.app_name = "{}-{}-{}-debug.app".format(self.app,
                                                                self.version,
                                                                self.version_build)
                else:
                    self.app_name = "{}-{}-debug.app".format(self.app,
                                                             self.version_build)
            else:
                if self.build is None:
                    self.app_name = "{}-{}-{}.app".format(self.app,
                                                          self.version,
                                                          self.version_build)
                else:
                    self.app_name = "{}-{}.app".format(self.app,
                                                       self.version_build)
        else:
            self.app_name = "{}.app".format(self.app)

        self.app_path = "{}/{}/{}".format(BINARY_DIR, self.app_dir, self.app_name)

        log_info("Installing: {}".format(self.app_path))
        # Launch the simulator and install the app
        output = subprocess.check_output([
            "ios-sim", "--devicetypeid", self.device, "install", self.app_path, "--exit"
        ])

        log_info(output)
        list_output = subprocess.Popen(["xcrun", "simctl", "list"], stdout=subprocess.PIPE)
        output = subprocess.check_output(('grep', 'Booted'), stdin=list_output.stdout)
        if len(output.decode().splitlines()) > 0:
            # Wait for the device to boot up
            # We check the status of the simulator using the command
            # xcrun simctl spawn booted launchctl print system | grep com.apple.springboard.services
            # If the simulator is still coming up, the output will say
            # 0x1d407    M   D   com.apple.springboard.services
            # If the simulator has booted up completely, it will say
            # 0x1e007    M   A   com.apple.springboard.services
            # We check if the third field is A
            start = time.time()
            while True:
                if time.time() - start > CLIENT_REQUEST_TIMEOUT:
                    raise LiteServError("iPhone Simulator failed to start")

                output = subprocess.Popen([
                    "xcrun", "simctl", "spawn", "booted", "launchctl", "print", "system"
                ], stdout=subprocess.PIPE)
                output = subprocess.check_output(('grep', 'com.apple.springboard.services'), stdin=output.stdout)
                output = re.sub(' +', ' ', output.decode()).strip()
                status = output.split(" ")[2]
                if status == "A":
                    log_info("iPhone Simulator seems to have booted up")
                    break
                else:
                    log_info("Waiting for the iPhone Simulator to boot up")
                    time.sleep(1)
                    continue

        # Get the device ID
        list_output = subprocess.Popen(["xcrun", "simctl", "list"], stdout=subprocess.PIPE)
        output = subprocess.check_output(('grep', 'Booted'), stdin=list_output.stdout)
        for line in output.splitlines():
            if "Phone" in line.decode():
                self.device_id = re.sub(' +', ' ', line.decode()).strip()
                self.device_id = self.device_id.split(" ")[3]
                self.device_id = self.device_id.strip('(')
                self.device_id = self.device_id.strip(')')

        if not self.device_id:
            raise LiteServError("Could not get the device ID of the running simulator")

    def remove_device(self):
        """
        Remove the iOS app from the connected device
        """
        output = subprocess.check_output([
            "ios-deploy", "--uninstall_only", "--bundle_id", self.bundle_id
        ])
        log_info(output)

        # Check that removal is successful
        output = subprocess.check_output(["ios-deploy", "--list_bundle_id"])
        log_info(output)

        if self.bundle_id in output.decode():
            raise LiteServError("CBLTestServer-iOS is still present after uninstall")

    def remove(self):
        """
        Remove the iOS app from the simulator
        """
        log_info("Removing CBLTestServer")

        self.stop()

        # Stop the simulator
        log_info("device_id: {}".format(self.device_id))
        output = subprocess.check_output([
            "killall", "Simulator"
        ])

        # Erase the simulator
        output = subprocess.check_output([
            "xcrun", "simctl", "erase", self.device_id
        ])

        if self.bundle_id in output.decode():
            raise LiteServError("{} is still present after uninstall".format(self.bundle_id))

    def start(self, logfile_name):
        """
        1. Starts a LiteServ with logging to provided logfile file object.
           The running LiteServ process will be stored in the self.process property.
        2. The method will poll on the endpoint to make sure LiteServ is available.
        3. The expected version will be compared with the version reported by http://<host>:<port>
        4. Return the url of the running LiteServ
        """

        self.logfile_name = logfile_name
        self.app_path = "{}/{}/{}".format(BINARY_DIR, self.app_dir, self.app_name)
        # Without --exit, ios-sim blocks
        # With --exit, --log has no effect
        # subprocess.Popen didn't launch the app
        output = subprocess.check_output([
            "ios-sim", "--devicetypeid", self.device, "launch", self.app_path, "--exit"
        ])

        log_info(output)
        self._wait_until_reachable(port=self.port)
        self._verify_running()

    def start_device(self, logfile_name):
        """
        1. Starts a LiteServ with logging to provided logfile file object.
           The running LiteServ process will be stored in the self.process property.
        2. The method will poll on the endpoint to make sure LiteServ is available.
        3. The expected version will be compared with the version reported by http://<host>:<port>
        4. Return the url of the running LiteServ
        """

        self.logfile_name = logfile_name
        self.app_path = "{}/{}/{}".format(BINARY_DIR, self.app_dir, self.app_name)

        output = subprocess.check_output([
            "ios-deploy", "--justlaunch", "--bundle", self.app_path
        ])
        log_info(output)

        self._wait_until_reachable(port=self.port)
        self._verify_running()

    def _verify_launched(self):
        """ Poll on expected http://<host>:<port> until it is reachable
        Assert that the response contains the expected version information
        """

        resp_obj = self._wait_until_reachable()
        log_info(resp_obj)

        if resp_obj["vendor"]["name"] != "Couchbase Lite (Objective-C)":
            raise LiteServError("Unexpected LiteServ platform running!")

        version, build = version_and_build(self.version_build)
        expected_version = "{} (build {})".format(version, build)
        running_version = resp_obj["vendor"]["version"]

        if expected_version != running_version:
            raise LiteServError("Expected version: {} does not match running version: {}".format(expected_version, running_version))

    def stop(self):
        """
        1. Flush and close the logfile capturing the LiteServ output
        """
        self.close_app()
        # Have to separately copy the simulator logs
        if self.logfile_name and self.device_id:
            home = os.environ['HOME']
            ios_log_file = "{}/Library/Logs/CoreSimulator/{}/system.log".format(home, self.device_id)
            copyfile(ios_log_file, self.logfile_name)
            # Empty the simulator logs so that the next test run
            # will only have logs for that run
            open(ios_log_file, 'w').close()

    def _verify_running(self):
        """
        Return true if it is running or else false
        Verifys that the endpoint return 200 from a running service
        """
        try:
            self.session.get("http://{}:{}/".format(self.host, self.port))
        except ConnectionError:
            # Expecting connection error if LiteServ is not running on the port
            raise LiteServError("Did not connected to Test server app")

        return True

    def close_app(self):
        cur_dir = os.getcwd()
        subprocess.check_output(["osascript", "{}/utilities/sim_close_app.scpt".format(cur_dir)])

    def open_app(self):
        if self.host == "localhost":
            # xcrun simctl launch booted com.couchbase.CBLTestServer-iOS
            output = subprocess.check_output(["xcrun", "simctl", "launch", "booted", self.bundle_id])
        else:
            output = subprocess.check_output(["ios-deploy", "--justlaunch", "--bundle", self.app_path])
        log_info("output of open app is {}".format(output.decode()))
        time.sleep(5)
