import base64
import json
import time
import sys

import requests

from couchbase.bucket import Bucket
from provision.ansible_runner import AnsibleRunner

from keywords.utils import log_info
from keywords.utils import log_error

class Server:

    """
    Old code -- slowly being deprecated

    Use keywords/CouchbaseServer.py for future development
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
        while count < 3:
            log_info(">>> Deleting buckets: {}".format(name))
            resp = requests.delete("{0}/pools/default/buckets/{1}".format(self.url, name), headers=self._headers)
            if resp.status_code == 200 or resp.status_code == 404:
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
        return Bucket(connection_str)
        
    def __repr__(self):
        return "Server: {}:{}\n".format(self.hostname, self.ip)


