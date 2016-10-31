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


class LiteServMacOSX(LiteServBase):

    def download(self):
        """
        1. Check to see if package is downloaded already. If so, return
        2. Download the LiteServ package from latest builds to 'deps/binaries'
        3. Unzip the packages and make the binary executable
        """

        package_name = "couchbase-lite-macosx-enterprise_{}.zip".format(self.version_build)

        # Skip download if packages is already downloaded
        expected_binary = "{}/couchbase-lite-macosx-enterprise_{}/LiteServ".format(BINARY_DIR, self.version_build)
        if os.path.isfile(expected_binary):
            log_info("Package already downloaded: {}".format(expected_binary))
            return

        version, build = version_and_build(self.version_build)

        if version == "1.2.0":
            package_url = "{}/couchbase-lite-ios/release/{}/macosx/{}/{}".format(LATEST_BUILDS, version, self.version_build, package_name)
        else:
            package_url = "{}/couchbase-lite-ios/{}/macosx/{}/{}".format(LATEST_BUILDS, version, self.version_build, package_name)

        # Download package to deps/binaries
        log_info("Downloading: {}".format(package_url))
        resp = requests.get(package_url)
        resp.raise_for_status()
        with open("{}/{}".format(BINARY_DIR, package_name), "wb") as f:
            f.write(resp.content)

        # Unzip package
        directory_name = package_name.replace(".zip", "")
        with ZipFile("{}/{}".format(BINARY_DIR, package_name)) as zip_f:
            zip_f.extractall("{}/{}".format(BINARY_DIR, directory_name))

        # Remove .zip
        os.remove("{}/{}".format(BINARY_DIR, package_name))

        # Make binary executable
        binary_path = "{}/{}/LiteServ".format(BINARY_DIR, directory_name)
        os.chmod(binary_path, 0755)
        log_info("LiteServ: {}".format(binary_path))

    def install(self):
        """
        Noop on Mac OSX. The LiteServ is a commandline binary
        """
        log_info("No install needed for macosx")
        pass

    def remove(self):
        """
        Noop on Mac OSX. The LiteServ is a commandline binary
        """
        log_info("No remove needed for macosx")
        pass

    def start(self, logfile_name):
        """
        1. Starts a LiteServ with logging to provided logfile file object.
           The running LiteServ process will be stored in the self.process property.
        2. The method will poll on the endpoint to make sure LiteServ is available.
        3. The expected version will be compared with the version reported by http://<host>:<port>
        4. Return the url of the running LiteServ
        """

        self._verify_not_running()

        binary_path = "{}/couchbase-lite-macosx-enterprise_{}/LiteServ".format(BINARY_DIR, self.version_build)
        log_info("Launching: {}".format(binary_path))

        process_args = [
            binary_path,
            "-Log", "YES",
            "-LogSync", "YES",
            "-LogSyncVerbose", "YES",
            "-LogRouter", "YES",
            "-LogRemoteRequest", "YES",
            "--port", str(self.port),
            "--dir", "{}/dbs/macosx/".format(RESULTS_DIR)
        ]

        if self.storage_engine == "ForestDB" or self.storage_engine == "ForestDB+Encryption":
            process_args.append("--storage")
            process_args.append("ForestDB")
        else:
            process_args.append("--storage")
            process_args.append("SQLite")

        if self.storage_engine == "SQLCipher" or self.storage_engine == "ForestDB+Encryption":
            log_info("Using Encryption ...")

            db_flags = []
            for db_name in REGISTERED_CLIENT_DBS:
                db_flags.append("--dbpassword")
                db_flags.append("{}=pass".format(db_name))
            process_args.extend(db_flags)

        log_info("Launching {} with args: {}".format(binary_path, process_args))

        # Launch LiteServ
        self.logfile = open(logfile_name, "w")
        self.process = subprocess.Popen(args=process_args, stderr=self.logfile)

        # Verify Expected version is running
        self._verify_launched()

        url = "http://{}:{}".format(self.host, self.port)
        log_info("LiteServ running on: {}".format(url))
        return url

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

        log_info("Killing LiteServ: http://{}:{}".format(self.host, self.port))

        self.logfile.flush()
        self.logfile.close()
        self.process.kill()
        self.process.wait()

        self._verify_not_running()
