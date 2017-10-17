import logging
import json
import time
import uuid
import re

from requests import Session
from requests.exceptions import HTTPError

import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

from keywords import attachment
from libraries.data import doc_generators
from libraries.provision.ansible_runner import AnsibleRunner

from keywords.constants import AuthType
from keywords.constants import ServerType
from keywords.constants import Platform
from keywords.constants import CLIENT_REQUEST_TIMEOUT
from keywords.constants import REGISTERED_CLIENT_DBS
from keywords.utils import log_r
from keywords.utils import log_info
from keywords.utils import log_debug
from keywords.SyncGateway import validate_sync_gateway_mode

from keywords.exceptions import RestError, TimeoutException, LiteServError, ChangesError
from keywords import types


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
        except KeyError:
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
        except KeyError:
            # Android LiteServ
            if resp_obj["CBLite"] == "Welcome":
                logging.info("Platform={}".format(Platform.android))
                return Platform.android

        raise ValueError("Unsupported platform type")

    def get_session(self, url, db=None, session_id=None):

        """
        :param url: url to get session from
        :param session_id: the session id to get information from
        :param db: database where session lives
        """

        if self.get_server_type(url) == ServerType.listener:
            # Listener should support the endpoint
            resp = self._session.get("{}/_session".format(url))
            log_r(resp)
            resp.raise_for_status()

            expected_response = {
                "userCtx": {
                    "name": None,
                    "roles": ["_admin"]
                },
                "ok": True
            }

            resp_obj = resp.json()
            assert resp_obj == expected_response, "Unexpected _session response from Listener"

        else:
            # Sync Gateway
            # Make sure session exists
            resp = self._session.get("{}/{}/_session/{}".format(url, db, session_id))
            log_r(resp)
            resp.raise_for_status()

            resp_obj = resp.json()
            assert resp_obj["ok"], "Make sure response includes 'ok'"

        return resp_obj

    def request_session(self, url, db, name, password=None, ttl=86400):
        data = {
            "name": name,
            "ttl": ttl
        }

        if password:
            data["password"] = password

        resp = self._session.post("{}/{}/_session".format(url, db), data=json.dumps(data))
        log_r(resp)
        resp.raise_for_status()
        return resp

    def create_session(self, url, db, name, password=None, ttl=86400):
        resp = self.request_session(url, db, name, password, ttl)
        resp_obj = resp.json()

        if "cookie_name" in resp_obj:
            # _session called via admin port
            # Cookie name / session is returned in response
            cookie_name = resp_obj["cookie_name"]
            session_id = resp_obj["session_id"]
        else:
            # _session called via public port.
            # get session info from 'Set-Cookie' header
            set_cookie_header = resp.headers["Set-Cookie"]

            # Split header on '=' and ';' characters
            cookie_parts = re.split("=|;", set_cookie_header)

            cookie_name = cookie_parts[0]
            session_id = cookie_parts[1]

        return cookie_name, session_id

    def create_session_header(self, url, db, name, password=None, ttl=86400):
        """
        Issues a POST to the public _session enpoint on sync_gateway for a user.
        Return the entire 'Set-Cookie' header. This is useful for creating authenticated
        push and pull replication via the Listener and REST
        """
        resp = self.request_session(url, db, name, password, ttl)
        return resp.headers["Set-Cookie"]

    def delete_session(self, url, db, user_name=None, session_id=None):
        """
        Sync Gateway only.

        :param url: sync_gateway endpoint (either public or admin port)
        :param db: database to delete the cookie from
        :param user_name: user_name associated with the cookie
        :param session_id: cookie session id to delete
        """

        if user_name is not None:
            # Delete session via /{db}/_user/{user-name}/_session/{session-id}
            resp = self._session.delete("{}/{}/_user/{}/_session/{}".format(url, db, user_name, session_id))
            log_r(resp)
            resp.raise_for_status()
        else:
            # Delete session via /{db}/_session/{session-id}
            resp = self._session.delete("{}/{}/_session/{}".format(url, db, session_id))
            log_r(resp)
            resp.raise_for_status()

    def get_role(self, url, db, name):
        """ Gets a roles for a db """

        resp = self._session.get("{}/{}/_role/{}".format(url, db, name))
        log_r(resp)
        resp.raise_for_status()

        return resp.json()

    def get_roles(self, url, db):
        """ Gets a list of roles for a db """

        resp = self._session.get("{}/{}/_role/".format(url, db))
        log_r(resp)
        resp.raise_for_status()

        return resp.json()

    def create_role(self, url, db, name, channels=None):
        """ Creates a role with name and channels for the specified 'db' """

        if channels is None:
            channels = []

        types.verify_is_list(channels)

        data = {
            "name": name,
            "admin_channels": channels
        }

        resp = self._session.post("{}/{}/_role/".format(url, db), data=json.dumps(data))
        log_r(resp)
        resp.raise_for_status()

    def update_role(self, url, db, name, channels=None):
        """ Updates a role with name and channels for the specified 'db' """

        if channels is None:
            channels = []

        types.verify_is_list(channels)

        data = {
            "name": name,
            "admin_channels": channels
        }

        resp = self._session.put("{}/{}/_role/{}".format(url, db, name), data=json.dumps(data))
        log_r(resp)
        resp.raise_for_status()

    def get_user(self, url, db, name):
        """ Gets a user for a db """

        resp = self._session.get("{}/{}/_user/{}".format(url, db, name))
        log_r(resp)
        resp.raise_for_status()

        return resp.json()

    def get_users(self, url, db):
        """ Gets a list of users for a db """

        resp = self._session.get("{}/{}/_user/".format(url, db))
        log_r(resp)
        resp.raise_for_status()

        return resp.json()

    def create_user(self, url, db, name, password, channels=None, roles=None):
        """ Creates a user with channels on the sync_gateway Admin REST API.
        Returns a name password tuple that can be used for session creation or basic authentication
        """

        if channels is None:
            channels = []

        if roles is None:
            roles = []

        types.verify_is_list(channels)
        types.verify_is_list(roles)

        data = {
            "name": name,
            "password": password,
            "admin_channels": channels,
            "admin_roles": roles
        }
        resp = self._session.post("{}/{}/_user/".format(url, db), data=json.dumps(data))
        log_r(resp)
        resp.raise_for_status()
        return name, password

    def update_user(self, url, db, name, password=None, channels=None, roles=None):
        """ Updates a user via the admin REST api
        Returns a name password tuple that can be used for session creation or basic authentication.

        Important!! If you provide a password, any sessions associated with the user will be destroyed
        """

        if channels is None:
            channels = []

        if roles is None:
            roles = []

        types.verify_is_list(channels)
        types.verify_is_list(roles)

        data = {
            "name": name,
            "admin_channels": channels,
            "admin_roles": roles
        }

        if password is not None:
            data["password"] = password

        resp = self._session.put("{}/{}/_user/{}".format(url, db, name), data=json.dumps(data))
        log_r(resp)
        resp.raise_for_status()
        return name, password

    def create_database(self, url, name, sync_gateway_mode=None, server_url=None, bucket_name=None, index_bucket_name=None, is_index_writer=None):
        """
        Create a Listener or Sync Gateway database via REST.

        IMPORTANT: If you want your database to run in encrypted mode on Mac, you must add the
        database name=password to the 'Start MacOSX LiteServ' keyword (resources/common.robot)

        To create a database on sync_gateway, you need to provide
        - sync_gateway_mode
        - server_url
        - bucket_name

        This assumes the buckets already exist on Couchbase Server.

        If you are running in distributed index mode (di, SG Accel), you need to provide
        - index_bucket_name
        - is_index_writer

        NOTE: In order for distributed index to work, you must create a db on the sg nodes (is_index_writer=False) as
        well as on the accel nodes (is_index_writer=False)
        """

        server_type = self.get_server_type(url)

        if server_type == ServerType.listener:

            if name not in REGISTERED_CLIENT_DBS:
                # If the db name is not in registered dbs and you are running
                # in excrypted mode (SQLCipher or ForestDB+Encryption), the db will be created
                # with no encryption silently. Adding the db to REGISTERED_CLIENT_DBS makes sure that
                # the db has a password and will be encrypted upon creation.
                raise ValueError("Make sure you have registered you db name in keywords/constants: {}".format(name))

            resp = self._session.put("{}/{}/".format(url, name))

        elif server_type == ServerType.syncgateway:

            validate_sync_gateway_mode(sync_gateway_mode)

            data = {}
            if server_url is None:
                raise RestError("Creating database error. You must provide a couchbase server url")
            data["server"] = server_url

            if bucket_name is None:
                raise RestError("Creating database error. You must provide a couchbase server bucket name")
            data["bucket"] = bucket_name

            if sync_gateway_mode is None:
                raise RestError("You must specify either 'cc' or 'di' for sync_gateway_mode")

            if sync_gateway_mode == "di" and index_bucket_name is None:
                raise RestError("You must provide an 'index_bucket_name' if you are running in distributed index mode")

            if sync_gateway_mode == "di" and is_index_writer is None:
                raise RestError("Please make sure you set 'is_index_writer' since you are running in 'di' mode")

            # Add additional information if running in distributed index mode
            if sync_gateway_mode == "di":
                data["channel_index"] = {
                    "server": server_url,
                    "bucket": index_bucket_name,
                    "writer": is_index_writer
                }

            resp = self._session.put("{}/{}/".format(url, name), data=json.dumps(data))

        log_r(resp)
        resp.raise_for_status()

        resp = self._session.get("{}/{}/".format(url, name))
        log_r(resp)
        resp.raise_for_status()

        resp_obj = resp.json()
        return resp_obj["db_name"]

    def get_databases(self, url):
        """
        Gets the databases for LiteServ or sync_gateway
        :param url: url of running service
        :return: array of database names
        """

        resp = self._session.get("{}/_all_dbs".format(url))
        log_r(resp)
        resp.raise_for_status()

        return resp.json()

    def get_database(self, url, db_name):
        """
        Gets the databases for LiteServ or sync_gateway
        :param url: url of running service
        :return: array of database names
        """

        resp = self._session.get("{}/{}".format(url, db_name))
        log_r(resp)
        resp.raise_for_status()

        return resp.json()

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
                raise TimeoutException("Verify Docs Present: TIMEOUT")

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

    def delete_database(self, url, name):
        """ Delete a database with 'name' """

        resp = self._session.delete("{}/{}".format(url, name))
        log_r(resp)
        resp.raise_for_status()

    def delete_databases(self, url):
        """ Delete all the databases for a given url """

        db_names = self.get_databases(url)
        for db_name in db_names:
            self.delete_database(url, db_name)

        # verify dbs are deleted
        db_names = self.get_databases(url)
        if len(db_names) != 0:
            raise LiteServError("Failed to delete dbs!")

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

        log_info("{} num revs: {} expected_revs_per_doc: {}".format(doc_id, doc_rev_ids_number, expected_revs_per_docs))

        if doc_rev_ids_number != expected_revs_per_docs:
            raise AssertionError("Expected num revs: {}, Actual num revs: {}".format(
                expected_revs_per_docs,
                doc_rev_ids_number
            ))

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

        log_info("{} num revs: {} expected_max_number_revs: {}".format(doc_id, doc_rev_ids_number, expected_max_number_revs))

        if doc_rev_ids_number > expected_max_number_revs:
            raise AssertionError("Expected num revs: {}, Actual num revs: {}".format(
                expected_max_number_revs,
                doc_rev_ids_number)
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
        log_info("doc {} has generation: {}, expected_generation: {}".format(doc_id, generation, expected_generation), is_verify=True)

        if generation != expected_generation:
            raise AssertionError("Expected generation: {} not found, found: {}".format(expected_generation, generation))

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

        if len(open_revs) != len(expected_open_revs):
            raise AssertionError("Unexpected open_revisions length! Expected: {}, Actual: {}".format(len(expected_open_revs), len(open_revs)))

        if set(open_revs) != set(expected_open_revs):
            raise AssertionError("Unexpected open_revisions found! Expected: {}, Actual: {}".format(expected_open_revs, open_revs))

        log_info("open revs: \n    found: {}\n    expected: {}".format(open_revs, expected_open_revs), is_verify=True)

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

    def get_raw_doc(self, url, db, doc_id):
        """ Get a document via _raw Sync Gateway endpoint """
        resp = self._session.get("{}/{}/_raw/{}".format(url, db, doc_id))
        log_r(resp)
        resp.raise_for_status()
        return resp.json()

    def add_doc(self, url, db, doc, auth=None, use_post=True):
        """
        Add a doc to a database. Either LiteServ or Sync Gateway

        Returns doc dictionary:
        {u'ok': True, u'rev': u'1-ccd39f3091bb9bb51524b97e69571f80', u'id': u'test_ls_db1_0'}
        """

        logging.info(auth)
        auth_type = get_auth_type(auth)

        doc["updates"] = 0

        if auth_type == AuthType.session:
            if use_post:
                resp = self._session.post("{}/{}/".format(url, db), data=json.dumps(doc), cookies=dict(SyncGatewaySession=auth[1]))
            else:
                resp = self._session.put("{}/{}/{}".format(url, db, doc["_id"]), data=json.dumps(doc), cookies=dict(SyncGatewaySession=auth[1]))
        elif auth_type == AuthType.http_basic:
            if use_post:
                resp = self._session.post("{}/{}/".format(url, db), data=json.dumps(doc), auth=auth)
            else:
                resp = self._session.put("{}/{}/{}".format(url, db, doc["_id"]), data=json.dumps(doc), auth=auth)
        else:
            if use_post:
                resp = self._session.post("{}/{}/".format(url, db), data=json.dumps(doc))
            else:
                resp = self._session.put("{}/{}/{}".format(url, db, doc["_id"]), data=json.dumps(doc))

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
            atts = attachment.load_from_data_dir([attachment_name])
            doc["_attachments"] = {
                atts[0].name: {"data": atts[0].data}
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
        log_info("Conflict revs: {}".format(conflict_revs))
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

    def verify_docs_deleted(self, url, db, docs, auth=None, reason="deleted"):

        auth_type = get_auth_type(auth)
        server_type = self.get_server_type(url)
        server_platform = self.get_server_platform(url)

        start = time.time()
        while True:

            not_deleted = []

            if time.time() - start > CLIENT_REQUEST_TIMEOUT:
                raise TimeoutException("Verify Docs Deleted: TIMEOUT")

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
                        assert resp_obj["reason"] == reason, "reason should be '{}'".format(reason)
                    elif server_type == ServerType.listener and server_platform == Platform.android:
                        assert "error" in resp_obj and "status" in resp_obj, "Response should have an error and status"
                        assert resp_obj["error"] == "not_found", "error should be 'not_found'"
                        assert resp_obj["status"] == 404, "status should be '404'"
                    elif server_type == ServerType.listener and (server_platform == Platform.macosx or server_platform == Platform.net):
                        assert "error" in resp_obj and "status" in resp_obj and "reason" in resp_obj, "Response should have an error, status, and reason"
                        assert resp_obj["error"] == "not_found", "error should be 'not_found'"
                        assert resp_obj["status"] == 404, "status should be '404'"
                        assert resp_obj["reason"] == reason, "reason should be '{}'".format(reason)
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

    def purge_docs(self, url, db, docs):
        """
        Purges the each doc in the provided 'docs' given the 'id' and 'rev'

        docs format (lite): [{u'ok': True, u'rev': u'3-56e50918afe3e9b3c29e94ad55cc6b15', u'id': u'large_attach_0'}, ...]
        docs format (Sync Gateway): [{u'ok': True, u'_rev': u'3-56e50918afe3e9b3c29e94ad55cc6b15', u'_id': u'large_attach_0'}, ...]
        """

        server_type = self.get_server_type(url=url)

        purged_docs = []
        for doc in docs:

            if server_type == ServerType.syncgateway:
                log_info("Purging doc: {}".format(doc["_id"]))
                data = {
                    doc["_id"]: ['*']
                }
            else:
                log_info("Purging doc: {}".format(doc["id"]))
                data = {
                    doc["id"]: [doc["rev"]]
                }

            resp = self._session.post("{}/{}/_purge".format(url, db), json.dumps(data))
            log_r(resp)
            resp.raise_for_status()
            resp_obj = resp.json()
            purged_docs.append(resp_obj)

        return purged_docs

    def update_docs(self, url, db, docs, number_updates, delay=None, auth=None, channels=None, property_updater=None):
        """ Updates docs (using doc["id"]) a number of times. It will wait a number of seconds (delay)
        between each update. The 'property_updater' can specify a custom property to update on each
        iteration.
        """

        updated_docs = []

        with ThreadPoolExecutor(max_workers=2) as executor:

            future_to_url = [
                executor.submit(
                    self.update_doc,
                    url,
                    db,
                    doc["id"],
                    number_updates=number_updates,
                    delay=delay,
                    auth=auth,
                    channels=channels,
                    property_updater=property_updater
                ) for doc in docs
            ]

            for future in concurrent.futures.as_completed(future_to_url):
                update_doc_result = future.result()
                updated_docs.append(update_doc_result)

        logging.debug("url: {} db: {} updated: {}".format(url, db, updated_docs))
        return updated_docs

    def put_doc(self, url, db, doc_id, doc_body, rev, auth=None):
        """
        Updates a doc with doc id, a given revision, and doc body
        """

        auth_type = get_auth_type(auth)

        params = {
            "rev": rev
        }

        if auth_type == AuthType.session:
            resp = self._session.put("{}/{}/{}".format(url, db, doc_id), params=params, data=json.dumps(doc_body), cookies=dict(SyncGatewaySession=auth[1]))
        elif auth_type == AuthType.http_basic:
            resp = self._session.put("{}/{}/{}".format(url, db, doc_id), params=params, data=json.dumps(doc_body), auth=auth)
        else:
            resp = self._session.put("{}/{}/{}".format(url, db, doc_id), params=params, data=json.dumps(doc_body))

        log_r(resp)
        resp.raise_for_status()

        return resp.json()

    def update_doc(self, url, db, doc_id, number_updates=1, attachment_name=None, expiry=None, delay=None, auth=None, channels=None, property_updater=None):
        """
        Updates a doc on a db a number of times.
            1. GETs the doc
            2. It increments the "updates" propery
            3. PUTS the doc
        """

        auth_type = get_auth_type(auth)
        doc = self.get_doc(url, db, doc_id, auth)
        current_rev = doc["_rev"]
        try:
            doc["updates"]
        except Exception:
            doc["updates"] = 0
        current_update_number = doc["updates"] + 1

        log_info("Updating {}/{}/{}: {} times".format(url, db, doc_id, number_updates))

        for i in xrange(number_updates):

            # Add "random" this to make each update unique. This will
            # cause document to conflict rather than optimize out
            # this behavior due to the same rev hash for doc content
            doc["random"] = str(uuid.uuid4())

            doc["updates"] = current_update_number
            doc["_rev"] = current_rev

            if attachment_name is not None:
                atts = attachment.load_from_data_dir([attachment_name])
                doc["_attachments"] = {
                    atts[0].name: {"data": atts[0].data}
                }

            if expiry is not None:
                doc["_exp"] = expiry

            if channels is not None:
                types.verify_is_list(channels)
                doc["channels"] = channels

            if property_updater is not None:
                types.verify_is_callable(property_updater)
                doc = property_updater(doc)

            if auth_type == AuthType.session:
                resp = self._session.put("{}/{}/{}".format(url, db, doc_id), data=json.dumps(doc), cookies=dict(SyncGatewaySession=auth[1]))
            elif auth_type == AuthType.http_basic:
                resp = self._session.put("{}/{}/{}".format(url, db, doc_id), data=json.dumps(doc), auth=auth)
            else:
                resp = self._session.put("{}/{}/{}".format(url, db, doc_id), data=json.dumps(doc))

            log_r(resp, info=False)
            resp.raise_for_status()
            resp_obj = resp.json()

            logging.debug(resp)

            current_update_number += 1
            current_rev = resp_obj["rev"]

            if delay is not None:
                logging.debug("Sleeping: {}s ...".format(delay))
                time.sleep(delay)

        return resp_obj

    def add_docs(self, url, db, number, id_prefix, auth=None, channels=None, generator=None, attachments_generator=None):
        """
        if id_prefix == None, generate a uuid for each doc

        Add a 'number' of docs with a prefix 'id_prefix' using the provided generator from libraries.data.doc_generators.
        ex. id_prefix=testdoc with a number of 3 would create 'testdoc_0', 'testdoc_1', and 'testdoc_2'
        """
        added_docs = []

        if channels is not None:
            types.verify_is_list(channels)

        log_info("PUT {} docs to {}/{}/ with prefix {}".format(number, url, db, id_prefix))

        for i in xrange(number):

            if generator == "four_k":
                doc_body = doc_generators.four_k()
            else:
                doc_body = doc_generators.simple()

            if channels is not None:
                doc_body["channels"] = channels

            if attachments_generator:
                types.verify_is_callable(attachments_generator)
                attachments = attachments_generator()
                doc_body["_attachments"] = {att.name: {"data": att.data} for att in attachments}

            if id_prefix is None:
                doc_id = str(uuid.uuid4())
            else:
                doc_id = "{}_{}".format(id_prefix, i)

            doc_body["_id"] = doc_id

            doc_obj = self.add_doc(url, db, doc_body, auth=auth, use_post=False)
            if attachments_generator:
                doc_obj["attachments"] = doc_body["_attachments"].keys()
            added_docs.append(doc_obj)

        # check that the docs returned in the responses equals the expected number
        if len(added_docs) != number:
            raise AssertionError("Client was not able to add all docs to: {}".format(url))

        log_info("Added: {} docs".format(len(added_docs)))

        return added_docs

    def add_bulk_docs(self, url, db, docs, auth=None):
        """
        Keyword that issues POST _bulk docs with the specified 'docs'.
        Use the Document.create_docs() to create the docs.
        """
        auth_type = get_auth_type(auth)
        server_type = self.get_server_type(url)

        # transform 'docs' into a format expected by _bulk_docs
        if server_type == ServerType.listener:
            request_body = {"docs": docs, "new_edits": True}
        else:
            request_body = {"docs": docs}

        if auth_type == AuthType.session:
            resp = self._session.post("{}/{}/_bulk_docs".format(url, db),
                                      data=json.dumps(request_body),
                                      cookies=dict(SyncGatewaySession=auth[1]))
        elif auth_type == AuthType.http_basic:
            resp = self._session.post("{}/{}/_bulk_docs".format(url, db), data=json.dumps(request_body), auth=auth)
        else:
            resp = self._session.post("{}/{}/_bulk_docs".format(url, db), data=json.dumps(request_body))

        log_r(resp)
        resp.raise_for_status()
        resp_obj = resp.json()

        for doc_resp in resp_obj:
            if "error" in doc_resp:
                raise RestError("Error while adding bulk docs!")

        return resp_obj

    def delete_bulk_docs(self, url, db, docs, auth=None):
        """
        Issues a bulk delete by setting the _deleted flag to true.
        This will create a tombstone.
        """
        auth_type = get_auth_type(auth)
        server_type = self.get_server_type(url)

        for doc in docs:
            doc['_deleted'] = True

        # transform 'docs' into a format expected by _bulk_docs
        if server_type == ServerType.listener:
            request_body = {"docs": docs, "new_edits": True}
        else:
            request_body = {"docs": docs}

        if auth_type == AuthType.session:
            resp = self._session.post("{}/{}/_bulk_docs".format(url, db),
                                      data=json.dumps(request_body),
                                      cookies=dict(SyncGatewaySession=auth[1]))
        elif auth_type == AuthType.http_basic:
            resp = self._session.post("{}/{}/_bulk_docs".format(url, db), data=json.dumps(request_body), auth=auth)
        else:
            resp = self._session.post("{}/{}/_bulk_docs".format(url, db), data=json.dumps(request_body))

        log_r(resp)
        resp.raise_for_status()
        resp_obj = resp.json()

        for resp_doc in resp_obj:
            if "error" in resp_doc:
                raise RestError("Error during deleting docs in bulk")

        return resp_obj

    def get_all_docs(self, url, db, auth=None, include_docs=False):
        """ Get all docs for a database via _all_docs """

        auth_type = get_auth_type(auth)

        params = {}
        if include_docs:
            params["include_docs"] = "true"

        if auth_type == AuthType.session:
            resp = self._session.get("{}/{}/_all_docs".format(url, db), params=params, cookies=dict(SyncGatewaySession=auth[1]))
        elif auth_type == AuthType.http_basic:
            resp = self._session.get("{}/{}/_all_docs".format(url, db), params=params, auth=auth)
        else:
            resp = self._session.get("{}/{}/_all_docs".format(url, db), params=params)

        log_r(resp)
        resp.raise_for_status()
        return resp.json()

    def get_bulk_docs(self, url, db, doc_ids, auth=None, validate=True):
        """
        Keyword that issues POST _bulk_get docs with the specified 'docs' array.
        docs need to be in the following format:
        [
            'exp_3_0',
            'exp_3_1', ...
            ...
            'exp_3_100'
        ]
        """

        # Format the list of ids to the expected format for bulk_get
        # ex. [
        #   {'id', 'doc_id_one'},
        #   {'id', 'doc_id_two'}, ...
        # ]
        doc_ids_formatted = [{"id": doc_id} for doc_id in doc_ids]
        request_body = {"docs": doc_ids_formatted}

        auth_type = get_auth_type(auth)

        if auth_type == AuthType.session:
            resp = self._session.post("{}/{}/_bulk_get".format(url, db), data=json.dumps(request_body), cookies=dict(SyncGatewaySession=auth[1]))
        elif auth_type == AuthType.http_basic:
            resp = self._session.post("{}/{}/_bulk_get".format(url, db), data=json.dumps(request_body), auth=auth)
        else:
            resp = self._session.post("{}/{}/_bulk_get".format(url, db), data=json.dumps(request_body))

        log_r(resp)
        resp.raise_for_status()

        resp_obj = parse_multipart_response(resp.text)
        logging.debug(resp_obj)

        docs = []
        errors = []
        for row in resp_obj["rows"]:
            if "error" in row:
                errors.append(row)
            else:
                docs.append(row)

        if len(errors) > 0 and validate:
            raise RestError("_bulk_get recieved errors in the response!")

        return docs, errors

    def start_replication(self,
                          url,
                          continuous,
                          from_url=None, from_db=None, from_auth=None,
                          to_url=None, to_db=None, to_auth=None,
                          repl_filter=None,
                          doc_ids=None,
                          channels_filter=None):
        """
        Starts a replication (one-shot or continous) between Lite instances (P2P),
        Sync Gateways, or Lite <-> Sync Gateways

        :param url: endpoint to start the replication on
        :param continuous: True = continuous, False = one-shot
        :param from_url: source url of the replication
        :param from_db: source db of the replication
        :param from_auth: session header to provide to source
        :param to_url: target url of the replication
        :param to_db: target db of the replication
        :param to_auth: session header to provide to target
        :param repl_filter: ** Lite only ** Custom filter that can be defined in design doc
        :param doc_ids: ** Will not work with continuous pull from LITE <- SG ** Doc ids to filter
            replication by
        :param channels_filter: ** Only works with pull from Sync Gateway ** This will filter the
            replication by the array of string channel names
        """

        if from_url is None:
            source = from_db
        else:
            source = "{}/{}".format(from_url, from_db)

        if to_url is None:
            target = to_db
        else:
            target = "{}/{}".format(to_url, to_db)

        # The replication endpoint should support a value or dictionary for source / target keys
        if to_auth is None and from_auth is None:
            data = {
                "continuous": continuous,
                "source": source,
                "target": target
            }
        else:
            # Use dictionary format for source and target to provide authentication
            # for each enpoint in the source and target dictionary
            data = {
                "continuous": continuous,
                "source": {"url": source},
                "target": {"url": target}
            }

            if to_auth is not None:
                # Format session auth if it is passed in a tuple
                # ('SyncGatewaySession', 'e831f78d0baaa96472fa90ba7cad2d27abf7692a') ->
                #   SyncGatewaySession=e831f78d0baaa96472fa90ba7cad2d27abf7692a
                if len(to_auth) == 2:
                    to_auth = "{}={}".format(to_auth[0], to_auth[1])

                data["target"]["headers"] = {"Cookie": to_auth}

            if from_auth is not None:
                # Format session auth if it is passed in a tuple
                # ('SyncGatewaySession', 'e831f78d0baaa96472fa90ba7cad2d27abf7692a') ->
                #   SyncGatewaySession=e831f78d0baaa96472fa90ba7cad2d27abf7692a
                if len(from_auth) == 2:
                    from_auth = "{}={}".format(from_auth[0], from_auth[1])

                data["source"]["headers"] = {"Cookie": from_auth}

        if repl_filter is not None:
            data["filter"] = repl_filter

        if channels_filter is not None:
            data["filter"] = "sync_gateway/bychannel"
            data["query_params"] = {"channels": ",".join(channels_filter)}

        if doc_ids is not None:
            data["doc_ids"] = doc_ids

        resp = self._session.post("{}/_replicate".format(url), data=json.dumps(data))
        log_r(resp)
        resp.raise_for_status()
        resp_obj = resp.json()

        replication_id = resp_obj["session_id"]
        logging.info("Replication started with: {}".format(replication_id))

        return replication_id

    def stop_replication(self,
                         url,
                         continuous,
                         from_url=None, from_db=None, from_auth=None,
                         to_url=None, to_db=None, to_auth=None,
                         repl_filter=None,
                         doc_ids=None,
                         channels_filter=None):

        """
        Starts a replication (one-shot or continous) between Lite instances (P2P),
        Sync Gateways, or Lite <-> Sync Gateways

        :param url: endpoint to start the replication on
        :param continuous: True = continuous, False = one-shot
        :param from_url: source url of the replication
        :param from_db: source db of the replication
        :param from_auth: session header to provide to source
        :param to_url: target url of the replication
        :param to_db: target db of the replication
        :param to_auth: session header to provide to target
        :param repl_filter: ** Lite only ** Custom filter that can be defined in design doc
        :param doc_ids: ** Will not work with continuous pull from LITE <- SG ** Doc ids to filter
            replication by
        :param channels_filter: ** Only works with pull from Sync Gateway ** This will filter the
            replication by the array of string channel names
        """

        if from_url is None:
            source = from_db
        else:
            source = "{}/{}".format(from_url, from_db)

        if to_url is None:
            target = to_db
        else:
            target = "{}/{}".format(to_url, to_db)

        # The replication endpoint should support a value or dictionary for source / target keys
        if to_auth is None and from_auth is None:
            data = {
                "continuous": continuous,
                "cancel": True,
                "source": source,
                "target": target
            }
        else:
            # Use dictionary format for source and target to provide authentication
            # for each enpoint in the source and target dictionary
            data = {
                "continuous": continuous,
                "cancel": True,
                "source": {"url": source},
                "target": {"url": target}
            }

            if to_auth is not None:
                # Format session auth if it is passed in a tuple
                # ('SyncGatewaySession', 'e831f78d0baaa96472fa90ba7cad2d27abf7692a') ->
                #   SyncGatewaySession=e831f78d0baaa96472fa90ba7cad2d27abf7692a
                if len(to_auth) == 2:
                    to_auth = "{}={}".format(to_auth[0], to_auth[1])

                data["target"]["headers"] = {"Cookie": to_auth}

            if from_auth is not None:
                # Format session auth if it is passed in a tuple
                # ('SyncGatewaySession', 'e831f78d0baaa96472fa90ba7cad2d27abf7692a') ->
                #   SyncGatewaySession=e831f78d0baaa96472fa90ba7cad2d27abf7692a
                if len(from_auth) == 2:
                    from_auth = "{}={}".format(from_auth[0], from_auth[1])

                data["source"]["headers"] = {"Cookie": from_auth}

        if repl_filter is not None:
            data["filter"] = repl_filter

        if channels_filter is not None:
            data["filter"] = "sync_gateway/bychannel"
            data["query_params"] = {"channels": ",".join(channels_filter)}

        if doc_ids is not None:
            data["doc_ids"] = doc_ids

        resp = self._session.post("{}/_replicate".format(url), data=json.dumps(data))

        log_r(resp)
        resp.raise_for_status()

        resp_obj = resp.json()

        if "ok" not in resp_obj:
            raise AssertionError("Unexpected response for cancelling a replication")

    def wait_for_replication_status_idle(self, url, replication_id):
        """
        Polls the /_active_task endpoint and waits for a replication to become idle
        """

        start = time.time()
        while True:
            if time.time() - start > CLIENT_REQUEST_TIMEOUT:
                raise TimeoutException("Wait for Replication Status Idle: TIMEOUT")

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

            if replication_found and not replication_busy:
                logging.info("Replication is idle: {}".format(replication_id))
                break
            else:
                logging.info("Replication busy or not found. Retrying ...")
                time.sleep(1)

    def wait_for_no_replications(self, url):
        """
        Polls the /_active_task endpoint and wait for an empty array
        """
        start = time.time()
        while True:
            if time.time() - start > CLIENT_REQUEST_TIMEOUT:
                raise TimeoutException("Verify Docs Present: TIMEOUT")

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

    def get_replications(self, url):
        """
        Issues a GET on the /_active tasks endpoint and returns the response in the format below:
        """
        resp = self._session.get("{}/_active_tasks".format(url))
        resp.raise_for_status()
        log_r(resp)

        return resp.json()

    def verify_docs_present(self, url, db, expected_docs, auth=None, timeout=CLIENT_REQUEST_TIMEOUT, attachments=False):
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

            if attachments:
                expected_attachment_map = {expected_doc["id"]: expected_doc["attachments"] for expected_doc in expected_docs}
        elif isinstance(expected_docs, dict):
            # When expected docs is a single doc
            expected_doc_map = {expected_docs["id"]: expected_docs["rev"]}

            if attachments:
                expected_attachment_map = {expected_docs["id"]: expected_docs["attachments"]}
        else:
            raise TypeError("Verify Docs Preset expects a list or dict of expected docs")

        log_info("Verify {}/{} has {} docs".format(url, db, len(expected_doc_map)), is_verify=True)

        start = time.time()
        while True:

            if time.time() - start > timeout:
                raise TimeoutException("Verify Docs Present: TIMEOUT")

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
            all_attachments_returned = True
            missing_docs = []
            missing_attachment_docs = []
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

                if attachments and server_type == ServerType.listener:
                    # Check for an attachment
                    doc_id = resp_doc["key"]
                    doc_data = self._session.get("{}/{}/{}".format(url, db, doc_id))
                    doc_json = doc_data.json()

                    if "_attachments" not in doc_json and "id" in resp_doc and expected_attachment_map[resp_doc["id"]] != doc_json["_attachments"].keys():
                        all_attachments_returned = False
                        missing_attachment_docs.append(doc_id)

            logging.debug("Missing Docs = {}".format(missing_docs))
            log_info("Num found docs: {}".format(len(resp_obj["rows"]) - len(missing_docs)))
            log_info("Num missing docs: {}".format(len(missing_docs)))

            # Issue the request again, docs my still be replicating
            if not all_docs_returned:
                logging.info("Retrying to verify all docs are present ...")
                time.sleep(1)
                continue

            # Issue the request again, docs my still be replicating
            if attachments:
                log_info("Num missing attachment Docs = {}".format(len(missing_attachment_docs)))
                if not all_attachments_returned:
                    logging.info("Retrying to verify all attachments are present ...")
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

            if expected_doc_map != resp_docs:
                raise AssertionError("Unable to verify docs present. Dictionaries are not equal")

            break

    def stream_continuous_changes(self, url, db, since, auth, filter_type=None, filter_channels=None):
        """
        Issues a continuous changes feed request and returns the stream
        """
        auth_type = get_auth_type(auth)
        body = {
            "feed": "continuous",
            "since": since
        }

        if filter_type is not None:

            if filter_type == "sync_gateway/bychannel":
                if filter_channels is None:
                    raise RestError("channel filter need 'filter_channels' set")

                types.verify_is_list(filter_channels)
                body["filter"] = "sync_gateway/bychannel"
                body["channels"] = ",".join(filter_channels)

            else:
                raise RestError("Unsupported _changes filter_type: {}. Use 'sync_gateway/bychannel'.".format(
                    filter_type
                ))

        if auth_type == AuthType.session:
            resp = self._session.post("{}/{}/_changes".format(url, db), data=json.dumps(body), cookies=dict(SyncGatewaySession=auth[1]), stream=True)
        elif auth_type == AuthType.http_basic:
            resp = self._session.post("{}/{}/_changes".format(url, db), data=json.dumps(body), auth=auth, stream=True)
        else:
            resp = self._session.post("{}/{}/_changes".format(url, db), data=json.dumps(body), stream=True)

        return resp

    def get_changes(self, url, db, since, auth, feed="longpoll", timeout=60, limit=None, skip_user_docs=False, filter_type=None, filter_channels=None, filter_doc_ids=None):
        """
        Issues a longpoll changes request with a provided since and authentication.
        The timeout is in seconds.
        Returns a python dictionary of the changes response in the format:

        {u'last_seq': u'2', u'results': [{u'changes': [], u'id': u'_user/adam', u'seq': 2}]}
        """

        # Convert to ms for the sync_gateway REST api
        timeout *= 1000

        auth_type = get_auth_type(auth)
        server_type = self.get_server_type(url)

        if server_type == ServerType.listener:

            request_url = "{}/{}/_changes?feed={}&since={}".format(url, db, feed, since)
            if limit is not None:
                request_url += "&limit={}".format(limit)

            resp = self._session.get(request_url)

        elif server_type == ServerType.syncgateway:

            body = {
                "feed": feed,
                "since": since,
                "timeout": timeout
            }

            if limit is not None:
                body["limit"] = limit

            if filter_type is not None:

                if filter_type == "sync_gateway/bychannel":
                    if filter_channels is None:
                        raise RestError("channel filter need 'filter_channels' set")

                    types.verify_is_list(filter_channels)
                    body["filter"] = "sync_gateway/bychannel"
                    body["channels"] = ",".join(filter_channels)

                elif filter_type == "_doc_ids":

                    if feed != "normal":
                        raise RestError("'_doc_ids' filter only works with feed=normal")

                    if filter_doc_ids is None:
                        raise RestError("channel filter need 'filter_channels' set")

                    types.verify_is_list(filter_doc_ids)
                    body["filter"] = "_doc_ids"
                    body["doc_ids"] = filter_doc_ids

                else:
                    raise RestError("Unsupported _changes filter_type: {}. Use 'sync_gateway/bychannel' or '_doc_ids'.".format(
                        filter_type
                    ))

            log_info("Using POST data: {}".format(body))

            if auth_type == AuthType.session:
                resp = self._session.post("{}/{}/_changes".format(url, db), data=json.dumps(body), cookies=dict(SyncGatewaySession=auth[1]))
            elif auth_type == AuthType.http_basic:
                resp = self._session.post("{}/{}/_changes".format(url, db), data=json.dumps(body), auth=auth)
            else:
                resp = self._session.post("{}/{}/_changes".format(url, db), data=json.dumps(body))

        log_r(resp)
        resp.raise_for_status()
        resp_obj = resp.json()

        if skip_user_docs:
            # filter out any changes with _user/* doc id
            log_info("Returning changes without '_user/*' docs")
            results_without_user_docs = [
                result for result in resp_obj["results"]
                if not result["id"].startswith("_user/")
            ]
            # assign return value the th stripped list
            resp_obj["results"] = results_without_user_docs

        log_info("Found {} changes".format(len(resp_obj["results"])))
        return resp_obj

    def verify_doc_id_in_changes(self, url, db, expected_doc_id, auth=None):
        """ Verifies 'expected_doc_id' shows up in the changes feed starting with a since of 0
        if the doc is not found before CLIENT_REQUEST_TIMEOUT, an exception is raised. If it is found,
        return the last sequence that includes the doc
        """

        start = time.time()

        last_seq = 0
        while True:

            if time.time() - start > CLIENT_REQUEST_TIMEOUT:
                raise TimeoutException("Verify Docs In Changes: TIMEOUT")

            resp_obj = self.get_changes(url=url, db=db, since=last_seq, auth=auth)
            doc_ids_in_changes = [change["id"] for change in resp_obj["results"]]

            if expected_doc_id in doc_ids_in_changes:
                last_seq = resp_obj["last_seq"]
                log_info("{} found at last_seq: {}".format(expected_doc_id, last_seq))
                return last_seq
            else:
                log_info("'{}' not found retrying ...".format(expected_doc_id))
                time.sleep(1)

    def verify_is_user_doc(self, doc):
        """
        Verify that a doc is a _user/ doc
        """

        if not doc["id"].startswith("_user/"):
            raise ValueError("User doc should have the prefix '_user'")
        if doc["changes"]:
            raise ValueError("User doc should have empty changes always")
        if "rev" in doc:
            raise ValueError("User doc should not have a rev")

    def verify_docs_in_changes(self, url, db, expected_docs, auth=None, strict=False, polling_interval=60):
        """
        Verifies the expected docs are present in the database _changes feed using longpoll in a loop with
        Uses a GET _changes?feed=longpoll&since=last_seq for Listener
        and POST _changes with a body {"feed": "longpoll", "since": last_seq} for sync_gateway

        expected_docs should be a dict {id: {rev: ""}} or
        a list of {id: {rev: ""}}. If the expected docs are a list, they will be converted to a single map.

        If strict = True, fail if any docs other that the expected docs are found while validating
        """

        if isinstance(expected_docs, list):
            # Create single dictionary for comparison, will also blow up for duplicate docs with the same id
            expected_doc_map = {expected_doc["id"]: expected_doc["rev"] for expected_doc in expected_docs}
        elif isinstance(expected_docs, dict):
            # When expected docs is a single doc
            expected_doc_map = {expected_docs["id"]: expected_docs["rev"]}
        else:
            raise TypeError("Verify Docs In Changes expects a list or dict of expected docs")

        log_info("Verify {}/{} has {} docs in changes".format(url, db, len(expected_doc_map)), is_verify=True)

        sequence_number_map = {}

        start = time.time()
        last_seq = 0

        while True:
            logging.info(time.time() - start)

            if time.time() - start > CLIENT_REQUEST_TIMEOUT:
                raise TimeoutException("Verify Docs In Changes: TIMEOUT")

            resp_obj = self.get_changes(url=url, db=db, since=last_seq, auth=auth, timeout=polling_interval)

            missing_expected_docs = []
            for resp_doc in resp_obj["results"]:

                # Check changes results contain a doc in the expected docs
                if resp_doc["id"] in expected_doc_map:

                    assert resp_doc["seq"] not in sequence_number_map, "Found duplicate sequence number: {} in sequence map!!".format(resp_doc["seq"])
                    sequence_number_map[resp_doc["seq"]] = resp_doc["id"]

                    # If the doc is a user doc, there will be no rev, cross it out
                    if resp_doc["id"].startswith("_user/"):
                        self.verify_is_user_doc(resp_doc)
                        del expected_doc_map[resp_doc["id"]]

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

            if strict and len(missing_expected_docs) > 0:
                log_info("Found doc id not in the expected_docs: {}".format(missing_expected_docs))
                raise ChangesError("Found unexpected docs in changes feed: {}".format(missing_expected_docs))

            log_info("Missing expected docs: {}".format(len(expected_doc_map)))
            log_debug("Sequence number map: {}".format(sequence_number_map))

            if len(expected_doc_map) == 0:
                # All expected docs have been crossed out
                break

            # update last sequence and continue
            last_seq = resp_obj["last_seq"]
            log_info("last_seq: {}".format(last_seq))

            time.sleep(1)

    def add_design_doc(self, url, db, name, doc):
        """
        Keyword that adds a Design Doc to the database
        """
        resp = self._session.put("{}/{}/_design/{}".format(url, db, name), data=doc)
        log_r(resp)
        resp.raise_for_status()

        # Only return a response if adding to the listener
        # Sync Gateway does not return a response
        if self.get_server_type(url) == ServerType.listener:
            resp_obj = resp.json()
            return resp_obj["id"]

    def get_design_doc_rev(self, url, db, name):
        """
        Keyword that gets a Design Doc revision
        """
        resp = self._session.get("{}/{}/_design/{}".format(url, db, name))
        log_r(resp)
        resp.raise_for_status()

        # Only return a response if adding to the listener
        # Sync Gateway does not return a response
        if self.get_server_type(url) == ServerType.listener:
            resp_obj = resp.json()
            return resp_obj["_rev"]

    def update_design_doc(self, url, db, name, doc, rev):
        """
        Keyword that updates a Design Doc to the database
        """
        resp = self._session.put("{}/{}/_design/{}?rev={}".format(url, db, name, rev), data=doc)
        log_r(resp)
        resp.raise_for_status()

        # Only return a response if adding to the listener
        # Sync Gateway does not return a response
        if self.get_server_type(url) == ServerType.listener:
            resp_obj = resp.json()
            return resp_obj["id"]

    def get_view(self, url, db, design_doc_name, view_name, auth=None):
        """
        Keyword that returns a view query for a design doc with a view name
        """

        auth_type = get_auth_type(auth)
        server_type = self.get_server_type(url)

        url = "{}/{}/_design/{}/_view/{}".format(url, db, design_doc_name, view_name)
        params = {}

        if server_type == ServerType.syncgateway:
            params["stale"] = "false"

        max_retries = 5
        count = 0
        while True:

            if count == max_retries:
                raise RestError("Could not get view after retries!")

            try:
                if auth_type == AuthType.session:
                    resp = self._session.get(url, params=params, cookies=dict(SyncGatewaySession=auth[1]))
                    log_r(resp)
                    resp.raise_for_status()
                    break
                elif auth_type == AuthType.http_basic:
                    resp = self._session.get(url, params=params, auth=auth)
                    log_r(resp)
                    resp.raise_for_status()
                    break
                else:
                    resp = self._session.get(url, params=params)
                    log_r(resp)
                    resp.raise_for_status()
                    break
            except HTTPError as he:
                # It is possible that the view is not inialized.
                # The server will return 500 in this case, handle this with a few retries.
                log_info("Failed to get view: {}".format(he))
                if he.response.status_code == 500:
                    time.sleep(1)
                    count += 1
                else:
                    # Reraise the exception is it is not what we are expecting
                    raise

        return resp.json()

    def verify_view_row_num(self, view_response, expected_num_rows):
        """
        Keyword that verifies the length of rows return from a view is the expected number of rows
        """
        num_row_entries = len(view_response["rows"])
        num_total_rows = view_response["total_rows"]
        log_info("Expected rows: {}".format(expected_num_rows), is_verify=True)
        log_info("Number of row entries: {}".format(num_row_entries), is_verify=True)
        log_info("Number of total_rows: {}".format(num_total_rows), is_verify=True)
        if num_row_entries != expected_num_rows:
            raise AssertionError("Expected number of rows did not match number of 'rows'")

        if num_row_entries != num_total_rows:
            raise AssertionError("Expected number of rows did not match number of 'total_rows'")

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

    def verify_doc_ids_found_in_response(self, response, expected_doc_ids):
        """ Verifies that list of doc ids are in the response.
         'response' expected format:
        [
            {u'channels': [u'NBC', u'ABC'], u'_rev': u'1-efda114d144b5220fa77c4e51f3e70a8', u'_id': u'exp_10_0'},
            {u'channels': [u'NBC', u'ABC'], u'_rev': u'1-efda114d144b5220fa77c4e51f3e70a8', u'_id': u'exp_10_1'},
            {u'channels': [u'NBC', u'ABC'], u'_rev': u'1-efda114d144b5220fa77c4e51f3e70a8', u'_id': u'exp_10_2'} ...
        ]
        """

        found_doc_ids = []
        for doc in response:
            if "error" not in doc:
                # doc was found
                found_doc_ids.append(doc["_id"])

        logging.debug("Found Doc Ids: {}".format(found_doc_ids))
        logging.debug("Expected Doc Ids: {}".format(expected_doc_ids))
        if found_doc_ids != expected_doc_ids:
            raise AssertionError("Found doc ids should be the same as expected doc ids")

    def verify_doc_ids_not_found_in_response(self, response, expected_missing_doc_ids):
        """ Verifies that list of doc ids are not present on sync gateway.
         'response' expected format:
        [
            {u'channels': [u'NBC', u'ABC'], u'_rev': u'1-efda114d144b5220fa77c4e51f3e70a8', u'_id': u'exp_10_0'},
            {u'channels': [u'NBC', u'ABC'], u'_rev': u'1-efda114d144b5220fa77c4e51f3e70a8', u'_id': u'exp_10_1'},
            {u'channels': [u'NBC', u'ABC'], u'_rev': u'1-efda114d144b5220fa77c4e51f3e70a8', u'_id': u'exp_10_2'} ...
        ]
        """

        missing_doc_ids = []
        for doc in response:
            if "error" in doc:
                # missing doc was found
                missing_doc_ids.append(doc["id"])

        logging.debug("Found Doc Ids: {}".format(missing_doc_ids))
        logging.debug("Expected Doc Ids: {}".format(expected_missing_doc_ids))
        if missing_doc_ids != expected_missing_doc_ids:
            raise AssertionError("Found doc ids should be the same as expected doc ids")

    def get_expvars(self, url):
        """ Gets expvars for the url """
        resp = self._session.get("{}/_expvar".format(url))
        log_r(resp)
        resp.raise_for_status()

        return resp.json()

    def take_db_offline(self, cluster_conf, db):
        # Take bucket offline
        ansible_runner = AnsibleRunner(cluster_conf)
        status = ansible_runner.run_ansible_playbook(
            "sync-gateway-db-offline.yml",
            extra_vars={
                "db": db
            }
        )

        return status

    def bring_db_online(self, cluster_conf, db, delay=0):
        # Bring db online
        ansible_runner = AnsibleRunner(cluster_conf)
        status = ansible_runner.run_ansible_playbook(
            "sync-gateway-db-online.yml",
            extra_vars={
                "db": db,
                "delay": delay
            }
        )

        return status

    def get_changes_style_all_docs(self, url, db, auth=None, include_docs=False):
        """ Get all changes with include docs enabled and style all_docs """
        auth_type = get_auth_type(auth)

        params = {}
        if include_docs:
            params["include_docs"] = "true"
            params["style"] = "all_docs"

        if auth_type == AuthType.session:
            resp = self._session.get("{}/{}/_changes".format(url, db), params=params, cookies=dict(SyncGatewaySession=auth[1]))
        elif auth_type == AuthType.http_basic:
            resp = self._session.get("{}/{}/_changes".format(url, db), params=params, auth=auth)
        else:
            resp = self._session.get("{}/{}/_changes".format(url, db), params=params)

        log_r(resp)
        resp.raise_for_status()
        resp_obj = resp.json()
        return resp_obj
