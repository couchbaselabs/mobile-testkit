import os
import subprocess
import re
import shutil
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


class LiteServNetMono(LiteServBase):

    def download(self):
        """
        1. Check to see if package is downloaded already. If so, return
        2. Download the LiteServ package from latest builds to 'deps/binaries'
        3. Unzip the packages and make the binary executable
        """

        # Skip download if packages is already downloaded
        expected_binary = "{}/couchbase-lite-net-mono-{}-liteserv/LiteServ.exe".format(BINARY_DIR, self.version_build)
        if os.path.isfile(expected_binary):
            log_info("Package already downloaded: {}".format(expected_binary))
            return

        version, build = version_and_build(self.version_build)
        download_url = "{}/couchbase-lite-net/{}/{}/LiteServ.zip".format(LATEST_BUILDS, version, build)

        downloaded_package_zip_name = "couchbase-lite-net-mono-{}-liteserv.zip".format(self.version_build)
        log_info("Downloading {} -> {}/{}".format(download_url, BINARY_DIR, downloaded_package_zip_name))
        resp = requests.get(download_url)
        resp.raise_for_status()
        with open("{}/{}".format(BINARY_DIR, downloaded_package_zip_name), "wb") as f:
            f.write(resp.content)

        extracted_directory_name = downloaded_package_zip_name.replace(".zip", "")
        with ZipFile("{}/{}".format(BINARY_DIR, downloaded_package_zip_name)) as zip_f:
            zip_f.extractall("{}/{}".format(BINARY_DIR, extracted_directory_name))

        # Remove .zip
        os.remove("{}/{}".format(BINARY_DIR, downloaded_package_zip_name))

        # Remove x64 and x86 HACK - To get around https://github.com/couchbase/couchbase-lite-net/issues/672
        # Need to remove once the issue is resolved
        shutil.rmtree("{}/{}/x64".format(BINARY_DIR, extracted_directory_name))
        shutil.rmtree("{}/{}/x86".format(BINARY_DIR, extracted_directory_name))

    def install(self):
        """
        Noop on mono .NET. The LiteServ is a commandline binary
        """
        log_info("No install needed for mono .NET")
        pass

    def start(self, logfile):
        """
        1. Starts a LiteServ with logging to provided logfile file object.
           The running LiteServ process will be stored in the self.process property.
        2. The method will poll on the endpoint to make sure LiteServ is available.
        3. The expected version will be compared with the version reported by http://<host>:<port>
        4. eturn the url of the running LiteServ
        """

        self._verify_not_running()

        binary_path = "{}/couchbase-lite-net-mono-{}-liteserv/LiteServ.exe".format(BINARY_DIR, self.version_build)

        process_args = [
            "mono",
            binary_path,
            "--port", str(self.port),
            "--dir", "{}/dbs/net-mono/".format(RESULTS_DIR)
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

        log_info("Launching: {} with args: {}".format(binary_path, process_args))

        self.process = subprocess.Popen(args=process_args, stdout=logfile)

        self._verify_launched()

        return "http://{}:{}".format(self.host, self.port)

    def _verify_launched(self):
        """ Poll on expected http://<host>:<port> until it is reachable
        Assert that the response contains the expected version information
        """

        resp_obj = self._wait_until_reachable()
        log_info(resp_obj)

        # .NET OS X 10.12/x86_64 1.3.1-build0013/5d1553d
        running_version = resp_obj["vendor"]["version"]

        if not running_version.startswith(".NET OS X"):
            raise LiteServError("Invalid platform running!")

        # [u'.NET', u'OS', u'X', u'10.12', u'x86_64', u'1.3.1', u'build0013', u'5d1553d']
        running_version_parts = re.split("[ /-]", running_version)

        running_version = running_version_parts[5]
        running_build = int(running_version_parts[6].strip("build"))
        running_version_composed = "{}-{}".format(running_version, running_build)

        if self.version_build != running_version_composed:
            raise LiteServError("Expected version does not match actual version: Expected={}  Actual={}".format(
                self.version_build,
                running_version_composed)
            )

    def stop(self, logfile):
        """
        1. Flush and close the logfile capturing the LiteServ output
        2. Kill the LiteServ process
        3. Verify that no service is running on http://<host>:<port>
        """

        if not isinstance(logfile, file):
            raise LiteServError("logfile must be of type 'file'")

        log_info("Stopping LiteServ ...")

        logfile.flush()
        logfile.close()
        self.process.kill()
        self.process.wait()

        self._verify_not_running()
