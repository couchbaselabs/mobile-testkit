import logging
import json
import time
import requests
from requests import Session
from requests.exceptions import HTTPError

from robot.api.logger import console

from libraries.data.generators import *
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
        if part_lines:
            doc = part_lines[-1]
            try:
                doc_obj = json.loads(doc)
                rows.append(doc_obj)
            except Exception as e:
                # A few lines from the response can't be parsed as docs
                logging.debug("doc_obj: {} e: {}".format(doc_obj, e))

    return {"rows": rows}

class TKClient:

    def __init__(self):
        headers = {"Content-Type": "application/json"}
        self._session = Session()
        self._session.headers = headers

    def create_database(self, url, name, listener=False):

        if listener:
            resp = self._session.put("{}/{}/".format(url, name))
        else:
            data = {
                "name": "{}".format(name),
                "server": "walrus:",
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

    def verify_docs_present(self, url, db, expected_docs, listener=False):
        """
        Verifies that the docs passed in the function exist in the database
        """

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

            if listener:

                data = {"keys": expected_doc_map.keys()}
                resp = self._session.post("{}/{}/_all_docs".format(url, db), data=json.dumps(data))
                log_r(resp)
                resp.raise_for_status()
                resp_obj = resp.json()

            else:

                # Constuct _bulk_get body
                bulk_get_body_id_list = []
                for key in expected_doc_map.keys():
                    bulk_get_body_id_list.append({"id": key})
                bulk_get_body = {"docs": bulk_get_body_id_list}

                resp = self._session.post("{}/{}/_bulk_get".format(url, db), data=json.dumps(bulk_get_body))
                log_r(resp)
                resp.raise_for_status()

                resp_obj = parse_multipart_response(resp.text)

            # See any docs were not retureed
            all_docs_returned = True
            missing_docs = []
            for resp_doc in resp_obj["rows"]:
                if "error" in resp_doc:
                    missing_docs.append(resp_doc)
                    all_docs_returned = False

            # Issue the request again, docs my still be replicating
            if not all_docs_returned:
                logging.info("Not all docs present. Retrying")
                logging.info(missing_docs)
                time.sleep(1)
                continue

            resp_docs = {}
            for resp_doc in resp_obj["rows"]:
                if listener:
                    resp_docs[resp_doc["id"]] = { "rev": resp_doc["value"]["rev"] }
                else:
                    resp_docs[resp_doc["_id"]] = {"rev": resp_doc["_rev"]}

            assert(expected_doc_map == resp_docs), "Unable to verify docs present. Dictionaries are not equal"
            break

    def verify_docs_in_changes(self, url, db, expected_docs, listener=False):

        if isinstance(expected_docs, list):
            # Create single dictionary for comparison
            expected_doc_map = {k: v for expected_doc_dict in expected_docs for k, v in expected_doc_dict.iteritems()}
        elif isinstance(expected_docs, dict):
            expected_doc_map = expected_docs
        else:
            raise TypeError("Verify Docs Preset expects a list or dict of expected docs")

        start = time.time()
        last_seq = 0
        while True:

            if time.time() - start > CLIENT_REQUEST_TIMEOUT:
                raise Exception("Verify Docs In Changes: TIMEOUT")

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

            logging.debug("Missing docs: {}".format(expected_doc_map))

            if len(expected_doc_map) == 0:
                # All expected docs have been crossed out
                break

            # update last sequence and continue
            last_seq = resp_obj["last_seq"]
            logging.debug(last_seq)

            time.sleep(1)





