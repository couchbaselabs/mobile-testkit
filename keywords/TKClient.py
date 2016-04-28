import logging
import json
import time
import requests
from requests import Session
from requests.exceptions import HTTPError

from robot.api.logger import console

from libraries.data.generators import *

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

        docs = []

        for i in xrange(number):

            doc_body = generator
            resp = self._session.put("{}/{}/{}_{}".format(url, db, id_prefix, i), data=doc_body)
            log_r(resp)
            resp.raise_for_status()

            doc_obj = resp.json()
            doc = {
                "id": doc_obj["id"],
                "rev": doc_obj["rev"]
            }
            docs.append(doc)

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
