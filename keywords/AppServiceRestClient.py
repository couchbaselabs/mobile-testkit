import logging
import json
import uuid

from libraries.data import doc_generators

from keywords import types
from keywords.utils import log_info
from keywords.utils import log_r

from keywords.exceptions import RestError
from requests import Session
from keywords.constants import AuthType


from requests.auth import HTTPBasicAuth


def parse_multipart_response(response):

    rows = []

    for part in response.split("--"):

        part_lines = part.splitlines()
        if part_lines and len(part_lines) > 2:
            doc = part_lines[-1]
            try:
                doc_obj = json.loads(doc)
                rows.append(doc_obj)
            except Exception as e:
                # A few lines from the response can't be parsed as docs
                logging.error("Could not parse docs as JSON: {} error: {}".format(doc, e))

    return {"rows": rows}


def get_auth(username, password):

    auth_type = AuthType.http_basic
    auth = HTTPBasicAuth(username, password)
    return auth_type, auth


def get_auth_type(auth):

    auth_type = AuthType.http_basic
    auth = HTTPBasicAuth(auth[0], auth[1])

    logging.info("Using auth type: {}".format(auth_type))
    return auth_type, auth


class MyEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, (bytes, bytearray)):
            return obj.decode("ASCII")
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


class AppServiceRestClient:

    def __init__(self):

        headers = {"Content-Type": "application/json"}
        self._session = Session()
        self._session.headers = headers
        self._session.verify = False

    def merge(self, *doc_lists):

        merged_list = []
        for doc_list in doc_lists:
            merged_list.extend(doc_list)
        return merged_list

    def get_all_docs(self, url, auth, include_docs=False):

        auth_type, auth = get_auth_type(auth)
        params = {}
        if include_docs:
            params["include_docs"] = "true"
        all_docs_url = "{}/_all_docs".format(url)
        resp = self._session.get(all_docs_url, params=params, auth=auth)
        log_r(resp)
        resp.raise_for_status()
        return resp.json()

    def doc_with_id(self, url, auth, doc_id):

        auth_type, auth = get_auth_type(auth)
        params = {}
        all_docs_url = "{}/{}".format(url, doc_id)
        resp = self._session.get(all_docs_url, params=params, auth=auth)
        log_r(resp)
        resp.raise_for_status()
        return resp.json()

    def get_bulk_docs(self, url, doc_ids, auth, validate=True, revs_history="false"):

        auth_type, auth = get_auth_type(auth)
        doc_ids_formatted = [{"id": doc_id} for doc_id in doc_ids]
        request_body = {"docs": doc_ids_formatted}
        resp = self._session.post("{}/_bulk_get?revs={}".format(url, revs_history), data=json.dumps(request_body), auth=auth)
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
            raise RestError("_bulk_get recieved errors in the response!{}".format(str(errors)))

        return docs, errors

    def add_bulk_docs(self, url, docs, auth):

        auth_type, auth = get_auth_type(auth)
        request_body = {"docs": docs}
        resp = self._session.post("{}/_bulk_docs".format(url), data=json.dumps(request_body), auth=auth)
        log_r(resp)
        resp.raise_for_status()
        resp_obj = resp.json()

        for doc_resp in resp_obj:
            if "error" in doc_resp:
                raise RestError("Error while adding bulk docs!")

        return resp_obj

    def add_doc(self, url, doc, auth):
        logging.info(auth)

        doc["updates"] = 0
        resp = self._session.post("{}/".format(url), data=json.dumps(doc, cls=MyEncoder), auth=auth)

        log_r(resp)
        resp.raise_for_status()
        resp_obj = resp.json()

        return resp_obj

    def add_docs(self, url, number, id_prefix, auth, channels=None, generator=None, attachments_generator=None, expiry=None):
        auth_type, auth = get_auth_type(auth)
        added_docs = []

        if channels is not None:
            types.verify_is_list(channels)

        log_info("PUT {} docs to {}/ with prefix {}".format(number, url, id_prefix))
        for i in range(number):

            if generator == "four_k":
                doc_body = doc_generators.four_k()
            elif generator == "simple_user":
                doc_body = doc_generators.simple_user()
            else:
                doc_body = doc_generators.simple()

            if channels is not None:
                doc_body["channels"] = channels

            if attachments_generator:
                types.verify_is_callable(attachments_generator)
                attachments = attachments_generator()
                doc_body["_attachments"] = {att.name: {"data": att.data} for att in attachments}
            if expiry is not None:
                doc_body["_exp"] = expiry

            if id_prefix is None:
                doc_id = str(uuid.uuid4())
            else:
                doc_id = "{}_{}".format(id_prefix, i)

            doc_body["_id"] = doc_id
            doc_obj = self.add_doc(url, doc_body, auth)
            if attachments_generator:
                doc_obj["attachments"] = list(doc_body["_attachments"].keys())
            added_docs.append(doc_obj)

        if len(added_docs) != number:
            raise AssertionError("Client was not able to add all docs to: {}".format(url))

        log_info("Added: {} docs".format(len(added_docs)))

        return added_docs
