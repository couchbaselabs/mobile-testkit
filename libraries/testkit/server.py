import base64
import json
import time

import requests

from couchbase.bucket import Bucket
from libraries.provision.ansible_runner import AnsibleRunner

from keywords.utils import log_info
from keywords.utils import log_error
from keywords.couchbaseserver import create_internal_rbac_bucket_user
from keywords.couchbaseserver import delete_internal_rbac_bucket_user
from keywords.couchbaseserver import get_server_version


class Server:

    """
    Old code -- slowly being deprecated

    Use keywords/couchbaseserver.py for future development
    """

    def __init__(self, cluster_config, target):
        self.ansible_runner = AnsibleRunner(cluster_config)
        self.ip = target["ip"]
        self.url = "http://{}:8091".format(target["ip"])
        self.hostname = target["name"]

        auth = base64.b64encode("{0}:{1}".format("Administrator", "password").encode())
        auth = auth.decode("UTF-8")
        self._headers = {'Content-Type': 'application/json', "Authorization": "Basic {}".format(auth)}

    def delete_buckets(self):
        count = 0
        status = 0
        server_version = get_server_version(self.ip)
        server_major_version = int(server_version.split(".")[0])

        while count < 3:
            resp = requests.get("{}/pools/default/buckets".format(self.url), headers=self._headers)
            resp.raise_for_status()
            obj = json.loads(resp.text)

            existing_bucket_names = []
            for entry in obj:
                existing_bucket_names.append(entry["name"])

            log_info(">>> Existing buckets: {}".format(existing_bucket_names))
            log_info(">>> Deleting buckets: {}".format(existing_bucket_names))

            # HACK around Couchbase Server issue where issuing a bucket delete via REST occasionally returns 500 error
            delete_num = 0
            # Delete existing buckets
            for bucket_name in existing_bucket_names:
                resp = requests.delete("{0}/pools/default/buckets/{1}".format(self.url, bucket_name), headers=self._headers)
                if resp.status_code == 200:
                    delete_num += 1
                    if server_major_version >= 5:
                        delete_internal_rbac_bucket_user(self.url, bucket_name)

            if delete_num == len(existing_bucket_names):
                break
            else:
                # A 500 error may have occured, query for buckets and try to delete them again
                time.sleep(5)
                count += 1

        if count == 3:
            log_error("Could not delete bucket")
            status = 1

        return status

    def delete_bucket(self, name):
        # HACK around Couchbase Server issue where issuing a bucket delete via REST occasionally returns 500 error
        count = 0
        status = 0
        server_version = get_server_version(self.ip)
        server_major_version = int(server_version.split(".")[0])

        while count < 3:
            log_info(">>> Deleting buckets: {}".format(name))
            resp = requests.delete("{0}/pools/default/buckets/{1}".format(self.url, name), headers=self._headers)
            if resp.status_code == 200 or resp.status_code == 404:
                if server_major_version >= 5:
                    delete_internal_rbac_bucket_user(self.url, name)

                break
            else:
                # A 500 error may have occured
                count += 1
                time.sleep(5)

        if count == 3:
            log_error("Could not delete bucket")
            status = 1

        return status

    def create_buckets(self, names):
        # Create a user with username=bucketname
        server_version = get_server_version(self.ip)
        server_major_version = int(server_version.split(".")[0])

        if server_major_version >= 5:
            if type(names) is list:
                for name in names:
                    create_internal_rbac_bucket_user(self.url, name)
            else:
                create_internal_rbac_bucket_user(self.url, names)

        # Create buckets
        status = self.ansible_runner.run_ansible_playbook(
            "create-server-buckets.yml",
            extra_vars={
                "bucket_names": names
            }
        )
        return status

    def get_bucket(self, bucket_name):
        connection_str = "couchbase://{}/{}".format(self.ip, bucket_name)
        return Bucket(connection_str, password='password')

    def __repr__(self):
        return "Server: {}:{}\n".format(self.hostname, self.ip)
