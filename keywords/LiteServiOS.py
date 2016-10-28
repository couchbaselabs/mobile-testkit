import json
import subprocess

from keywords.LiteServBase import LiteServBase
from keywords.constants import BINARY_DIR
from keywords.exceptions import LiteServError
from keywords.utils import version_and_build
from keywords.utils import log_info
from keywords.utils import log_r


class LiteServiOS(LiteServBase):

    def __init__(self, version_build, host, port, storage_engine):

        # Initialize baseclass properies
        super(LiteServiOS, self).__init__(version_build, host, port, storage_engine)

    def download(self):
        """
        1. Check to see if package is downloaded already. If so, return
        2. Download the LiteServ package from latest builds to 'deps/binaries'
        3. Unzip the packages and make the binary executable
        """
        raise NotImplementedError("iOS not a part of build yet")

    def install(self):
        """Installs / launches LiteServ on iOS device
        Warning: Only works with a single device at the moment
        """

        if self.storage_engine != "SQLite":
            raise LiteServError("https://github.com/couchbaselabs/liteserv-ios/issues/1")

        package_name = "couchbase-lite-ios-liteserv-{}.app".format(self.version_build)
        app_path = "{}/{}".format(BINARY_DIR, package_name)
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

    def remove(self):
        """
        Remove the iOS app from the connected device
        """
        log_info("Removing LiteServ-iOS")

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

    def start(self, logfile_name):
        """
        1. Starts a LiteServ with logging to provided logfile file object.
           The running LiteServ process will be stored in the self.process property.
        2. The method will poll on the endpoint to make sure LiteServ is available.
        3. The expected version will be compared with the version reported by http://<host>:<port>
        4. Return the url of the running LiteServ
        """

        if self.storage_engine != "SQLite":
            raise NotImplementedError("Need to make sure to support other storage types")

        self._verify_not_running()

        if self.port == 59850:
            raise LiteServError("On iOS, port 59850 is reserved for the admin port")

        liteserv_admin_url = "http://{}:59850".format(self.host)
        log_info("Starting LiteServ: {}".format(liteserv_admin_url))

        data = {
            "port": int(self.port)
        }

        resp = self.session.put("{}/start".format(liteserv_admin_url), data=json.dumps(data))
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

        liteserv_admin_url = "http://{}:59850".format(self.host)
        log_info("Stopping LiteServ: {}".format(liteserv_admin_url))
        resp = self.session.put("{}/stop".format(liteserv_admin_url))
        log_r(resp)
        resp.raise_for_status()

        self._verify_not_running()
