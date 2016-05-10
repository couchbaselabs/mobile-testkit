import os
import shutil
import subprocess
import logging
import requests
import tarfile

from subprocess import CalledProcessError
from zipfile import ZipFile

from constants import *
from utils import version_and_build

class CouchbaseServer:
    """ Downloads / Installs Couchbase Server on local Mac OSX machine"""

    def __init__(self, version_build):

        self._version_build = version_build
        self.extracted_file_name = "couchbase-server-{}".format(self._version_build)

    def download_couchbase_server(self):
        # Check if package is already downloaded and return if it is preset
        # if os.path.isdir("{}/{}".format(BINARY_DIR, self.extracted_file_name)):
        #     logging.info("Package exists: {}. Skipping download".format(self.extracted_file_name))
        #     return

        print("Installing Couchbase Server: {}".format(self._version_build))

        version, build = version_and_build(self._version_build)

        # Get dev server package from latestbuilds
        if self._version_build.startswith("4.1"):
            # http://cbnas01.sc.couchbase.com/builds/latestbuilds/couchbase-server/sherlock/5914/couchbase-server-enterprise_4.1.1-5914-macos_x86_64.zip
            base_url = "http://cbnas01.sc.couchbase.com/builds/latestbuilds/couchbase-server/sherlock/{}".format(build)
            package_name = "couchbase-server-enterprise_{}-{}-macos_x86_64.zip".format(version, build)
        elif self._version_build.startswith("4.5"):
            base_url = "http://cbnas01.sc.couchbase.com/builds/latestbuilds/couchbase-server/watson/{}".format(build)
            package_name = "couchbase-server-enterprise_{}-{}-macos_x86_64.zip".format(version, build)
        else:
            raise ValueError("Unable to resolve dev build for version: {}".format(self._version_build))

        url = "{}/{}".format(base_url, package_name)

        # Download and write package
        r = requests.get(url)
        r.raise_for_status()

        file_name = "{}/{}.zip".format(BINARY_DIR, self.extracted_file_name)

        with open(file_name, "wb") as f:
            f.write(r.content)

        # Unzip the package
        with ZipFile("{}".format(file_name)) as zip_f:
            zip_f.extractall("{}/{}".format(BINARY_DIR, self.extracted_file_name))

        os.chmod("{}/{}/Couchbase Server.app/Contents/MacOS/Couchbase Server".format(BINARY_DIR, self.extracted_file_name), 0755)

        # Remove .tar.gz
        os.remove(file_name)

        subprocess.check_call("mv {}/{}/Couchbase\ Server.app /Applications/".format(BINARY_DIR, self.extracted_file_name), shell=True)

        # Launch Server
        subprocess.check_call("xattr -dr com.apple.quarantine /Applications/Couchbase\ Server.app", shell=True)
        launch_server_output = subprocess.check_output("open /Applications/Couchbase\ Server.app", shell=True)
        print(launch_server_output)

    def _remove_existing_couchbase_server(self):

        # Kill Archive
        try:
            output = subprocess.check_output("ps aux | grep Archive | awk '{print $2}' | xargs kill -9", shell=True)
            logging.info(output)
        except CalledProcessError as e:
            logging.info("No Archive process running: {}".format(e))

        # Kill Couchbase server
        try:
            subprocess.check_output("ps aux | grep '/Applications/Couchbase Server.app/Contents/MacOS/Couchbase Server' | awk '{print $2}' | xargs kill -9",
                                    shell=True)
            logging.info(output)
        except CalledProcessError as e:
            logging.info("No Couchbase Server process running: {}".format(e))

        if os.path.isdir("/Applications/Couchbase Server.app/"):
            shutil.rmtree("/Applications/Couchbase Server.app/")

        if os.path.isdir("~/Library/Application Support/Couchbase"):
            shutil.rmtree("~/Library/Application Support/Couchbase")

        if os.path.isdir("~/Library/Application Support/Membase"):
            shutil.rmtree("~/Library/Application Support/Membase")

    def install_couchbase_server(self):

        # Remove Couchbase Server Install
        self._remove_existing_couchbase_server()



        subprocess.check_call("mv {}/{}/Couchbase\ Server.app /Applications/".format(BINARY_DIR, self.extracted_file_name), shell=True)


        # Launch Server
        subprocess.check_call("xattr -dr com.apple.quarantine /Applications/Couchbase\ Server.app", shell=True)
        launch_server_output = subprocess.check_output("open /Applications/Couchbase\ Server.app", shell=True)
        print(launch_server_output)

