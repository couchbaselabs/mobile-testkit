import requests
import subprocess
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
from keywords.utils import log_info
from keywords.constants import RBAC_FULL_ADMIN
from requests.auth import HTTPBasicAuth
from utilities.cluster_config_utils import is_admin_auth_disabled

import logging
log = logging.getLogger(settings.LOGGER)


class Admin:

    def __init__(self, sync_gateway):
        sg_scheme = "http"

        self.cluster_config = os.environ["CLUSTER_CONFIG"]
        if sg_ssl_enabled(self.cluster_config):
            sg_scheme = "https"

        self.admin_url = "{}://{}:4985".format(sg_scheme, sync_gateway.ip)
        self.users = {}
        self._headers = {"Content-Type": "application/json"}
        self.auth = None

    def create_db_with_rest(self, db, db_config={}):
        db_config = json.dumps(db_config)
        db_config = db_config.replace('"', '\\"')
        command = 'curl -X PUT {0}/{1}/ -H "Content-Type: application/json" -d "{2}"'.format(self.admin_url, db, db_config)
        command_output = subprocess.check_output(command, shell=True)
        return command_output

    def create_db(self, name, db_config={}):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        if self.auth:
            resp = requests.put("{}/{}/".format(self.admin_url, name), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(db_config), verify=False, auth=self.auth)
        else:
            resp = requests.put("{}/{}/".format(self.admin_url, name), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(db_config), verify=False)
        log.info("PUT {}".format(resp.url))
        log_request(resp)
        log_response(resp)
        resp.raise_for_status()
        return resp.status_code

    def delete_db(self, name):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        if self.auth:
            r = requests.delete("{}/{}".format(self.admin_url, name), verify=False, auth=self.auth)
        else:
            r = requests.delete("{}/{}".format(self.admin_url, name), verify=False)
        log_request(r)
        log_response(r)
        r.raise_for_status()
        return r.json()

    def get_dbs(self):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        if self.auth:
            r = requests.get("{}/_all_dbs".format(self.admin_url), verify=False, auth=self.auth)
        else:
            r = requests.get("{}/_all_dbs".format(self.admin_url), verify=False)
        log.info("GET {}".format(r.url))
        log_response(r)
        r.raise_for_status()
        return r.json()

    def get_dbs_from_config(self):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        if self.auth:
            r = requests.get("{}/_config".format(self.admin_url), verify=False, auth=self.auth)
        else:
            r = requests.get("{}/_config".format(self.admin_url), verify=False)
        log.info("GET {}".format(r.url))
        r.raise_for_status()
        json_config = r.json()
        return list(json_config["Databases"].keys())

    # GET /{db}/
    def get_db_info(self, db):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        if self.auth:
            resp = requests.get("{0}/{1}/".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False, auth=self.auth)
        else:
            resp = requests.get("{0}/{1}/".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # PUT /{db}/_role/{name}
    def create_role(self, db, name, channels):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        data = {"name": name, "admin_channels": channels}
        if self.auth:
            resp = requests.put("{0}/{1}/_role/{2}".format(self.admin_url, db, name), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(data), verify=False, auth=self.auth)
        else:
            resp = requests.put("{0}/{1}/_role/{2}".format(self.admin_url, db, name), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(data), verify=False)
        log.info("PUT {}".format(resp.url))
        resp.raise_for_status()

    # GET /{db}/_role
    def get_roles(self, db):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        if self.auth:
            resp = requests.get("{0}/{1}/_role/".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False, auth=self.auth)
        else:
            resp = requests.get("{0}/{1}/_role/".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # GET /{db}/_role/{name}
    def get_role(self, db, name):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        if self.auth:
            resp = requests.get("{0}/{1}/_role/{2}".format(self.admin_url, db, name), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False, auth=self.auth)
        else:
            resp = requests.get("{0}/{1}/_role/{2}".format(self.admin_url, db, name), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # PUT /{db}/_user/{name}
    def register_user(self, target, db, name, password=None, channels=list(), roles=list()):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        if password is None:
            data = {"name": name, "admin_channels": channels, "admin_roles": roles, "disabled": False}
        else:
            data = {"name": name, "password": password, "admin_channels": channels, "admin_roles": roles}

        if self.auth:
            resp = requests.put("{0}/{1}/_user/{2}".format(self.admin_url, db, name), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(data), verify=False, auth=self.auth)
        else:
            resp = requests.put("{0}/{1}/_user/{2}".format(self.admin_url, db, name), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(data), verify=False)
        log.info("PUT {}".format(resp.url))
        resp.raise_for_status()

        return User(target, db, name, password, channels)

    def delete_user_if_exists(self, db, sg_username):
        does_user_exist = self.does_user_exist(db, sg_username)
        if does_user_exist:
            resp = requests.delete("{}/{}/_user/{}".format(self.admin_url, db, sg_username))
            log.info("DELETE user {} from database {}".format(db, sg_username))
            resp.raise_for_status()

        return does_user_exist

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
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        if self.auth:
            resp = requests.get("{0}/{1}/_user/".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False, auth=self.auth)
        else:
            resp = requests.get("{0}/{1}/_user/".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # GET /{db}/_user/{name}
    def get_user_info(self, db, name):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        if self.auth:
            resp = requests.get("{0}/{1}/_user/{2}".format(self.admin_url, db, name), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False, auth=self.auth)
        else:
            resp = requests.get("{0}/{1}/_user/{2}".format(self.admin_url, db, name), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # POST /{db}/_resync
    def db_resync(self, db):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        result = dict()
        if self.auth:
            resp = requests.post("{0}/{1}/_resync".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False, auth=self.auth)
        else:
            resp = requests.post("{0}/{1}/_resync".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
        log.info("POST {}".format(resp.url))
        resp.raise_for_status()
        result['status_code'] = resp.status_code
        result['payload'] = resp.json()
        return result

    # GET /{db}/_resync
    def db_get_resync_status(self, db):
        result = dict()
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        if self.auth:
            resp = requests.get("{0}/{1}/_resync".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False, auth=self.auth)
        else:
            resp = requests.get("{0}/{1}/_resync".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        result['status_code'] = resp.status_code
        result['payload'] = resp.json()
        return result

    # POST /{db}/_online
    def bring_db_online(self, db, delay=None):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        data = {}
        if delay is not None:
            data = {"delay": delay}

        if self.auth:
            resp = requests.post("{0}/{1}/_online".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(data), verify=False, auth=self.auth)
        else:
            resp = requests.post("{0}/{1}/_online".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(data), verify=False)
        log.info("POST {}".format(resp.url))
        resp.raise_for_status()
        return resp.status_code

    # POST /{db}/_offline
    def take_db_offline(self, db):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        if self.auth:
            resp = requests.post("{0}/{1}/_offline".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False, auth=self.auth)
        else:
            resp = requests.post("{0}/{1}/_offline".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
        log.info("POST {}".format(resp.url))
        resp.raise_for_status()
        return resp.status_code

    # GET /{db}/_config
    def get_db_config(self, db):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        if self.auth:
            resp = requests.get("{0}/{1}/_config".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False, auth=self.auth)
        else:
            resp = requests.get("{0}/{1}/_config".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # PUT /{db}/_config
    def put_db_config(self, db, config):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        if self.auth:
            resp = requests.put("{0}/{1}/_config".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(config), verify=False, auth=self.auth)
        else:
            resp = requests.put("{0}/{1}/_config".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(config), verify=False)
        log.info("PUT {}".format(resp.url))
        resp.raise_for_status()
        return resp.status_code

    # POST /{db}/_config
    def post_db_config(self, db, config):
        if self.auth:
            resp = requests.post("{0}/{1}/_config".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(config), verify=False, auth=self.auth)
        else:
            resp = requests.post("{0}/{1}/_config".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(config), verify=False)
        log.info("POST {}".format(resp.url))
        resp.raise_for_status()

        return resp.status_code

    # GET /_config
    def get_config(self):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])

        if self.auth:
            resp = requests.get("{0}/_config".format(self.admin_url), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False, auth=self.auth)
        else:
            resp = requests.get("{0}/_config".format(self.admin_url), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # GET /_cbgt/api/cfg
    def get_cbgt_config(self):
        """ Get the REST cfg response from an accel node.
        Return an CbgtConfig object that exposes common methods useful in validation"""
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        if self.auth:
            resp = requests.get("{0}/_cbgt/api/cfg".format(self.admin_url), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False, auth=self.auth)
        else:
            resp = requests.get("{0}/_cbgt/api/cfg".format(self.admin_url), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return cbgtconfig.CbgtConfig(resp.json())

    # GET /_cbgt/api/diag
    def get_cbgt_diagnostics(self):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        if self.auth:
            resp = requests.get("{0}/_cbgt/api/diag".format(self.admin_url), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False, auth=self.auth)
        else:
            resp = requests.get("{0}/_cbgt/api/diag".format(self.admin_url), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # GET /{db}/_changes
    def get_global_changes(self, db):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        if self.auth:
            r = requests.get("{}/{}/_changes".format(self.admin_url, db), verify=False, auth=self.auth)
        else:
            r = requests.get("{}/{}/_changes".format(self.admin_url, db), verify=False)
        log_request(r)
        log_response(r)
        r.raise_for_status()
        resp_data = r.json()
        return resp_data["results"]

    # GET /_active_tasks
    def get_active_tasks(self):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        if self.auth:
            r = requests.get("{}/_active_tasks".format(self.admin_url), verify=False, auth=self.auth)
        else:
            r = requests.get("{}/_active_tasks".format(self.admin_url), verify=False)
        log_request(r)
        log_response(r)
        r.raise_for_status()
        resp_data = r.json()
        return resp_data

    def get_all_docs(self, db):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        if self.auth:
            resp = requests.get("{0}/{1}/_all_docs".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False, auth=self.auth)
        else:
            resp = requests.get("{0}/{1}/_all_docs".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    # GET /_replicationStatus for sg replicate2
    def get_sgreplicate2_active_tasks(self, db, expected_tasks=1):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        count = 0
        max_count = 5
        while True:
            if self.auth:
                r = requests.get("{}/{}/_replicationStatus".format(self.admin_url, db), verify=False, auth=self.auth)
            else:
                r = requests.get("{}/{}/_replicationStatus".format(self.admin_url, db), verify=False)
            log_request(r)
            log_response(r)
            r.raise_for_status()
            resp_data = r.json()
            active_resp_data = []
            for repl in resp_data:
                if "starting" in repl['status'] or "started" in repl['status'] or "running" in repl['status']:
                    active_resp_data.append(repl)
            if len(active_resp_data) == expected_tasks or count >= max_count:
                break
            count += 1
            time.sleep(1)
        return active_resp_data

    def wait_until_sgw_replication_done(self, db, repl_id, read_flag=False, write_flag=False, max_times=180):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        # read_flag = True
        # write_flag = True
        read_timeout = False
        write_timeout = False
        if read_flag is False:
            read_timeout = True  # To avoid waiting for read doc count as there is not expectation of read docs
        if write_flag is False:
            write_timeout = True  # To avoid waiting for write doc count as there is not expectation of write docs
        retry_max_count = 120
        count = 0
        prev_read_count = 0
        prev_write_count = 0
        read_retry_count = 0
        write_retry_count = 0
        while count < max_times:
            if self.auth:
                r = requests.get("{}/{}/_replicationStatus/{}".format(self.admin_url, db, repl_id), verify=False, auth=self.auth)
            else:
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
                    if write_retry_count < retry_max_count:
                        try:
                            docs_write_count = resp_obj["docs_written"]
                            if docs_write_count > prev_write_count:
                                prev_write_count = docs_write_count
                                write_retry_count = 0
                            else:
                                write_retry_count += 1
                        except KeyError:
                            write_retry_count += 1
                    else:
                        write_timeout = True
            else:
                log_info("looks like replication is stopped")
                break
            count += 1
            time.sleep(1)
            if read_timeout and write_timeout:
                log_info("read or write timeout happened")
                break
        if count == max_times:
            raise Exception("timeout while waiting for replication to complete on sgw replication")

    def get_replications_count(self, db, expected_count=1):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        local_count = 0
        max_count = 15
        while True:
            if self.auth:
                r = requests.get("{}/{}/_replication".format(self.admin_url, db), verify=False, auth=self.auth)
            else:
                r = requests.get("{}/{}/_replication".format(self.admin_url, db), verify=False)
            log_request(r)
            log_response(r)
            r.raise_for_status()
            resp_data = r.json()
            count = 0
            for repl in resp_data:
                repl_body = resp_data[repl]
                if "(local)" in repl_body['assigned_node']:
                    count += 1
            if count == expected_count or local_count >= max_count:
                break
            time.sleep(1)
            local_count += 1
        return count

    def create_sync_func(self, db, sync_func):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        sync_headers = {"Content-Type": "application/javascript"}
        if self.auth:
            resp = requests.put("{0}/{1}/_config/sync".format(self.admin_url, db), headers=sync_headers, timeout=settings.HTTP_REQ_TIMEOUT, data=sync_func, verify=False, auth=self.auth)
        else:
            resp = requests.put("{0}/{1}/_config/sync".format(self.admin_url, db), headers=sync_headers, timeout=settings.HTTP_REQ_TIMEOUT, data=sync_func, verify=False)
        log.info("PUT {}".format(resp.url))
        resp.raise_for_status()
        return resp.status_code

    def delete_sync_func(self, db):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        sync_headers = {"Content-Type": "application/javascript"}
        if self.auth:
            resp = requests.delete("{0}/{1}/_config/sync".format(self.admin_url, db), headers=sync_headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False, auth=self.auth)
        else:
            resp = requests.delete("{0}/{1}/_config/sync".format(self.admin_url, db), headers=sync_headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
        log.info("PUT {}".format(resp.url))
        resp.raise_for_status()
        return resp.status_code

    def create_imp_fltr_func(self, db, imp_fltr_func):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        if self.auth:
            resp = requests.put("{0}/{1}/_config/import_filter".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=imp_fltr_func, verify=False, auth=self.auth)
        else:
            resp = requests.put("{0}/{1}/_config/import_filter".format(self.admin_url, db), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=imp_fltr_func, verify=False)
        log.info("PUT {}".format(resp.url))
        resp.raise_for_status()
        return resp.status_code

    # PUT /_config
    def put_config(self, config):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        if self.auth:
            resp = requests.put("{0}/_config".format(self.admin_url), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(config), verify=False, auth=self.auth)
        else:
            resp = requests.put("{0}/_config".format(self.admin_url), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(config), verify=False)
        log.info("PUT {}".format(resp.url))
        resp.raise_for_status()
        return resp.status_code

    # GET /_config
    def get_runtime_config(self):
        if not is_admin_auth_disabled(self.cluster_config):
            self.auth = HTTPBasicAuth(RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd'])
        if self.auth:
            resp = requests.get("{0}/_config?include_runtime=true".format(self.admin_url), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False, auth=self.auth)
        else:
            resp = requests.get("{0}/_config?include_runtime=true".format(self.admin_url), headers=self._headers, timeout=settings.HTTP_REQ_TIMEOUT, verify=False)
        log.info("GET {}".format(resp.url))
        resp.raise_for_status()
        return resp.json()

    def does_db_exist(self, db):
        try:
            self.get_db_info(db)
            return True
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return False
            else:
                raise Exception("Could not determine if the database exists due to the following error: " + str(e)) from e

    def does_user_exist(self, db, user):
        try:
            self.get_user_info(db, user)
            return True
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return False
            else:
                raise Exception("Could not determine if the user exists due to the following error: " + str(e)) from e

    def get_bucket_db(self, bucket):
        dbs = self.get_dbs()
        if not dbs:
            return None
        for db in dbs:
            dbconfig = self.get_db_config(db)
            if dbconfig["bucket"] == bucket:
                return db
        return None
