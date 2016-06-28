import logging
import json
import time
import uuid
import requests
from requests import Session
from requests.exceptions import HTTPError
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

from CouchbaseServer import CouchbaseServer
from Document import get_attachment

from libraries.data import doc_generators

from constants import AuthType
from constants import ServerType
from constants import Platform
from constants import CLIENT_REQUEST_TIMEOUT

from utils import log_r
from utils import log_info

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

def get_auth_type(auth):

    if auth is None:
        return AuthType.none

    if auth[0] == "SyncGatewaySession":
        auth_type = AuthType.session
    else:
        auth_type = AuthType.http_basic

    logging.debug("Using auth type: {}".format(auth_type))
    return auth_type

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

    def merge(self, *doc_lists):
        """
        Keyword to merge multiple lists of document dictionarys into one list
        eg. [{u'id': u'ls_db1_0'}, ...] + [{u'id': u'ls_db2_0'}, ...] => [{u'id': u'ls_db1_0'}, {u'id': u'ls_db2_0'} ...]
        :param doc_lists: lists of document dictionaries to merge into one list
        :return: single list of documents
        """
        merged_list = []
        for doc_list in doc_lists:
            merged_list.extend(doc_list)
        return merged_list

    def get_server_type(self, url):
        """
        Issues a get to the service running at the specified url.
        It will return a server type of 'listener' or 'syncgateway'
        """

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

    def get_server_platform(self, url):
        """
        Issues a get to the service running at the specified url.
        It will return a server type of 'macosx', 'android', or 'net' for listener
        of centos for sync_gateway
        """

        resp = self._session.get(url)
        log_r(resp)
        resp.raise_for_status()
        resp_obj = resp.json()

        try:
            if resp_obj["vendor"]["name"] == "Couchbase Sync Gateway":
                logging.info("Platform={}".format(Platform.centos))
                return Platform.centos
            elif resp_obj["vendor"]["name"] == "Couchbase Lite (Objective-C)":
                logging.info("Platform={}".format(Platform.macosx))
                return Platform.macosx
            elif resp_obj["vendor"]["name"] == "Couchbase Lite (C#)":
                logging.info("Platform={}".format(Platform.net))
                return Platform.net
        except KeyError as ke:
            # Android LiteServ
            if resp_obj["CBLite"] == "Welcome":
                logging.info("Platform={}".format(Platform.android))
                return Platform.android

        raise ValueError("Unsupported platform type")

    def get_session(self, url):
        resp = self._session.get("{}/_session".format(url))
        log_r(resp)
        resp.raise_for_status()

        expected_response = {
            "userCtx": {
                "name": None,
                "roles": [
                    "_admin"
                    ]
                },
                "ok": True
            }

        assert resp.json() == expected_response, "Unexpected _session response from Listener"
        return resp.json()

    def create_session(self, url, db, name, ttl=86400):
        data = {
            "name": name,
            "ttl": ttl
        }
        resp = self._session.post("{}/{}/_session".format(url, db), data=json.dumps(data))
        log_r(resp)
        resp.raise_for_status()
        resp_obj = resp.json()
        return (resp_obj["cookie_name"], resp_obj["session_id"])

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

    def compact_database(self, url, db):
        """
        POST /{db}/_compact and will verify compaction by
        iterating though each document and inspecting the revs_info to make sure all revs are 'missing'
        except for the leaf revision
        """

        resp = self._session.post("{}/{}/_compact".format(url, db))
        log_r(resp)
        resp.raise_for_status()

        start = time.time()
        while True:

            if time.time() - start > CLIENT_REQUEST_TIMEOUT:
                raise Exception("Verify Docs Present: TIMEOUT")

            resp = self._session.get("{}/{}/_all_docs".format(url, db))
            log_r(resp)
            resp.raise_for_status()
            resp_obj = resp.json()

            all_revs_compacted = True

            for row in resp_obj["rows"]:
                doc_id = row["id"]
                doc = self.get_doc(url, db, doc_id, revs_info=True)

                revs_info = doc["_revs_info"]
                # _compact should reduce the revs to 20 on client
                if len(revs_info) > 20:
                    all_revs_compacted = False
                    break

                available_count = 0
                for rev_info in revs_info:
                    if rev_info["status"] == "available":
                        available_count += 1

                # After compaction, the number of a available revs should be 1 (the leaf revision)
                assert available_count == 1, "Revisions remain after compaction"

            if all_revs_compacted:
                logging.info("All docs compacted!")
                break
            else:
                logging.info("Found uncompacted revisions. Retrying ...")
                time.sleep(1)

    def delete_databases(self, url):
        resp = self._session.get("{}/_all_dbs".format(url))
        log_r(resp)
        resp.raise_for_status()

        db_list = resp.json()
        for db in db_list:
            resp = self._session.delete("{}/{}".format(url, db))
            log_r(resp)
            resp.raise_for_status()

    def get_rev_generation_digest(self, rev):
        """
        helper function that returns a tuple of generation and digest for a revision
        """
        rev_parts = rev.split("-")
        assert len(rev_parts) == 2, "Revision should have a generation and a digest"

        return rev_parts[0], rev_parts[1]

    def verify_revs_num_for_docs(self, url, db, docs, expected_revs_per_doc, auth=None):
        for doc in docs:
            self.verify_revs_num(url, db, doc["id"], expected_revs_per_doc, auth)

    def verify_revs_num(self, url, db, doc_id, expected_revs_per_docs, auth=None):
        """
        Verify that the number of revisions for a document is equal to the max expected number of revisions
        Validate with ?revs=true. Check that the doc's length of _revisions["ids"] == expected_number_revs
        """
        doc = self.get_doc(url, db, doc_id, auth)
        logging.debug(doc)

        doc_rev_ids_number = len(doc["_revisions"]["ids"])
        assert doc_rev_ids_number == expected_revs_per_docs, "Expected num revs: {}, Actual num revs: {}".format(
            expected_revs_per_docs, doc_rev_ids_number
        )

    def verify_max_revs_num_for_docs(self, url, db, docs, expected_max_number_revs_per_doc, auth=None):
        for doc in docs:
            self.verify_max_revs_num(url, db, doc["id"], expected_max_number_revs_per_doc, auth)

    def verify_max_revs_num(self, url, db, doc_id, expected_max_number_revs, auth=None):
        """
        Verify that the number of revisions for a document is less than or equal to the max expected number of revisions
        Validate with ?revs=true. Check that the doc's length of _revisions["ids"] <= expected_number_revs
        """

        doc = self.get_doc(url, db, doc_id, auth)
        logging.debug(doc)

        doc_rev_ids_number = len(doc["_revisions"]["ids"])
        assert doc_rev_ids_number <= expected_max_number_revs, "Expected num revs: {}, Actual num revs: {}".format(
            expected_max_number_revs, doc_rev_ids_number
        )

    def verify_docs_rev_generations(self, url, db, docs, expected_generation, auth=None):
        """
        Verify that the rev generation (rev = {generation}-{hash}) is the expected generation
        for a set of docs
        """
        for doc in docs:
            self.verify_doc_rev_generation(url, db, doc["id"], expected_generation, auth)

    def verify_doc_rev_generation(self, url, db, doc_id, expected_generation, auth=None):
        """
        Verify that the rev generation (rev = {generation}-{hash}) is the expected generation for a doc
        """
        doc = self.get_doc(url, db, doc_id, auth)
        rev = doc["_rev"]
        generation = int(rev.split("-")[0])
        logging.debug("Found generation: {}".format(generation))
        assert generation == expected_generation, "Expected generation: {} not found, found: {}".format(expected_generation, generation)

    def verify_open_revs(self, url, db, doc_id, expected_open_revs, auth=None):
        """
        1. Gets a current doc for doc_id
        2. Verifies that the /{db}/{doc_id}?open_revs=all matches that expected revisions
        """

        open_rev_resp = self.get_open_revs(url, db, doc_id, auth)

        open_revs = []
        for row in open_rev_resp:
            logging.debug(row)
            open_revs.append(row["ok"]["_rev"])

        assert len(open_revs) == len(expected_open_revs), "Unexpected open_revisions length! Expected: {}, Actual: {}".format(len(expected_open_revs), len(open_revs))
        assert set(open_revs) == set(expected_open_revs), "Unexpected open_revisions found! Expected: {}, Actual: {}".format(expected_open_revs, open_revs)
        log_info("Found expected open revs.")

    def get_open_revs(self, url, db, doc_id, auth=None):
        """
        Gets the open_revs=all for a specified doc_id.
        Returns a parsed multipart reponse in the below format
        {"rows" : docs}
        """
        # Returns multipart by default, specify json for cleaner code
        headers = {"Accept": "application/json"}

        auth_type = get_auth_type(auth)

        params = {"open_revs": "all"}


        if auth_type == AuthType.session:
            resp = self._session.get("{}/{}/{}".format(url, db, doc_id), headers=headers, params=params, cookies=dict(SyncGatewaySession=auth[1]))
        elif auth_type == AuthType.http_basic:
            resp = self._session.get("{}/{}/{}".format(url, db, doc_id), headers=headers, params=params, auth=auth)
        else:
            resp = self._session.get("{}/{}/{}".format(url, db, doc_id), headers=headers, params=params)

        log_r(resp)
        resp.raise_for_status()
        resp_obj = resp.json()

        return resp_obj

    def get_doc(self, url, db, doc_id, auth=None, rev=None, revs_info=False):
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
            "_revisions":{
                "ids":[
                    "875459bdcc4b76eb786cf8b956a7bb17",
                    ],
                "start":5
            },
            "content":"{ \"sample_key\": \"sample_value\" }"
            ,"updates":0
        }

        If revs_info is True, also include the following property:

         "_revs_info": [
            {
                "rev": "5-875459bdcc4b76eb786cf8b956a7bb17",
                "status": "available"
        },
        """

        auth_type = get_auth_type(auth)

        params = {
            "conflicts": "true",
            "revs": "true"
        }

        if revs_info:
            params["revs_info"] = "true"

        if rev:
            params["rev"] = rev

        if auth_type == AuthType.session:
            resp = self._session.get("{}/{}/{}".format(url, db, doc_id), params=params, cookies=dict(SyncGatewaySession=auth[1]))
        elif auth_type == AuthType.http_basic:
            resp = self._session.get("{}/{}/{}".format(url, db, doc_id), params=params, auth=auth)
        else:
            resp = self._session.get("{}/{}/{}".format(url, db, doc_id), params=params)

        log_r(resp)
        resp.raise_for_status()
        resp_obj = resp.json()

        if "_attachments" in resp_obj:
            for k in resp_obj["_attachments"].keys():
                del resp_obj["_attachments"][k]["digest"]
                del resp_obj["_attachments"][k]["length"]

        return resp_obj

    def add_doc(self, url, db, doc, auth=None):
        """
        Add a doc to a database. Either LiteServ or Sync Gateway

        Returns doc dictionary:
        {u'ok': True, u'rev': u'1-ccd39f3091bb9bb51524b97e69571f80', u'id': u'test_ls_db1_0'}
        """

        logging.info(auth)
        auth_type = get_auth_type(auth)

        doc["updates"] = 0

        if auth_type == AuthType.session:
            resp = self._session.post("{}/{}/".format(url, db), data=json.dumps(doc), cookies=dict(SyncGatewaySession=auth[1]))
        elif auth_type == AuthType.http_basic:
            resp = self._session.post("{}/{}/".format(url, db), data=json.dumps(doc), auth=auth)
        else:
            resp = self._session.post("{}/{}/".format(url, db), data=json.dumps(doc))

        log_r(resp)
        resp.raise_for_status()
        resp_obj = resp.json()

        return resp_obj

    def get_attachment(self, url, db, doc_id, attachment_name, auth=None):
        """
        Keyword to get a raw attachment with name 'attachment_name' for the specified 'doc_id'.
        ex. GET http://localhost:59840/ls_db/att_doc/sample_text.txt
        Returns the raw response.
        """

        headers = {"Accept": "*/*"}

        auth_type = get_auth_type(auth)

        if auth_type == AuthType.session:
            resp = self._session.get("{}/{}/{}/{}".format(url, db, doc_id, attachment_name), headers=headers, cookies=dict(SyncGatewaySession=auth[1]))
        elif auth_type == AuthType.http_basic:
            resp = self._session.get("{}/{}/{}/{}".format(url, db, doc_id, attachment_name), headers=headers, auth=auth)
        else:
            resp = self._session.get("{}/{}/{}/{}".format(url, db, doc_id, attachment_name), headers=headers)

        log_r(resp)
        resp.raise_for_status()

        return resp.text

    def add_conflict(self, url, db, doc_id, parent_revisions, new_revision, attachment_name=None, auth=None):
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

            IMPORTANT: If you specify a list of parent revisions, you need to make sure that they
            are ordered from latest to oldest to ensure the document is built correctly
        """

        if isinstance(parent_revisions, basestring):
            # if only one rev is specified, wrap it in a list
            parent_revs = [parent_revisions]
        elif isinstance(parent_revisions, list):
            parent_revs = parent_revisions
        else:
            raise TypeError("Add Conflict expects a list or str for parent_revisions")

        auth_type = get_auth_type(auth)

        logging.info("PARENT: {}".format(parent_revs))
        logging.info("NEW: {}".format(new_revision))

        doc = self.get_doc(url, db, doc_id, auth)

        # Delete rev property and add our own "_revisions"

        new_revision_parts = new_revision.split("-")
        new_revision_generation = int(new_revision_parts[0])
        new_revision_digest = new_revision_parts[1]

        logging.debug("New Generation: {}".format(new_revision_generation))
        logging.debug("New Digest: {}".format(new_revision_digest))

        doc["_rev"] = new_revision
        doc["_revisions"] = {
            "ids": [
                new_revision_digest
            ],
            "start": new_revision_generation
        }

        if attachment_name is not None:
            doc["_attachments"] = {
                attachment_name: {"data": get_attachment(attachment_name)}
            }


        parent_revision_digests = []
        for parent_rev in parent_revs:
            generation, digest = self.get_rev_generation_digest(parent_rev)
            parent_revision_digests.append(digest)

        logging.debug("parent_revision_digests: {}".format(parent_revision_digests))

        doc["_revisions"]["ids"].extend(parent_revision_digests)

        params = {"new_edits": "false"}

        if auth_type == AuthType.session:
            resp = self._session.put("{}/{}/{}".format(url, db, doc_id), params=params, data=json.dumps(doc), cookies=dict(SyncGatewaySession=auth[1]))
        elif auth_type == AuthType.http_basic:
            resp = self._session.put("{}/{}/{}".format(url, db, doc_id), params=params, data=json.dumps(doc), auth=auth)
        else:
            resp = self._session.put("{}/{}/{}".format(url, db, doc_id), params=params, data=json.dumps(doc))

        log_r(resp)
        resp.raise_for_status()

        return {"id": doc_id, "rev": new_revision}

    def get_conflict_revs(self, url, db, doc, auth=None):
        """
        Keyword that return the _conflicts revs array for a doc. It expects conflicts to exist.
        """
        doc_resp = self.get_doc(url, db, doc["id"], auth)
        conflict_revs = doc_resp["_conflicts"]
        logging.debug("Conflict revs: {}".format(conflict_revs))
        return conflict_revs

    def delete_conflicts(self, url, db, docs, auth=None):
        """
        Deletes all the conflicts for a dictionary of docs.
        1. Issue a GET with conflicts=true
        2. Issue a DELETE to {db}/{doc_id}?rev={rev_from_conflicts}
        3. Loop over all the docs and assert that no more conflicts exist
        """

        for doc in docs:
            doc_resp = self.get_doc(url, db, doc["id"], auth)
            if "_conflicts" in doc_resp:
                for rev in doc_resp["_conflicts"]:
                    self.delete_doc(url, db, doc["id"], rev)

        logging.info("Checkking that no _conflicts property is returned")

        for doc in docs:
            doc_resp = self.get_doc(url, db, doc["id"], auth)
            if "_conflicts" in doc:
                assert len(doc_resp["_conflicts"]) == 0, "Some conflicts still present after deletion: doc={}".format(doc)

    def delete_docs(self, url, db, docs, auth=None):
        """
        Deletes a set of docs with the latest revision
        """
        for doc in docs:
            doc_resp = self.get_doc(url, db, doc["id"], auth=auth)
            latest_rev = doc_resp["_rev"]
            self.delete_doc(url, db, doc["id"], latest_rev, auth=auth)

    def delete_doc(self, url, db, doc_id, rev, auth=None):
        """
        Removes a document with the specfied revision
        """

        auth_type = get_auth_type(auth)

        params = {}
        if rev is not None:
            params["rev"] = rev

        if auth_type == AuthType.session:
            resp = self._session.delete("{}/{}/{}".format(url, db, doc_id), params=params, cookies=dict(SyncGatewaySession=auth[1]))
        elif auth_type == AuthType.http_basic:
            resp = self._session.delete("{}/{}/{}".format(url, db, doc_id), params=params, auth=auth)
        else:
            resp = self._session.delete("{}/{}/{}".format(url, db, doc_id), params=params)

        log_r(resp)
        resp.raise_for_status()
        resp_obj = resp.json()

        return resp_obj

    def verify_docs_deleted(self, url, db, docs, auth=None):

        auth_type = get_auth_type(auth)
        server_type = self.get_server_type(url)
        server_platform = self.get_server_platform(url)

        start = time.time()
        while True:

            not_deleted = []

            if time.time() - start > CLIENT_REQUEST_TIMEOUT:
                raise Exception("Verify Docs Deleted: TIMEOUT")

            for doc in docs:
                if auth_type == AuthType.session:
                    resp = self._session.get("{}/{}/{}".format(url, db, doc["id"]), cookies=dict(SyncGatewaySession=auth[1]))
                elif auth_type == AuthType.http_basic:
                    resp = self._session.get("{}/{}/{}".format(url, db, doc["id"]), auth=auth)
                else:
                    resp = self._session.get("{}/{}/{}".format(url, db, doc["id"]))
                log_r(resp)
                resp_obj = resp.json()

                if resp.status_code == 200:
                    not_deleted.append(resp_obj)
                elif resp.status_code == 404:
                    if server_type == ServerType.syncgateway:
                        assert "error" in resp_obj and "reason" in resp_obj, "Response should have an error and reason"
                        assert resp_obj["error"] == "not_found", "error should be 'not_found'"
                        assert resp_obj["reason"] == "deleted", "reason should be 'not_found'"
                    elif server_type == ServerType.listener and server_platform == Platform.android:
                        assert "error" in resp_obj and "status" in resp_obj, "Response should have an error and status"
                        assert resp_obj["error"] == "not_found", "error should be 'not_found'"
                        assert resp_obj["status"] == 404, "status should be '404'"
                    elif server_type == ServerType.listener and server_platform == Platform.macosx:
                        assert "error" in resp_obj and "status" in resp_obj and "reason" in resp_obj, "Response should have an error, status, and reason"
                        assert resp_obj["error"] == "not_found", "error should be 'not_found'"
                        assert resp_obj["status"] == 404, "status should be '404'"
                        assert resp_obj["reason"] == "deleted", "status should be '404'"
                    else:
                        raise ValueError("Unsupported server type and platform")
                else:
                    raise HTTPError("Unexpected error for: {}".format(resp.status_code))

            if len(not_deleted) == 0:
                logging.info("All Docs Deleted")
                break
            else:
                logging.info("{} docs still not deleted. Retrying...".format(not_deleted))
                time.sleep(1)
                continue

    def update_docs(self, url, db, docs, number_updates, auth=None):

        updated_docs = []

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_to_url = [executor.submit(self.update_doc, url, db, doc["id"], number_updates, auth=auth) for doc in docs]
            for future in concurrent.futures.as_completed(future_to_url):
                update_doc_result = future.result()
                updated_docs.append(update_doc_result)

        logging.debug("url: {} db: {} updated: {}".format(url, db, updated_docs))
        return updated_docs

    def update_doc(self, url, db, doc_id, number_updates=1, attachment_name=None, auth=None):
        """
        Updates a doc on a db a number of times.
            1. GETs the doc
            2. It increments the "updates" propery
            3. PUTS the doc
        """

        auth_type = get_auth_type(auth)
        doc = self.get_doc(url, db, doc_id, auth)
        current_rev = doc["_rev"]
        current_update_number = doc["updates"] + 1

        for i in xrange(number_updates):

            # Add "random" this to make each update unique. This will
            # cause document to conflict rather than optimize out
            # this behavior due to the same rev hash for doc content
            doc["random"] = str(uuid.uuid4())

            doc["updates"] = current_update_number
            doc["_rev"] = current_rev

            if attachment_name is not None:
                doc["_attachments"] = {
                    attachment_name: {"data": get_attachment(attachment_name)}
                }


            if auth_type == AuthType.session:
                resp = self._session.put("{}/{}/{}".format(url, db, doc_id), data=json.dumps(doc), cookies=dict(SyncGatewaySession=auth[1]))
            elif auth_type == AuthType.http_basic:
                resp = self._session.put("{}/{}/{}".format(url, db, doc_id), data=json.dumps(doc), auth=auth)
            else:
                resp = self._session.put("{}/{}/{}".format(url, db, doc_id), data=json.dumps(doc))

            log_r(resp)
            resp.raise_for_status()
            resp_obj = resp.json()

            logging.debug(resp)

            current_update_number += 1
            current_rev = resp_obj["rev"]


        return resp_obj

    def add_docs(self, url, db, number, id_prefix, auth=None, channels=None, generator=None):
        """
        Add a 'number' of docs with a prefix 'id_prefix' using the provided generator from libraries.data.doc_generators.
        ex. id_prefix=testdoc with a number of 3 would create 'testdoc_0', 'testdoc_1', and 'testdoc_2'

        Returns list of docs with the format
        [{u'ok': True, u'rev': u'1-ccd39f3091bb9bb51524b97e69571f80', u'id': u'test_ls_db1_0'}, ... ]
        """
        added_docs = []
        auth_type = get_auth_type(auth)

        for i in xrange(number):

            if generator == "four_k":
                doc_body = doc_generators.four_k()
            else:
                doc_body = doc_generators.simple()

            if channels is not None:
                doc_body["channels"] = channels

            data = json.dumps(doc_body)

            if auth_type == AuthType.session:
                resp = self._session.put("{}/{}/{}_{}".format(url, db, id_prefix, i), data=data, cookies=dict(SyncGatewaySession=auth[1]))
            elif auth_type == AuthType.http_basic:
                resp = self._session.put("{}/{}/{}_{}".format(url, db, id_prefix, i), data=data, auth=auth)
            else:
                resp = self._session.put("{}/{}/{}_{}".format(url, db, id_prefix, i), data=data)
            log_r(resp)
            resp.raise_for_status()

            doc_obj = resp.json()
            added_docs.append(doc_obj)

        # check that the docs returned in the responses equals the expected number
        if len(added_docs) != number:
            raise RuntimeError("Client was not able to add all docs to: {}".format(url))

        logging.info(added_docs)

        return added_docs

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
        resp_obj = resp.json()

        replication_id = resp_obj["session_id"]
        logging.info("Replication started with: {}".format(replication_id))

        return replication_id

    def wait_for_replication_status_idle(self, url, replication_id):
        """
        Polls the /_active_task endpoint and waits for a replication to become idle
        """

        start = time.time()
        while True:
            if time.time() - start > CLIENT_REQUEST_TIMEOUT:
                raise Exception("Verify Docs Present: TIMEOUT")

            resp = self._session.get("{}/_active_tasks".format(url))
            log_r(resp)
            resp.raise_for_status()
            resp_obj = resp.json()

            replication_busy = False
            replication_found = False

            for replication in resp_obj:
                if replication["task"] == replication_id:
                    replication_found = True
                    if replication["status"] == "Idle":
                        replication_busy = False
                    else:
                        replication_busy = True

            assert replication_found, "Replication not found: {}".format(replication_id)

            if replication_found and not replication_busy:
                logging.info("Replication is idle: {}".format(replication_id))
                break
            else:
                logging.info("Replication busy. Retrying ...")
                time.sleep(1)

    def wait_for_no_replications(self, url):
        """
        Polls the /_active_task endpoint and wait for an empty array
        """
        start = time.time()
        while True:
            if time.time() - start > CLIENT_REQUEST_TIMEOUT:
                raise Exception("Verify Docs Present: TIMEOUT")

            resp = self._session.get("{}/_active_tasks".format(url))
            log_r(resp)
            resp.raise_for_status()
            resp_obj = resp.json()

            if not resp_obj:
                # active tasks is an empty array
                break
            else:
                logging.info("Replications still running. Retrying")
                time.sleep(1)

    def verify_docs_present(self, url, db, expected_docs, auth=None):
        """
        Verifies the expected docs are present in the database using a polling loop with
        POST _all_docs with Listener and a POST _bulk_get for sync_gateway

        expected_docs should be a dict {id: {rev: ""}} or
        a list of {id: {rev: ""}}. If the expected docs are a list, they will be converted to a single map.
        """

        auth_type = get_auth_type(auth)
        server_type = self.get_server_type(url)

        logging.debug(expected_docs)

        if isinstance(expected_docs, list):
            # Create single dictionary for comparison, will also blow up for duplicate docs with the same id
            expected_doc_map = {expected_doc["id"]: expected_doc["rev"] for expected_doc in expected_docs}
        elif isinstance(expected_docs, dict):
            # When expected docs is a single doc
            expected_doc_map = {expected_docs["id"]: expected_docs["rev"]}
        else:
            raise TypeError("Verify Docs Preset expects a list or dict of expected docs")

        logging.debug(expected_docs)

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

                if auth_type == AuthType.session:
                    resp = self._session.post("{}/{}/_bulk_get".format(url, db), data=json.dumps(bulk_get_body), cookies=dict(SyncGatewaySession=auth[1]))
                elif auth_type == AuthType.http_basic:
                    resp = self._session.post("{}/{}/_bulk_get".format(url, db), data=json.dumps(bulk_get_body), auth=auth)
                else:
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
                    # Doc not found
                    missing_docs.append(resp_doc)
                    all_docs_returned = False
                elif server_type == ServerType.listener and resp_doc["value"]["rev"] != expected_doc_map[resp_doc["id"]]:
                    # Found the doc but unexpected rev on LiteServ
                    missing_docs.append(resp_doc)
                    all_docs_returned = False
                elif server_type == ServerType.syncgateway and resp_doc["_rev"] != expected_doc_map[resp_doc["_id"]]:
                    # Found the doc but unexpected rev on LiteServ
                    missing_docs.append(resp_doc)
                    all_docs_returned = False

            logging.info("Missing Docs = {}".format(missing_docs))
            # Issue the request again, docs my still be replicating
            if not all_docs_returned:
                logging.info("Retrying to verify all docs are present ...")
                time.sleep(1)
                continue

            resp_docs = {}
            for resp_doc in resp_obj["rows"]:
                if server_type == ServerType.listener:
                    resp_docs[resp_doc["id"]] = resp_doc["value"]["rev"]
                elif server_type == ServerType.syncgateway:
                    resp_docs[resp_doc["_id"]] = resp_doc["_rev"]

            logging.debug("Expected: {}".format(expected_doc_map))
            logging.debug("Actual: {}".format(resp_docs))
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
            # Create single dictionary for comparison, will also blow up for duplicate docs with the same id
            expected_doc_map = {expected_doc["id"]: expected_doc["rev"] for expected_doc in expected_docs}
        elif isinstance(expected_docs, dict):
            # When expected docs is a single doc
            expected_doc_map = {expected_docs["id"]: expected_docs["rev"]}
        else:
            raise TypeError("Verify Docs In Changes expects a list or dict of expected docs")

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
                        if resp_doc_change["rev"] == expected_doc_map[resp_doc["id"]]:
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

    def add_design_doc(self, url, db, name, view):
        """
        Keyword that adds a Design Doc to the database
        """
        resp = self._session.put("{}/{}/_design/{}".format(url, db, name), data=view)
        log_r(resp)
        resp.raise_for_status()

        resp_obj = resp.json()

        return resp_obj["id"]

    def get_view(self, url, db, design_doc_id, view_name):
        """
        Keyword that returns a view query for a design doc with a view name
        """
        resp = self._session.get("{}/{}/{}/_view/{}".format(url, db, design_doc_id, view_name))
        log_r(resp)
        resp.raise_for_status()
        return resp.json()

    def verify_view_row_num(self, view_response, expected_num_rows):
        """
        Keyword that verifies the length of rows return from a view is the expected number of rows
        """
        num_row_entries = len(view_response["rows"])
        num_total_rows = view_response["total_rows"]
        logging.info("Expected rows: {}".format(expected_num_rows))
        logging.info("Number of row entries: {}".format(num_row_entries))
        logging.info("Number of total_rows: {}".format(num_total_rows))
        assert num_row_entries == expected_num_rows, "Expeced number of rows did not match number of 'rows'"
        assert num_row_entries == num_total_rows, "Expeced number of rows did not match number of 'total_rows'"

    def verify_view_contains_keys(self, view_response, keys):
        """
        Keyword that verifies a view response contain all of the keys specified and no more than that
        """
        if not isinstance(keys, list):
            keys = [keys]

        assert len(view_response["rows"]) == len(keys), "Different number of rows were returned than expected keys"
        for row in view_response["rows"]:
            assert row["key"] in keys, "Did not find expected key in view response"

    def verify_view_contains_values(self, view_response, values):
        """
        Keyword that verifies a view response contain all of the values specified and no more than that
        """
        if not isinstance(values, list):
            values = [values]

        assert len(view_response["rows"]) == len(values), "Different number of rows were returned than expected values"
        for row in view_response["rows"]:
            assert row["value"] in values, "Did not find expected value in view response"
