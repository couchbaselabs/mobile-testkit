import logging
import json

import requests
from requests import Session
from requests.exceptions import HTTPError

from robot.api.logger import console

def log_r(request):
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

    def start_push_pull_replication(self, url, continuous, source_url, source_db, target_url, target_db):
        self.start_push_replication(url, continuous, source_url, source_db, target_url, target_db)
        #self.start_pull_replication(url, continuous, source_url, source_db, target_url, target_db)

    def start_push_replication(self, url, continuous, source_url, source_db, target_url, target_db):

        console(url)
        console(continuous)
        console(source_url)
        console(source_db)
        console(target_url)
        console(target_db)

        data = {
            #"continuous": continuous,
            "source": "{}".format(source_db),
            "target": "{}/{}".format(target_url, target_db)
        }
        resp = self._session.post("{}/_replicate".format(url), data=json.dumps(data))
        log_r(resp)
        resp.raise_for_status()

    # def start_pull_replication(self, url, continuous, source_url, source_db, target_url, target_db):
    #     data = {
    #         "continuous": "true",
    #         "source": "{}/{}".format(target_url, target_db),
    #         "target": "{}".format(source_db)
    #     }
    #     resp = self._session.post("{}/_replicate".format(url), data=json.dumps(data))
    #     log_r(resp)
    #     resp.raise_for_status()