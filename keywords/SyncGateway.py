import requests
import tarfile
import os
import shutil
import logging

from constants import *

from testkit.admin import Admin
from testkit.syncgateway import SyncGateway


def version_and_build(full_version):
    version_parts = full_version.split("-")
    assert (len(version_parts) == 2)
    return version_parts[0], version_parts[1]


class SyncGateway:

    def __init__(self, version_build):

        self.version_build = version_build
        self.extracted_file_name = "couchbase-sync_gateway-{}".format(self.version_build)

        # self.sync_gateway = SyncGateway({"ip": "localhost", "name": "local"})
        #self.admin = Admin(self.sync_gateway)

    def download_sync_gateway(self):

        print("Installing {} sync_gateway".format(self.version_build))

        version, build = version_and_build(self.version_build)
        if version == "1.1.1":
            url = "{}/couchbase-sync-gateway/release/{}/{}/couchbase-sync-gateway-enterprise_{}_x86_64.tar.gz".format(
                LATEST_BUILDS,
                version,
                self.version_build,
                self.version_build)
        else:
            url = "{}/couchbase-sync-gateway/{}/{}/couchbase-sync-gateway-enterprise_{}_x86_64.tar.gz".format(
                LATEST_BUILDS,
                version,
                self.version_build,
                self.version_build)

        os.chdir(BINARY_DIR)

        # Download and write package
        r = requests.get(url)
        file_name = "{}.tar.gz".format(self.extracted_file_name)

        with open(file_name, "wb") as f:
            f.write(r.content)

        # Extract package
        with tarfile.open(file_name) as tar_f:
            tar_f.extractall(path=self.extracted_file_name)

        # Remove .tar.gz and return to root directory
        os.remove(file_name)
        os.chdir("../../")

    def remove_sync_gateway(self):
        logging.info("Removing {}".format(self.extracted_file_name))
        shutil.rmtree("deps/binaries/{}".format(self.extracted_file_name))

    def get_sync_gateway_binary_path(self):
        sync_gateway_binary_path = "{}/{}/couchbase-sync-gateway/bin/sync_gateway".format(BINARY_DIR, self.extracted_file_name)
        logging.info("sync_gateway binary path: {}".format(sync_gateway_binary_path))
        return sync_gateway_binary_path

    def verify_sync_gateway_launched(self):
        logging.info("verify_sync_gateway_launched")

    def get_sync_gateway_document_count(self, db):
        docs = self.admin.get_all_docs(db)
        return docs["total_rows"]

