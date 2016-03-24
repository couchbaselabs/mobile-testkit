import requests
import tarfile
import os
import shutil

from testkit.admin import Admin
from testkit.syncgateway import SyncGateway


class SyncGatewayUtils:

    def __init__(self):
        self.file_name = "couchbase-sync-gateway-enterprise_1.2.0-83_x86_64.tar.gz"
        self.sync_gateway = SyncGateway({"ip": "localhost", "name": "local"})
        self.admin = Admin(self.sync_gateway)

    def install_local_sync_gateway(self, version):
        print("Installing {} sync_gateway".format(version))

        url = "http://latestbuilds.hq.couchbase.com/couchbase-sync-gateway/1.2.0/1.2.0-83/couchbase-sync-gateway-enterprise_1.2.0-83_x86_64.tar.gz"

        print os.getcwd()

        os.chdir("resources/artifacts/sync_gateway")

        r = requests.get(url)

        with open(self.file_name, "wb") as f:
            f.write(r.content)

        with tarfile.open(self.file_name) as tar_f:
            tar_f.extractall()

        os.chdir("../../../")

        print os.getcwd()

    def uninstall_local_sync_gateway(self, platform):

        os.chdir("resources/artifacts/sync_gateway")

        os.remove(self.file_name)
        shutil.rmtree("couchbase-sync-gateway")

        os.chdir("../../../")

    def get_sync_gateway_document_count(self, db):
        docs = self.admin.get_all_docs(db)
        return docs["total_rows"]

