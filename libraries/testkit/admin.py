import requests
import json
import concurrent.futures

from libraries.testkit.user import User
from libraries.testkit import settings
from libraries.testkit.debug import log_request
from libraries.testkit.debug import log_response

import logging
log = logging.getLogger(settings.LOGGER)


class Admin:

    def __init__(self, sync_gateway):
        self.admin_url = "http://{}:4985".format(sync_gateway.ip)
        self.users = {}
        self._headers = {"Content-Type": "application/json"}

    def create_db(self, name):
        r = requests.put("{}/{}".format(self.admin_url, name))
        log_request(r)
        log_response(r)
        r.raise_for_status()
        return r.json()

    def delete_db(self, name):
        r = requests.delete("{}/{}".format(self.admin_url, name))
        log_request(r)
        log_response(r)
        r.raise_for_status()
        return r.json()

    def get_dbs(self):
        r = requests.get("{}/_all_dbs".format(self.admin_url))
        log.info("GET {}".format(r.url))
        r.raise_for_status()
        return r.json()

    # GET /{db}/
    def get_db_info(self, db):
        resp = requests.get("{0}/{1}/".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # PUT /{db}/_role/{name}
    def create_role(self, db, name, channels):
        data = {"name": name, "admin_channels": channels}
        resp = requests.put("{0}/{1}/_role/{2}".format(self.admin_url, db, name), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(data))
        log.info("PUT {}".format(resp.url))
        resp.raise_for_status()

    # GET /{db}/_role
    def get_roles(self, db):
        resp = requests.get("{0}/{1}/_role/".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # GET /{db}/_role/{name}
    def get_role(self, db, name):
        resp = requests.get("{0}/{1}/_role/{2}".format(self.admin_url, db, name), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # PUT /{db}/_user/{name}
    def register_user(self, target, db, name, password, channels=list(), roles=list()):

        data = {"name": name, "password": password, "admin_channels": channels, "admin_roles": roles}

        resp = requests.put("{0}/{1}/_user/{2}".format(self.admin_url, db, name), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(data))
        log.info("PUT {}".format(resp.url))
        resp.raise_for_status()

        return User(target, db, name, password, channels)

    def register_bulk_users(self, target, db, name_prefix, number, password, channels=list(), roles=list()):

        if type(channels) is not list:
            raise ValueError("Channels needs to be a list")

        users = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=settings.MAX_REQUEST_WORKERS) as executor:
            futures = [executor.submit(self.register_user, target=target, db=db, name="{}_{}".format(name_prefix, i), password=password, channels=channels, roles=roles) for i in range(number)]
            for future in concurrent.futures.as_completed(futures):
                try:
                    user = future.result()
                    users.append(user)
                except Exception as e:
                    raise ValueError("register_bulk_users failed: {}".format(e))

        if len(users) != number:
            raise ValueError("Not all users added during register_bulk users")

        return users

    # GET /{db}/_user/
    def get_users_info(self, db):
        resp = requests.get("{0}/{1}/_user/".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # GET /{db}/_user/{name}
    def get_user_info(self, db, name):
        resp = requests.get("{0}/{1}/_user/{2}".format(self.admin_url, db, name), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # POST /{db}/_resync
    def db_resync(self, db):
        result = dict()
        resp = requests.post("{0}/{1}/_resync".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT)
        log.info("POST {}".format(resp.url))
        resp.raise_for_status()
        result['status_code'] = resp.status_code
        result['payload'] = resp.json()
        return result

    # POST /{db}/_online
    def bring_db_online(self, db, delay=None):
        data = {}
        if delay is not None:
            data = {"delay": delay}

        resp = requests.post("{0}/{1}/_online".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(data))
        log.info("POST {}".format(resp.url))
        resp.raise_for_status()
        return resp.status_code

    # POST /{db}/_offline
    def take_db_offline(self, db):
        resp = requests.post("{0}/{1}/_offline".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT)
        log.info("POST {}".format(resp.url))
        resp.raise_for_status()
        return resp.status_code

    # GET /{db}/_config
    def get_db_config(self, db):
        resp = requests.get("{0}/{1}/_config".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # PUT /{db}/_config
    def put_db_config(self, db, config):
        resp = requests.put("{0}/{1}/_config".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(config))
        log.info("PUT {}".format(resp.url))
        resp.raise_for_status()
        return resp.status_code

    # GET /_cbgt/api/cfg
    def get_cbgt_cfg(self):
        resp = requests.get("{0}/_cbgt/api/cfg".format(self.admin_url), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # GET /_cbgt/api/diag
    def get_cbgt_diagnostics(self):
        resp = requests.get("{0}/_cbgt/api/diag".format(self.admin_url), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # GET /{db}/_changes
    def get_global_changes(self, db):
        r = requests.get("{}/{}/_changes".format(self.admin_url, db))
        log_request(r)
        log_response(r)
        r.raise_for_status()
        resp_data = r.json()
        return resp_data["results"]

    # GET /_active_tasks
    def get_active_tasks(self):
        r = requests.get("{}/_active_tasks".format(self.admin_url))
        log_request(r)
        log_response(r)
        r.raise_for_status()
        resp_data = r.json()
        return resp_data

    def get_all_docs(self, db):
        resp = requests.get("{0}/{1}/_all_docs".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()
