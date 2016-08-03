import json
import time
import logging

import requests

from keywords.MobileRestClient import get_auth_type
from keywords.constants import AuthType
from keywords.utils import log_r
from keywords.utils import log_info

class ChangesTracker:

    def __init__(self, url, db, auth):
        self.processed_changes = {}
        self.endpoint = "{}/{}".format(url, db)
        self.auth = auth

        self.cancel = False

    def process_changes(self, results):
        """
        Add each doc from longpoll changes results to the processed changes list in the following format:
        { "doc_id": [ {"rev": "rev1"}, {"rev", "rev2"}, ...] }
        """
        for doc in results:
            if len(doc["changes"]) > 0:
                if doc["id"] in self.processed_changes:
                    # doc has already been seen in the changes feed,
                    # append new changes to revs accociated with that id
                    revs_list = self.processed_changes[doc["id"]]
                    revs_list = revs_list.extend(doc["changes"])
                    self.processed_changes[doc["id"]] = revs_list
                else:
                    # Stored the doc with the list of rev changes
                    self.processed_changes[doc["id"]] = doc["changes"]

    def start(self):
        """
        Start a longpoll changes feed and and store the results in self.processed changes
        """

        auth_type = get_auth_type(self.auth)
        current_seq_num = 0

        while not self.cancel:

            log_info("self.cancel: {}".format(self.cancel))

            data = {
                "feed": "longpoll",
                "style": "all_docs",
                "timeout": 1000,
                "since": current_seq_num
            }

            log_info("Making Request")

            if auth_type == AuthType.session:
                resp = requests.post("{}/_changes".format(self.endpoint), data=json.dumps(data), cookies=dict(SyncGatewaySession=self.auth[1]), stream=True)
            elif auth_type == AuthType.http_basic:
                resp = requests.post("{}/_changes".format(self.endpoint), data=json.dumps(data), auth=self.auth, stream=True)
            else:
                resp = requests.post("{}/_changes".format(self.endpoint), data=json.dumps(data), stream=True)

            log_r(resp)
            resp.raise_for_status()
            resp_obj = resp.json()

            self.process_changes(resp_obj["results"])
            current_seq_num = resp_obj["last_seq"]

    def stop(self):
        """
        Stop the longpoll changes feed
        """
        log_info("Closing _changes feed ...")
        self.cancel = True

    def wait_until(self, expected_docs, timeout=30):
        """
        Poll self.processed_changes to see if all expected docs have been recieved
        via the changes feed. This will return false if the polling exceeds the timeout

        expected docs format: [{"id": "doc_id1" "rev": "rev1", "ok", "true"}, ...]
        """

        start = time.time()
        while True:
            if time.time() - start > timeout:
                log_info("ChangeTracker.wait_until: TIMEOUT")
                return False

            # Check that the expected docs exist in the the
            missing_docs = []
            for doc in expected_docs:
                if doc["id"] not in self.processed_changes:
                    # doc_id not found in changes
                    missing_docs.append(doc)
                else:
                    rev_found = False
                    for rev in self.processed_changes[doc["id"]]:
                        if rev["rev"] == doc["rev"]:
                            # Found rev in changes feed, continue with the next dox
                            log_info("FOUND id: {}, rev: {}".format(doc["id"], doc["rev"]))
                            rev_found = True

                    if not rev_found:
                        missing_docs.append(doc)

            if len(missing_docs) == 0:
                log_info(":) Saw all docs in the changes feed for ({})!".format(self.auth))

                return True

            log_info("Docs missing from changes feed: {}".format(missing_docs))

            time.sleep(1)
