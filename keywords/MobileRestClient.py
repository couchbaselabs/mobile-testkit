import logging
import json
import time
import requests
from requests import Session
from requests.exceptions import HTTPError

from robot.api.logger import console

from CouchbaseServer import CouchbaseServer
from libraries.data.doc_generators import *
from constants import *

def log_r(request):
    logging.info("{0} {1} {2}".format(
            request.request.method,
            request.request.url,
            request.status_code
        )
    )
    logging.debug("{0} {1}\nHEADERS = {2}\nBODY = {3}".format(
            request.request.method,
            request.request.url,
            request.request.headers,
            request.request.body,
        )
    )
    logging.debug("{}".format(request.text))

def parse_multipart_response(response):
    """
    Parses a multipart response where each section looks like below:
    --------------------------------------------------------------------
    --5570ab847be212079e2b05bbbfa023da25b07712bda36aec6481bca024f3
        Content-Type: application/json

        {"_id":"test_ls_db2_0","_rev":"1-9a525c69cafb3d1cdf69545fa5ccfecc","date_time_added":"2016-04-29 13:34:26.346148"}

    Returns a a list of docs {"rows": [ {"_id":"test_ls_db2_0","_rev":"1-9a525c69cafb3d1cdf69545fa5ccfecc" ... } ] }
    """
    rows = []

    for part in response.split("--"):

        part_lines = part.splitlines()
        # part_lines follow the format
        # [
        #   '5570ab847be212079e2b05bbbfa023da25b07712bda36aec6481bca024f3',
        #   Content-Type: application/json,
        #   { doc }
        # ]
        # Only include part that has doc property
        if part_lines and len(part_lines) > 2:
            doc = part_lines[-1]
            try:
                doc_obj = json.loads(doc)
                rows.append(doc_obj)
            except Exception as e:
                # A few lines from the response can't be parsed as docs
                logging.error("Could not parse docs as JSON: {} error: {}".format(doc, e))

    return {"rows": rows}

class MobileRestClient:
    """
    A set of robot keyworks that can be executed against
        - LiteServ (Mac OSX, Android, .NET)
        - sync_gateway
    via REST
    """

    def __init__(self):
        headers = {"Content-Type": "application/json"}
        self._session = Session()
        self._session.headers = headers

    def get_server_type(self, url):
        resp = self._session.get(url)
        log_r(resp)
        resp.raise_for_status()
        resp_obj = resp.json()

        try:
            if resp_obj["vendor"]["name"] == "Couchbase Sync Gateway":
                logging.info("ServerType={}".format(ServerType.syncgateway))
                return ServerType.syncgateway
            elif resp_obj["vendor"]["name"] == "Couchbase Lite (Objective-C)":
                logging.info("ServerType={}".format(ServerType.listener))
                return ServerType.listener
            elif resp_obj["vendor"]["name"] == "Couchbase Lite (C#)":
                logging.info("ServerType={}".format(ServerType.listener))
                return ServerType.listener
        except KeyError as ke:
            # Android LiteServ
            if resp_obj["CBLite"] == "Welcome":
                return ServerType.listener

        raise ValueError("Unsupported couchbase lite server type")

    def create_user(self, url, db, name, password, channels=[]):
        data = {
            "name": name,
            "password": password,
            "admin_channels": channels
        }
        resp = self._session.post("{}/{}/_user/".format(url, db), data=json.dumps(data))
        log_r(resp)
        resp.raise_for_status()

        return (name, password)

    def create_database(self, url, name, server=None):

        server_type = self.get_server_type(url)

        if server_type == ServerType.listener:
            resp = self._session.put("{}/{}/".format(url, name))
        elif server_type == ServerType.syncgateway:
            if server is None:
                raise ValueError("Creating database error. You must provide a server either ('walrus:' or '{coucbase_server_url}')")

            logging.info("Using server: {} for database: {}".format(server, name))

            if server != "walrus:":
                # Create bucket to support the database
                logging.info("Creating backing bucket for sync_gateway db '{}' on '{}'".format(name, server))
                server = CouchbaseServer()
                server.create_bucket(server, name)

            data = {
                "name": "{}".format(name),
                "server": server,
                "bucket": "{}".format(name)
            }
            resp = self._session.put("{}/{}/".format(url, name), data=json.dumps(data))

        log_r(resp)
        resp.raise_for_status()

        resp = self._session.get("{}/{}/".format(url, name))
        log_r(resp)
        resp.raise_for_status()

        resp_obj = resp.json()
        return resp_obj["db_name"]

    def delete_databases(self, url):
        resp = self._session.get("{}/_all_dbs".format(url))
        log_r(resp)
        resp.raise_for_status()

        db_list = resp.json()
        for db in db_list:
            resp = self._session.delete("{}/{}".format(url, db))
            log_r(resp)
            resp.raise_for_status()

    def get_doc(self, url, db, doc_id, auth):
        """
        returns a dictionary with the following format:

        {
            "_attachments":{
                "sample_text.txt":{
                    "digest":"sha1-x6zPGLnfGXxKdGqxUN2YzvFGdho=",
                    "length":445,
                    "revpos":1,
                    "stub":true}
                },
            "_id":"att_doc",
            "_rev":"1-59bd81bc19049947b4728f8c769a44bd",
            "content":"{ \"sample_key\": \"sample_value\" }"
            ,"updates":0
        }
        """

        resp = self._session.get("{}/{}/{}".format(url, db, doc_id), auth=auth)
        log_r(resp)
        resp.raise_for_status()
        resp_obj = resp.json()

        if "_attachments" in resp_obj:
            for k in resp_obj["_attachments"].keys():
                del resp_obj["_attachments"][k]["digest"]
                del resp_obj["_attachments"][k]["length"]

        return resp_obj

    def add_doc(self, url, db, doc, auth):
        doc["updates"] = 0
        resp = self._session.post("{}/{}/".format(url, db), data=json.dumps(doc), auth=auth)
        log_r(resp)
        resp.raise_for_status()
        resp_obj = resp.json()

        return {"id": resp_obj["id"], "rev": resp_obj["rev"]}

    def add_conflict(self, url, db, doc_id, parent_revision, new_revision, auth):
        """
            1. GETs the doc with id == doc_id
            2. adds a _revisions property with
                ids[0] == new_revision's digest

            Sample doc JSON:
            {
                "_rev":"2-foo",
                "_attachments":{"hello.txt":{"stub":true,"revpos":1}},
                "_revisions":{
                    "ids":[
                        "${new_revision's digest}",
                        "${parent_revision's digest}"
                    ],
                    "start":${new_revision's generation number}
                }
            }
        """
        logging.info("PARENT: {}".format(parent_revision))
        logging.info("NEW: {}".format(new_revision))

        doc = self.get_doc(url, db, doc_id, auth)

        # Delete rev property and add our own "_revisions"
        parent_revision_parts = parent_revision.split("-")
        parent_revision_generation = int(parent_revision_parts[0])
        parent_revision_digest = parent_revision_parts[1]

        new_revision_parts = new_revision.split("-")
        new_revision_generation = int(new_revision_parts[0])
        new_revision_digest = new_revision_parts[1]

        logging.debug("Parent Generation: {}".format(parent_revision_generation))
        logging.debug("Parent Digest: {}".format(parent_revision_digest))
        logging.debug("New Generation: {}".format(new_revision_generation))
        logging.debug("New Digest: {}".format(new_revision_digest))

        doc["_rev"] = new_revision
        doc["_revisions"] = {
            "ids": [
                new_revision_digest,
                parent_revision_digest
            ],
            "start": new_revision_generation
        }

        params = {"new_edits": "false"}
        resp = self._session.put("{}/{}/{}".format(url, db, doc_id), params=params, data=json.dumps(doc), auth=auth)
        log_r(resp)
        resp.raise_for_status()

    def update_doc(self, url, db, doc_id, number_updates, auth):
        """
        Updates a doc on a db a number of times.
            1. GETs the doc
            2. It increments the "updates" propery
            3. PUTS the doc
        """

        for i in xrange(number_updates):

            doc = self.get_doc(url, db, doc_id, auth)

            current_update_number = doc["updates"]
            doc["updates"] = current_update_number + 1

            resp = self._session.put("{}/{}/{}".format(url, db, doc_id), data=json.dumps(doc), auth=auth)

            log_r(resp)
            resp.raise_for_status()
            resp_obj = resp.json()

        return {"id": resp_obj["id"], "rev": resp_obj["rev"]}

    def add_docs(self, url, db, number, id_prefix, generator=simple()):

        docs = {}

        for i in xrange(number):

            doc_body = generator
            resp = self._session.put("{}/{}/{}_{}".format(url, db, id_prefix, i), data=doc_body)
            log_r(resp)
            resp.raise_for_status()

            doc_obj = resp.json()
            docs[doc_obj["id"]] = { "rev": doc_obj["rev"] }

        # check that the docs returned in the responses equals the expected number
        if len(docs) != number:
            raise RuntimeError("Client was not able to add all docs to: {}".format(url))

        logging.info(docs)

        return docs

    def start_replication(self, url, continuous, from_url=None, from_db=None, to_url=None, to_db=None):

        if from_url is None:
            source = from_db
        else:
            source = "{}/{}".format(from_url, from_db)

        if to_url is None:
            target = to_db
        else:
            target = "{}/{}".format(to_url, to_db)

        data = {
            "continuous": continuous,
            "source": source,
            "target": target
        }

        resp = self._session.post("{}/_replicate".format(url), data=json.dumps(data))
        log_r(resp)
        resp.raise_for_status()

    def verify_docs_present(self, url, db, expected_docs):
        """
        Verifies the expected docs are present in the database using a polling loop with
        POST _all_docs with Listener and a POST _bulk_get for sync_gateway

        expected_docs should be a dict {id: {rev: ""}} or
        a list of {id: {rev: ""}}. If the expected docs are a list, they will be converted to a single map.
        """

        server_type = self.get_server_type(url)

        if isinstance(expected_docs, list):
            # Create single dictionary for comparison
            expected_doc_map = {k: v for expected_doc_dict in expected_docs for k, v in expected_doc_dict.iteritems()}
        elif isinstance(expected_docs, dict):
            expected_doc_map = expected_docs
        else:
            raise TypeError("Verify Docs Preset expects a list or dict of expected docs")

        start = time.time()
        while True:

            if time.time() - start > CLIENT_REQUEST_TIMEOUT:
                raise Exception("Verify Docs Present: TIMEOUT")

            if server_type == ServerType.listener:

                data = {"keys": expected_doc_map.keys()}
                resp = self._session.post("{}/{}/_all_docs".format(url, db), data=json.dumps(data))
                log_r(resp)
                resp.raise_for_status()
                resp_obj = resp.json()

            elif server_type == ServerType.syncgateway:

                # Constuct _bulk_get body
                bulk_get_body_id_list = []
                for key in expected_doc_map.keys():
                    bulk_get_body_id_list.append({"id": key})
                bulk_get_body = {"docs": bulk_get_body_id_list}

                resp = self._session.post("{}/{}/_bulk_get".format(url, db), data=json.dumps(bulk_get_body))
                log_r(resp)
                resp.raise_for_status()

                resp_obj = parse_multipart_response(resp.text)

            # See any docs were not retured
            # Mac OSX - {"key":"test_ls_db2_5","error":"not_found"}
            # Android - {"doc":null,"id":"test_ls_db2_5","key":"test_ls_db2_5","value":{}}
            all_docs_returned = True
            missing_docs = []
            for resp_doc in resp_obj["rows"]:
                if "error" in resp_doc or ("value" in resp_doc and len(resp_doc["value"]) == 0):
                    missing_docs.append(resp_doc)
                    all_docs_returned = False

            logging.info("Missing Docs = {}".format(missing_docs))
            # Issue the request again, docs my still be replicating
            if not all_docs_returned:
                logging.info("Retrying ...")
                time.sleep(1)
                continue

            resp_docs = {}
            for resp_doc in resp_obj["rows"]:
                if server_type == ServerType.listener:
                    resp_docs[resp_doc["id"]] = { "rev": resp_doc["value"]["rev"] }
                elif server_type == ServerType.syncgateway:
                    resp_docs[resp_doc["_id"]] = {"rev": resp_doc["_rev"]}

            assert(expected_doc_map == resp_docs), "Unable to verify docs present. Dictionaries are not equal"
            break

    def verify_docs_in_changes(self, url, db, expected_docs):
        """
        Verifies the expected docs are present in the database _changes feed using longpoll in a loop with
        Uses a GET _changes?feed=longpoll&since=last_seq for Listener
        and POST _changes with a body {"feed": "longpoll", "since": last_seq} for sync_gateway

        expected_docs should be a dict {id: {rev: ""}} or
        a list of {id: {rev: ""}}. If the expected docs are a list, they will be converted to a single map.
        """

        if isinstance(expected_docs, list):
            # Create single dictionary for comparison
            expected_doc_map = {k: v for expected_doc_dict in expected_docs for k, v in expected_doc_dict.iteritems()}
        elif isinstance(expected_docs, dict):
            expected_doc_map = expected_docs
        else:
            raise TypeError("Verify Docs Preset expects a list or dict of expected docs")

        server_type = self.get_server_type(url)
        sequence_number_map = {}

        start = time.time()
        last_seq = 0
        while True:

            logging.info(time.time() - start)

            if time.time() - start > CLIENT_REQUEST_TIMEOUT:
                raise Exception("Verify Docs In Changes: TIMEOUT")

            if server_type == ServerType.listener:
                resp = self._session.get("{}/{}/_changes?feed=longpoll&since={}".format(url, db, last_seq))

            elif server_type == ServerType.syncgateway:
                body = {
                    "feed": "longpoll",
                    "since": last_seq
                }
                resp = self._session.post("{}/{}/_changes".format(url, db), data=json.dumps(body))

            log_r(resp)
            resp.raise_for_status()
            resp_obj = resp.json()

            missing_expected_docs = []
            for resp_doc in resp_obj["results"]:
                # Check changes results contain a doc in the expected docs
                if resp_doc["id"] in expected_doc_map:
                    assert resp_doc["seq"] not in sequence_number_map, "Found duplicate sequence number: {} in sequence map!!".format(resp_doc["seq"])
                    sequence_number_map[resp_doc["seq"]] = resp_doc["id"]
                    # Check that the rev of the changes docs matches the expected docs rev
                    for resp_doc_change in resp_doc["changes"]:
                        if resp_doc_change["rev"] == expected_doc_map[resp_doc["id"]]["rev"]:
                            # expected doc with expected revision found in changes, cross out doc from expected docs
                            del expected_doc_map[resp_doc["id"]]
                        else:
                            # expected rev not found
                            logging.debug("Found doc: {} in changes but could not find expected rev")
                else:
                    missing_expected_docs.append(resp_doc)

            logging.info("Missing docs: {}".format(expected_doc_map))
            logging.debug("Sequence number map: {}".format(sequence_number_map))

            if len(expected_doc_map) == 0:
                # All expected docs have been crossed out
                break

            # update last sequence and continue
            last_seq = int(resp_obj["last_seq"])
            logging.info("last_seq: {}".format(last_seq))

            time.sleep(1)





