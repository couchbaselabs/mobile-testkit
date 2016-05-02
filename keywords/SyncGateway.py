import tarfile
import os
import shutil
import logging
import time
import re

import requests
from requests import Session
from requests import ConnectionError

from constants import *

def version_and_build(full_version):
    version_parts = full_version.split("-")
    assert (len(version_parts) == 2)
    return version_parts[0], version_parts[1]

class SyncGateway:

    def __init__(self, version_build):

        self._version_build = version_build
        self.extracted_file_name = "couchbase-sync_gateway-{}".format(self._version_build)

        self._session = Session()

    def download_sync_gateway(self):

        # Check if package is already downloaded and return if it is preset
        if os.path.isdir("{}/{}".format(BINARY_DIR, self.extracted_file_name)):
            logging.info("Package exists: {}. Skipping download".format(self.extracted_file_name))
            return

        print("Installing {} sync_gateway".format(self._version_build))

        version, build = version_and_build(self._version_build)
        if version == "1.1.1":
            url = "{}/couchbase-sync-gateway/release/{}/{}/couchbase-sync-gateway-enterprise_{}_x86_64.tar.gz".format(
                LATEST_BUILDS,
                version,
                self._version_build,
                self._version_build)
        else:
            url = "{}/couchbase-sync-gateway/{}/{}/couchbase-sync-gateway-enterprise_{}_x86_64.tar.gz".format(
                LATEST_BUILDS,
                version,
                self._version_build,
                self._version_build)

        # Download and write package
        r = requests.get(url)
        file_name = "{}/{}.tar.gz".format(BINARY_DIR, self.extracted_file_name)

        with open(file_name, "wb") as f:
            f.write(r.content)

        # Extract package
        with tarfile.open(file_name) as tar_f:
            tar_f.extractall(path="{}/{}".format(BINARY_DIR, self.extracted_file_name))

        # Remove .tar.gz and return to root directory
        os.remove(file_name)

    def remove_sync_gateway(self):
        logging.info("Removing {}".format(self.extracted_file_name))
        shutil.rmtree("deps/binaries/{}".format(self.extracted_file_name))

    def get_sync_gateway_binary_path(self):
        sync_gateway_binary_path = "{}/{}/couchbase-sync-gateway/bin/sync_gateway".format(BINARY_DIR, self.extracted_file_name)
        logging.info("sync_gateway binary path: {}".format(sync_gateway_binary_path))
        return sync_gateway_binary_path

    def verify_sync_gateway_launched(self, host, port, admin_port):

        url = "http://{}:{}".format(host, port)
        admin_url = "http://{}:{}".format(host, admin_port)

        count = 0
        wait_time = 1
        while count < MAX_RETRIES:
            try:
                resp = self._session.get(url)
                # If request does not throw, exit retry loop
                break
            except ConnectionError as ce:
                logging.info("Sync Gateway may not be launched (Retrying): {}".format(ce))
                time.sleep(wait_time)
                count += 1
                wait_time *= 2

        if count == MAX_RETRIES:
            raise RuntimeError("Could not connect to Sync Gateway")

        # Get version from running sync_gateway and compare with expected version
        resp_json = resp.json()
        logging.info(resp_json)
        sync_gateway_version = resp_json["version"]
        resp_version_parts = re.split("[ /(;)]", sync_gateway_version)
        actual_version = "{}-{}".format(resp_version_parts[3], resp_version_parts[4])

        logging.info("Expected Version {}".format(self._version_build))
        logging.info("Actual Version {}".format(actual_version))

        assert (actual_version == self._version_build)

        logging.info("{} is running".format(sync_gateway_version))

        return url, admin_url

    def get_sync_gateway_document_count(self, db):
        docs = self.admin.get_all_docs(db)
        return docs["total_rows"]

