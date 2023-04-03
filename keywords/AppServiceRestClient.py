import logging
import json
import time
import uuid
import re

from requests import Session
from keywords.constants import AuthType
from keywords.utils import log_r

from requests.auth import HTTPBasicAuth

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
        self._session.verify = False

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