import requests
import json
import concurrent.futures

from lib.user import User
from lib.scenarioprinter import ScenarioPrinter
from lib import settings

import logging
log = logging.getLogger(settings.LOGGER)

class Admin:

    def __init__(self, sync_gateway):
        self.admin_url = "http://{}:4985".format(sync_gateway.ip)
        self.users = {}

        self._printer = ScenarioPrinter()

        self._headers = {"Content-Type": "application/json"}

    def get_db_info(self, db):
        resp = requests.get("{0}/{1}/".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT)
        log.info(resp.url)
        resp.raise_for_status()
        return resp.json()

    # PUT /{db}/_role/{name}
    def create_role(self, db, name, channels):
        data = {"name": name, "admin_channels": channels}
        resp = requests.put("{0}/{1}/_role/{2}".format(self.admin_url, db, name), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(data))
        log.info(resp.url)
        resp.raise_for_status()

    # GET /{db}/_role
    def get_roles(self, db):
        resp = requests.get("{0}/{1}/_role/".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT)
        log.info(resp.url)
        resp.raise_for_status()
        return resp.json()

    # GET /{db}/_role/{name}
    def get_role(self, db, name):
        resp = requests.get("{0}/{1}/_role/{2}".format(self.admin_url, db, name), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT)
        log.info(resp.url)
        resp.raise_for_status()
        return resp.json()

    # PUT /{db}/_user/{name}
    def register_user(self, target, db, name, password, channels=list(), roles=list()):

        data = {"name": name, "password": password, "admin_channels": channels, "admin_roles": roles}

        resp = requests.put("{0}/{1}/_user/{2}".format(self.admin_url, db, name), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(data))

        print(resp.status_code)

        log.info(resp.url)
        resp.raise_for_status()

        self._printer.print_user_add()

        return User(target, db, name, password, channels)

    def register_bulk_users(self, target, db, name_prefix, number, password, channels=list(), roles=list()):

        if type(channels) is not list:
            raise("Channels needs to be a list")

        users = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=settings.MAX_REQUEST_WORKERS) as executor:
            futures = [executor.submit(self.register_user, target=target, db=db, name="{}_{}".format(name_prefix, i), password=password, channels=channels, roles=roles) for i in range(number)]
            for future in concurrent.futures.as_completed(futures):
                try:
                    user = future.result()
                    users.append(user)
                except Exception as e:
                    raise("register_bulk_users failed: {}".format(e))

        if len(users) != number:
            raise("Not all users added during register_bulk users")

        return users

    # GET /{db}/_user/
    def get_users_info(self, db):
        resp = requests.get("{0}/{1}/_user/".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT)
        log.info(resp.url)
        resp.raise_for_status()
        return resp.json()

    # GET /{db}/_user/{name}
    def get_user_info(self, db, name):
        resp = requests.get("{0}/{1}/_user/{2}".format(self.admin_url, db, name), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT)
        log.info(resp.url)
        resp.raise_for_status()
        return resp.json()

    def db_resync(self, db):
        pass

    def db_online(self, db, delay=None):

        data = {}
        if delay is not None:
            data = {"delay": delay}

        resp = requests.post("{0}/{1}/_online".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(data))
        log.info(resp.url)
        resp.raise_for_status()
        print(resp.text)

    def db_offline(self, db):
        resp = requests.post("{0}/{1}/_offline".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT)
        resp.raise_for_status()
        print(resp.text)

    def get_db_status(self, db):
        resp = requests.get("{0}/{1}".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT)
        log.info(resp.url)
        resp.raise_for_status()
        print(resp.text)

    def get_db_config(self, db):
        resp = requests.get("{0}/{1}/_config".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT)
        log.info(resp.url)
        resp.raise_for_status()
        print(resp.text)

    def put_config(self, db, config_name):

        # sample_conf = {
        #     "server": "http://localhost:8091",
        #     "bucket": "bucket-1",
        #     "users": {
        #         "GUEST": {
        #             "disabled": False,
        #             "admin_channels": ["*"]
        #         }
        #     }
        # }

        resp = requests.put("{0}/{1}".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(config))
        log.info(resp.url)
        resp.raise_for_status()
        print(resp.text)

