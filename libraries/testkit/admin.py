import requests
import json
import concurrent.futures
import os
import time

from libraries.testkit.user import User
from libraries.testkit import settings
from libraries.testkit.debug import log_request
from libraries.testkit.debug import log_response
from keywords import cbgtconfig
from utilities.cluster_config_utils import sg_ssl_enabled
from requests.exceptions import HTTPError

import logging
log = logging.getLogger(settings.LOGGER)


class Admin:

    def __init__(self, sync_gateway):
        sg_scheme = "http"

        cluster_config = os.environ["CLUSTER_CONFIG"]
        if sg_ssl_enabled(cluster_config):
            sg_scheme = "https"

        self.admin_url = "{}://{}:4985".format(sg_scheme, sync_gateway.ip)
        self.users = {}
        self._headers = {"Content-Type": "application/json"}

    def create_db(self, name):
        r = requests.put("{}/{}".format(self.admin_url, name), verify=False)
        log_request(r)
        log_response(r)
        r.raise_for_status()
        return r.json()

    def delete_db(self, name):
        r = requests.delete("{}/{}".format(self.admin_url, name), verify=False)
        log_request(r)
        log_response(r)
        r.raise_for_status()
        return r.json()

    def get_dbs(self):
        r = requests.get("{}/_all_dbs".format(self.admin_url), verify=False)
        log.info("GET {}".format(r.url))
        r.raise_for_status()
        return r.json()

    # GET /{db}/
    def get_db_info(self, db):
        resp = requests.get("{0}/{1}/".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # PUT /{db}/_role/{name}
    def create_role(self, db, name, channels):
        data = {"name": name, "admin_channels": channels}
        resp = requests.put("{0}/{1}/_role/{2}".format(self.admin_url, db, name), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(data), verify=False)
        log.info("PUT {}".format(resp.url))
        resp.raise_for_status()

    # GET /{db}/_role
    def get_roles(self, db):
        resp = requests.get("{0}/{1}/_role/".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # GET /{db}/_role/{name}
    def get_role(self, db, name):
        resp = requests.get("{0}/{1}/_role/{2}".format(self.admin_url, db, name), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # PUT /{db}/_user/{name}
    def register_user(self, target, db, name, password, channels=list(), roles=list()):

        data = {"name": name, "password": password, "admin_channels": channels, "admin_roles": roles}

        resp = requests.put("{0}/{1}/_user/{2}".format(self.admin_url, db, name), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(data), verify=False)
        log.info("PUT {}".format(resp.url))
        resp.raise_for_status()

        return User(target, db, name, password, channels)

    def register_bulk_users(self, target, db, name_prefix, number, password, channels=list(), roles=list(), num_of_workers=settings.MAX_REQUEST_WORKERS):

        if type(channels) is not list:
            raise ValueError("Channels needs to be a list")

        users = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_of_workers) as executor:
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
        resp = requests.get("{0}/{1}/_user/".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # GET /{db}/_user/{name}
    def get_user_info(self, db, name):
        resp = requests.get("{0}/{1}/_user/{2}".format(self.admin_url, db, name), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # POST /{db}/_resync
    def db_resync(self, db):
        result = dict()
        resp = requests.post("{0}/{1}/_resync".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
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

        resp = requests.post("{0}/{1}/_online".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(data), verify=False)
        log.info("POST {}".format(resp.url))
        resp.raise_for_status()
        return resp.status_code

    # POST /{db}/_offline
    def take_db_offline(self, db):
        resp = requests.post("{0}/{1}/_offline".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
        log.info("POST {}".format(resp.url))
        resp.raise_for_status()
        return resp.status_code

    # GET /{db}/_config
    def get_db_config(self, db):
        resp = requests.get("{0}/{1}/_config".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # PUT /{db}/_config
    def put_db_config(self, db, config):
        resp = requests.put("{0}/{1}/_config".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(config), verify=False)
        log.info("PUT {}".format(resp.url))
        resp.raise_for_status()
        return resp.status_code

    # GET /_cbgt/api/cfg
    def get_cbgt_config(self):
        """ Get the REST cfg response from an accel node.
        Return an CbgtConfig object that exposes common methods useful in validation"""

        resp = requests.get("{0}/_cbgt/api/cfg".format(self.admin_url), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return cbgtconfig.CbgtConfig(resp.json())

    # GET /_cbgt/api/diag
    def get_cbgt_diagnostics(self):
        resp = requests.get("{0}/_cbgt/api/diag".format(self.admin_url), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # GET /{db}/_changes
    def get_global_changes(self, db):
        r = requests.get("{}/{}/_changes".format(self.admin_url, db), verify=False)
        log_request(r)
        log_response(r)
        r.raise_for_status()
        resp_data = r.json()
        return resp_data["results"]

    # GET /_active_tasks
    def get_active_tasks(self):
        r = requests.get("{}/_active_tasks".format(self.admin_url), verify=False)
        log_request(r)
        log_response(r)
        r.raise_for_status()
        resp_data = r.json()
        return resp_data

    def get_all_docs(self, db):
        resp = requests.get("{0}/{1}/_all_docs".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # GET /_replicationStatus for sg replicate2
    def get_sgreplicate2_active_tasks(self, db):
        r = requests.get("{}/{}/_replicationStatus".format(self.admin_url, db), verify=False)
        log_request(r)
        log_response(r)
        r.raise_for_status()
        resp_data = r.json()
        return resp_data

    def wait_until_sgw_replication_done(self, db, repl_id, read_flag=False, write_flag=False, max_times=25):

        read_flag = True
        write_flag = True
        read_timeout = False
        write_timeout = False
        if read_flag is False:
            read_timeout = True  # To avoid waiting for read doc count as there is not expectation of read docs
        if write_flag is False:
            write_timeout = True  # To avoid waiting for write doc count as there is not expectation of write docs
        retry_max_count = 5
        count = 0
        prev_read_count = 0
        prev_write_count = 0
        read_retry_count = 0
        write_retry_count = 0
        while count < max_times:
            r = requests.get("{}/{}/_replicationStatus/{}".format(self.admin_url, db, repl_id), verify=False)
            r.raise_for_status()
            resp_obj = r.json()
            status = resp_obj["status"]
            if status == "starting" or status == "started":
                count += 1
            elif status == "running":
                if read_flag:
                    if read_retry_count < retry_max_count:
                        try:
                            docs_read_count = resp_obj["docs_read"]
                            if docs_read_count > prev_read_count:
                                prev_read_count = docs_read_count
                                read_retry_count = 0
                            else:
                                read_retry_count += 1
                        except KeyError:
                            read_retry_count += 1
                    else:
                        read_timeout = True

                if write_flag:
                    print("it is insidde write flag")
                    if write_retry_count < retry_max_count:
                        try:
                            docs_write_count = resp_obj["docs_written"]
                            print("doc written count is ", docs_write_count)
                            if docs_write_count > prev_write_count:
                                prev_write_count = docs_write_count
                                write_retry_count = 0
                                print("ddocs write count got incremented")
                            else:
                                write_retry_count += 1
                                print("docss write count ddid not increment")
                        except KeyError:
                            write_retry_count += 1
                    else:
                        write_timeout = True
            count += 1
            time.sleep(1)
            print("replication still happening andd counting ", count)
            if read_timeout and write_timeout:
                break
        if count == max_times:
            raise Exception("timeout while waiting for replication to complete on sgw replication")

    def get_replications_count(self, db, expected_count=1):
        r = requests.get("{}/{}/_replication".format(self.admin_url, db), verify=False)
        log_request(r)
        log_response(r)
        r.raise_for_status()
        resp_data = r.json()
        count = 0
        while count < expected_count:
            for repl in resp_data:
                repl_body = resp_data[repl]
                if "(local)" in repl_body['assigned_node']:
                    count += 1
            if count >= expected_count:
                break
            time.sleep(1)
        return count
