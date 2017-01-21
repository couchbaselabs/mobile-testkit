import os
import subprocess
from zipfile import ZipFile
import requests
import sys
import LiteServXamarinCommon
from keywords.LiteServBase import LiteServBase
from keywords.constants import LATEST_BUILDS
from keywords.constants import BINARY_DIR
from keywords.constants import REGISTERED_CLIENT_DBS
from keywords.exceptions import LiteServError
from keywords.utils import version_and_build
from keywords.utils import log_info
from keywords.constants import MAX_RETRIES
from subprocess import CalledProcessError

class LiteServXamarinAndroid(LiteServBase):

    def download(self):
        """
        1. Check to see if .apk is downloaded already. If so, return
        2. Download the LiteServ .apk from latest builds to 'deps/binaries'
        """

        version, build = version_and_build(self.version_build)

        package_name = "LiteServ.zip"

        expected_binary_path = "{}/{}".format(BINARY_DIR, package_name)
        if os.path.isfile(expected_binary_path):
            log_info("Package is already downloaded. Skipping.")
            return

        # Package not downloaded, proceed to download from latest builds
        downloaded_package_zip_name = "{}/{}".format(BINARY_DIR, package_name)
        url = "{}/couchbase-lite-net/{}/{}/{}".format(LATEST_BUILDS, version, build, package_name)

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

    def install(self):
        """Install the apk to running Android device or emulator"""

        apk_name = "LiteServ.apk"
        folder_name = "LiteServ/Android"
        apk_path = "{}/{}/{}".format(BINARY_DIR, folder_name, apk_name)

        log_info("Installing: {}".format(apk_path))

        count = 0

        while count != MAX_RETRIES:
            try:
                output = subprocess.check_output(["adb", "install", apk_path])

                # Break the loop for successful install
                break
            except CalledProcessError as e:
                 log_info("Apk might already be installed. Will uninstall and retry install")
                 self.remove()
            except:
                raise Exception("Failed to install apk", sys.exc_info()[0])

            count += 1

        output = subprocess.check_output(["adb", "shell", "pm", "list", "packages"])

        if count == MAX_RETRIES and "com.couchbase.liteserv" in output:
            raise LiteServError("Failed to uninstall APK after {} retries.".format(MAX_RETRIES))

        output = subprocess.check_output(["adb", "shell", "pm", "list", "packages"])
        if "com.couchbase.liteserv" not in output:
            raise LiteServError("Failed to install package")

        log_info("LiteServ installed to {}".format(self.host))

    def remove(self):
        """Removes the LiteServ application from the running device
        """
        output = subprocess.check_output(["adb", "uninstall", "com.couchbase.liteserv"])
        if output.strip() != "Success":
            log_info(output)
            raise LiteServError("Error. Could not remove app.")

        output = subprocess.check_output(["adb", "shell", "pm", "list", "packages"])
        if "com.couchbase.liteserv" in output:
            raise LiteServError("Error uninstalling app!")

        log_info("LiteServ removed from {}".format(self.host))

