import json
import subprocess
import os
import time
from zipfile import ZipFile
import requests
from requests.exceptions import ConnectionError

from keywords.LiteServBase import LiteServBase
from keywords.constants import BINARY_DIR
from keywords.constants import LATEST_BUILDS
from keywords.exceptions import LiteServError
from keywords.utils import version_and_build
from keywords.utils import log_info
from keywords.utils import log_r
from keywords.constants import REGISTERED_CLIENT_DBS
from keywords.constants import CLIENT_REQUEST_TIMEOUT


class LiteServiOS(LiteServBase):

    def __init__(self, version_build, host, port, storage_engine):

        if storage_engine == "ForestDB" or "ForestDB+Encryption":
            raise LiteServError("ForestDB not supported with the current LiteServ iOS app")

        super(LiteServiOS, self).__init__(version_build, host, port, storage_engine)
        self.liteserv_admin_url = "http://{}:59850".format(self.host)
        self.logfile_name = None
        self.device_id = None

    def download(self):
        """
        1. Check to see if package is downloaded already. If so, return
        2. Download the LiteServ package from latest builds to 'deps/binaries'
        3. Unzip the packages and make the binary executable
        """
        version, build = version_and_build(self.version_build)

        package_name = "LiteServ-iOS.zip"
        app_name = "LiteServ-iOS.app"
        app_dir = "LiteServ-iOS"

        if self.storage_engine == "SQLCipher":
            package_name = "LiteServ-iOS-SQLCipher.zip"
            app_name = "LiteServ-iOS-SQLCipher.app"
            app_dir = "LiteServ-iOS-SQLCipher"

        expected_binary_path = "{}/{}/{}".format(BINARY_DIR, app_dir, app_name)
        if os.path.isfile(expected_binary_path):
            log_info("Package is already downloaded. Skipping.")
            return

        # Package not downloaded, proceed to download from latest builds
        downloaded_package_zip_name = "{}/{}".format(BINARY_DIR, package_name)
        url = "{}/couchbase-lite-ios/{}/ios/{}/{}".format(LATEST_BUILDS, version, self.version_build, package_name)

        log_info("Downloading {} -> {}/{}".format(url, BINARY_DIR, package_name))
        resp = requests.get(url)
        resp.raise_for_status()
        with open("{}/{}".format(BINARY_DIR, package_name), "wb") as f:
            f.write(resp.content)

        extracted_directory_name = downloaded_package_zip_name.replace(".zip", "")
        with ZipFile("{}".format(downloaded_package_zip_name)) as zip_f:
            zip_f.extractall("{}".format(extracted_directory_name))

        # Remove .zip
        os.remove("{}".format(downloaded_package_zip_name))

    def install_device(self):
        """Installs / launches LiteServ on iOS device
        Warning: Only works with a single device at the moment
        """

        if self.storage_engine != "SQLite":
            raise LiteServError("https://github.com/couchbaselabs/liteserv-ios/issues/1")

        package_name = "LiteServ-iOS.app"
        app_path = "{}/{}/{}".format(BINARY_DIR, "LiteServ-iOS", package_name)
        log_info("Installing: {}".format(app_path))

        # install app / launch app to connected device
        output = subprocess.check_output([
            "ios-deploy", "--justlaunch", "--bundle", app_path
        ])
        log_info(output)

        bundle_id = "com.couchbase.LiteServ-iOS"
        output = subprocess.check_output(["ios-deploy", "--list_bundle_id"])
        log_info(output)

        if bundle_id not in output:
            raise LiteServError("Could not install LiteServ-iOS")

        self.stop()

    def install(self):
        """Installs / launches LiteServ on iOS simulator
        Default is iPhone 7 Plus
        """
        device = "iPhone-7-Plus"
        package_name = "LiteServ-iOS.app"
        app_dir = "LiteServ-iOS"

        if self.storage_engine == "SQLCipher":
            package_name = "LiteServ-iOS-SQLCipher.app"
            app_dir = "LiteServ-iOS-SQLCipher"

        app_path = "{}/{}/{}".format(BINARY_DIR, app_dir, package_name)
        output = subprocess.check_output([
            "ios-sim", "--devicetypeid", device, "start"
        ])

        log_info("Installing: {}".format(app_path))
        # Launch the simulator and install the app
        output = subprocess.check_output([
            "ios-sim", "--devicetypeid", device, "install", app_path, "--exit"
        ])

        log_info(output)

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
            output = re.sub(' +', ' ', output).strip()
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
            if "Phone" in line:
                self.device_id = re.sub(' +', ' ', line).strip()
                self.device_id = self.device_id.split(" ")[4]
                self.device_id = self.device_id.strip('(')
                self.device_id = self.device_id.strip(')')

        if not self.device_id:
            raise LiteServError("Could not get the device ID of the running simulator")

    def remove_device(self):
        """
        Remove the iOS app from the connected device
        """
        bundle_id = "com.couchbase.LiteServ-iOS"

        output = subprocess.check_output([
            "ios-deploy", "--uninstall_only", "--bundle_id", bundle_id
        ])
        log_info(output)

        # Check that removal is successful
        output = subprocess.check_output(["ios-deploy", "--list_bundle_id"])
        log_info(output)

        if bundle_id in output:
            raise LiteServError("LiteServ-iOS is still present after uninstall")

    def remove(self):
        """
        Remove the iOS app from the simulator
        """
        bundle_id = "com.couchbase.LiteServ-iOS"
        if self.storage_engine == "SQLCipher":
            bundle_id = "com.couchbase.LiteServ-iOS-SQLCipher"

        log_info("Removing LiteServ")

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

        if bundle_id in output:
            raise LiteServError("{} is still present after uninstall".format(bundle_id))

    def start(self, logfile_name):
        """
        1. Starts a LiteServ with logging to provided logfile file object.
           The running LiteServ process will be stored in the self.process property.
        2. The method will poll on the endpoint to make sure LiteServ is available.
        3. The expected version will be compared with the version reported by http://<host>:<port>
        4. Return the url of the running LiteServ
        """

        data = {}
        encryption_enabled = False
        device = "iPhone-7-Plus"
        self.logfile_name = logfile_name

        package_name = "LiteServ-iOS.app"
        app_dir = "LiteServ-iOS"

        if self.storage_engine == "SQLCipher":
            package_name = "LiteServ-iOS-SQLCipher.app"
            app_dir = "LiteServ-iOS-SQLCipher"

        app_path = "{}/{}/{}".format(BINARY_DIR, app_dir, package_name)

        # Without --exit, ios-sim blocks
        # With --exit, --log has no effect
        # subprocess.Popen didn't launch the app
        output = subprocess.check_output([
            "ios-sim", "--devicetypeid", device, "launch", app_path, "--exit"
        ])
        log_info(output)

        if self.storage_engine == "SQLite" or self.storage_engine == "SQLCipher":
            data["storage"] = "SQLite"
        elif self.storage_engine == "ForestDB" or self.storage_engine == "ForestDB+Encryption":
            data["storage"] = "ForestDB"

        if self.storage_engine == "ForestDB+Encryption" or self.storage_engine == "SQLCipher":
            encryption_enabled = True

        self._verify_not_running()

        if self.port == 59850:
            raise LiteServError("On iOS, port 59850 is reserved for the admin port")

        data["port"] = int(self.port)

        if encryption_enabled:
            log_info("Encryption enabled ...")

            db_flags = []
            for db_name in REGISTERED_CLIENT_DBS:
                db_flags.append("{}:pass".format(db_name))
            db_flags = ",".join(db_flags)

            log_info("Running with db_flags: {}".format(db_flags))
            data["dbpasswords"] = db_flags

        self._wait_until_reachable(port=59850)
        log_info("Starting LiteServ: {}".format(self.liteserv_admin_url))
        resp = self.session.put("{}/start".format(self.liteserv_admin_url), data=json.dumps(data))
        log_r(resp)
        resp.raise_for_status()
        self._verify_launched()

        return "http://{}:{}".format(self.host, self.port)

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
        2. Kill the LiteServ process
        3. Verify that no service is running on http://<host>:<port>
        """

        log_info("Stopping LiteServ: http://{}:{}".format(self.host, self.port))
        log_info("Stopping LiteServ: {}".format(self.liteserv_admin_url))

        resp = self.session.put("{}/stop".format(self.liteserv_admin_url))
        log_r(resp)
        resp.raise_for_status()

        # Using --exit in ios-sim means, --log has no effect
        # Have to separately copy the simulator logs
        if self.logfile_name and self.device_id:
            home = os.environ['HOME']
            ios_log_file = "{}/Library/Logs/CoreSimulator/{}/system.log".format(home, self.device_id)
            copyfile(ios_log_file, self.logfile_name)
            # Empty the simulator logs so that the next test run
            # will only have logs for that run
            open(ios_log_file, 'w').close()

        self._verify_not_running()
