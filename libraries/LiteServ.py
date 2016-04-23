import logging
import os
import shutil
from zipfile import ZipFile
from constants import *

from testkit.debug import log_request
from testkit.debug import log_response
import requests

def version_and_build(full_version):
    version_parts = full_version.split("-")
    assert (len(version_parts) == 2)
    return version_parts[0], version_parts[1]

class LiteServ:

    def __init__(self, platform, version_build, hostname, port):

        supported_platforms = ["macosx", "android", "net"]
        if platform not in supported_platforms:
            raise ValueError("Unsupported version of LiteServ")

        self.platform = platform
        self.version_build = version_build

        if self.platform == "macosx":
            self.extracted_file_name = "couchbase-lite-macosx-{}".format(version_build)
        elif self.platform == "android":
            # TODO
            pass
        elif self.platform == "net":
            # TODO
            pass

        self.url = "http://{}:{}".format(hostname, port)
        logging.info("Launching Listener on {}".format(self.url))

    def download_liteserv(self):

        logging.info("Downloading {} LiteServ, version: {}".format(self.platform, self.version_build))
        if self.platform == "macosx":
            version, build = version_and_build(self.version_build)
            file_name = "couchbase-lite-macosx-enterprise_{}.zip".format(self.version_build)
            url = "{}/couchbase-lite-ios/{}/macosx/{}/{}".format(LATEST_BUILDS, version, self.version_build, file_name)
        elif self.platform == "android":
            # TODO
            pass
        elif self.platform == "net":
            # TODO
            pass

        # Change to package dir
        os.chdir(BINARY_DIR)

        # Download the packages
        print("Downloading: {}".format(url))
        resp = requests.get(url)
        resp.raise_for_status()
        with open(file_name, "wb") as f:
            f.write(resp.content)

        # Unzip the package
        with ZipFile(file_name) as zip_f:
            zip_f.extractall(self.extracted_file_name)

        # Make binary executable
        os.chmod("{}/LiteServ".format(self.extracted_file_name), 0755)

        # Remove .zip file
        os.remove(file_name)

        # Change back to root dir
        os.chdir("../..")

    def get_binary_path(self):

        if self.platform == "macosx":
            binary_path = "{}/{}/LiteServ".format(BINARY_DIR, self.extracted_file_name)
        elif self.platform == "android":
            # TODO
            pass
        elif self.platform == "net":
            # TODO
            pass

        return binary_path

    def remove_liteserv(self):
        logging.info("Removing {} LiteServ, version: {}".format(self.platform, self.version_build))
        os.chdir(BINARY_DIR)
        shutil.rmtree(self.extracted_file_name)
        os.chdir("../..")

    def verify_listener_launched(self):
        resp = requests.get(self.url)
        log_request(resp)
        log_response(resp)
