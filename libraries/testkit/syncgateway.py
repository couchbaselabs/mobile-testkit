import json
import logging
import os
import time
import re

import requests
from requests import HTTPError

import libraries.testkit.settings
from libraries.provision.ansible_runner import AnsibleRunner
from libraries.testkit.admin import Admin
from libraries.testkit.config import Config
from libraries.testkit.debug import log_request, log_response
from utilities.cluster_config_utils import is_cbs_ssl_enabled, is_xattrs_enabled, no_conflicts_enabled, sg_ssl_enabled, is_ipv6
from utilities.cluster_config_utils import get_revs_limit, get_redact_level, is_delta_sync_enabled, get_sg_platform
from utilities.cluster_config_utils import get_sg_replicas, get_sg_use_views, get_sg_version, is_x509_auth, generate_x509_certs
from keywords.utils import add_cbs_to_sg_config_server_field, log_info
from keywords.constants import SYNC_GATEWAY_CERT
from keywords.exceptions import ProvisioningError

log = logging.getLogger(libraries.testkit.settings.LOGGER)


class SyncGateway:

    def __init__(self, cluster_config, target):
        self.ansible_runner = AnsibleRunner(cluster_config)
        self.ip = target["ip"]

        sg_scheme = "http"

        if sg_ssl_enabled(cluster_config):
            sg_scheme = "https"

        self.url = "{}://{}:4984".format(sg_scheme, target["ip"])
        self.hostname = target["name"]
        self._headers = {'Content-Type': 'application/json'}
        self.cbs_cert_path = os.path.join(os.getcwd(), "certs")
        self.admin = Admin(self)

        self.cluster_config = cluster_config
        self.server_port = 8091
        self.server_scheme = "http"

        if is_cbs_ssl_enabled(self.cluster_config):
            self.server_port = 18091
            self.server_scheme = "https"

        if is_x509_auth(cluster_config):
            self.server_port = ""
            self.server_scheme = "couchbases"

        self.couchbase_server_primary_node = add_cbs_to_sg_config_server_field(self.cluster_config)

    def info(self):
        r = requests.get(self.url)
        r.raise_for_status()
        return r.text

    def stop(self):
        status = self.ansible_runner.run_ansible_playbook(
            "stop-sync-gateway.yml",
            subset=self.hostname
        )
        return status

    def start(self, config):
        conf_path = os.path.abspath(config)
        log.info(">>> Starting sync_gateway with configuration: {}".format(conf_path))
        sg_cert_path = os.path.abspath(SYNC_GATEWAY_CERT)
        bucket_names = get_buckets_from_sync_gateway_config(conf_path)
        sg_platform = get_sg_platform(self.cluster_config)

        playbook_vars = {
            "sync_gateway_config_filepath": conf_path,
            "username": "",
            "password": "",
            "certpath": "",
            "keypath": "",
            "cacertpath": "",
            "sg_cert_path": sg_cert_path,
            "x509_certs_dir": self.cbs_cert_path,
            "x509_auth": False,
            "server_port": self.server_port,
            "server_scheme": self.server_scheme,
            "autoimport": "",
            "xattrs": "",
            "no_conflicts": "",
            "sslcert": "",
            "sslkey": "",
            "num_index_replicas": "",
            "sg_use_views": "",
            "couchbase_server_primary_node": self.couchbase_server_primary_node,
            "delta_sync": ""
        }

        if sg_ssl_enabled(self.cluster_config):
            playbook_vars["sslcert"] = '"SSLCert": "sg_cert.pem",'
            playbook_vars["sslkey"] = '"SSLKey": "sg_privkey.pem",'

        if get_sg_version(self.cluster_config) >= "2.1.0":
            logging_config = '"logging": {"debug": {"enabled": true}'
            try:
                redact_level = get_redact_level(self.cluster_config)
                playbook_vars["logging"] = '{}, "redaction_level": "{}" {},'.format(logging_config, redact_level, "}")
            except KeyError as ex:
                log_info("Keyerror in getting logging{}".format(ex.message))
                playbook_vars["logging"] = '{} {},'.format(logging_config, "}")

            if get_sg_use_views(self.cluster_config):
                playbook_vars["sg_use_views"] = '"use_views": true,'
            else:
                num_replicas = get_sg_replicas(self.cluster_config)
                playbook_vars["num_index_replicas"] = '"num_index_replicas": {},'.format(num_replicas)

            if sg_platform == "macos":
                sg_home_directory = "/Users/sync_gateway"
            else:
                sg_home_directory = "/home/sync_gateway"

            if is_x509_auth(self.cluster_config):
                playbook_vars[
                    "certpath"] = '"certpath": "{}/certs/chain.pem",'.format(sg_home_directory)
                playbook_vars[
                    "keypath"] = '"keypath": "{}/certs/pkey.key",'.format(sg_home_directory)
                playbook_vars[
                    "cacertpath"] = '"cacertpath": "{}/certs/ca.pem",'.format(sg_home_directory)
                playbook_vars["server_scheme"] = "couchbases"
                playbook_vars["server_port"] = ""
                playbook_vars["x509_auth"] = True
                generate_x509_certs(conf_path, bucket_names)
            else:
                playbook_vars["username"] = '"username": "{}",'.format(
                    bucket_names[0])
                playbook_vars["password"] = '"password": "password",'
        else:
            playbook_vars["logging"] = '"log": ["*"],'
            playbook_vars["username"] = '"username": "{}",'.format(
                bucket_names[0])
            playbook_vars["password"] = '"password": "password",'

        if sg_ssl_enabled(self.cluster_config):
            playbook_vars["sslcert"] = '"SSLCert": "sg_cert.pem",'
            playbook_vars["sslkey"] = '"SSLKey": "sg_privkey.pem",'

        if is_xattrs_enabled(self.cluster_config):
            playbook_vars["autoimport"] = '"import_docs": true,'
            playbook_vars["xattrs"] = '"enable_shared_bucket_access": true,'

        if no_conflicts_enabled(self.cluster_config):
            playbook_vars["no_conflicts"] = '"allow_conflicts": false,'
        try:
            revs_limit = get_revs_limit(self.cluster_config)
            playbook_vars["revs_limit"] = '"revs_limit": {},'.format(revs_limit)
        except KeyError:
            log_info("revs_limit no found in {}, Ignoring".format(self.cluster_config))

        if is_delta_sync_enabled(self.cluster_config) and get_sg_version(self.cluster_config) >= "2.5.0":
            playbook_vars["delta_sync"] = '"delta_sync": { "enabled": true},'

        if is_cbs_ssl_enabled(self.cluster_config) and get_sg_version(self.cluster_config) >= "1.5.0":
            playbook_vars["server_scheme"] = "couchbases"
            playbook_vars["server_port"] = 11207
            block_http_vars = {}
            port_list = [8091, 8092, 8093, 8094, 8095, 8096, 11210, 11211]
            for port in port_list:
                block_http_vars["port"] = port
                status = self.ansible_runner.run_ansible_playbook(
                    "block-http-ports.yml",
                    extra_vars=block_http_vars
                )
                if status != 0:
                    raise ProvisioningError("Failed to block port on SGW")

        status = self.ansible_runner.run_ansible_playbook(
            "start-sync-gateway.yml",
            extra_vars=playbook_vars,
            subset=self.hostname
        )
        return status

    def restart(self, config, cluster_config=None):

        if(cluster_config is not None):
            self.cluster_config = cluster_config
        conf_path = os.path.abspath(config)
        log.info(">>> Restarting sync_gateway with configuration: {}".format(conf_path))
        sg_cert_path = os.path.abspath(SYNC_GATEWAY_CERT)
        bucket_names = get_buckets_from_sync_gateway_config(conf_path)

        playbook_vars = {
            "sync_gateway_config_filepath": conf_path,
            "server_port": self.server_port,
            "server_scheme": self.server_scheme,
            "autoimport": "",
            "xattrs": "",
            "no_conflicts": "",
            "revs_limit": "",
            "sslcert": "",
            "sslkey": "",
            "username": "",
            "password": "",
            "certpath": "",
            "keypath": "",
            "cacertpath": "",
            "sg_cert_path": sg_cert_path,
            "x509_certs_dir": self.cbs_cert_path,
            "x509_auth": False,
            "num_index_replicas": "",
            "sg_use_views": "",
            "couchbase_server_primary_node": self.couchbase_server_primary_node,
            "delta_sync": ""
        }

        if sg_ssl_enabled(self.cluster_config):
            playbook_vars["sslcert"] = '"SSLCert": "sg_cert.pem",'
            playbook_vars["sslkey"] = '"SSLKey": "sg_privkey.pem",'

        if get_sg_version(self.cluster_config) >= "2.1.0":
            logging_config = '"logging": {"debug": {"enabled": true}'
            try:
                redact_level = get_redact_level(self.cluster_config)
                playbook_vars["logging"] = '{}, "redaction_level": "{}" {},'.format(logging_config, redact_level, "}")
            except KeyError as ex:
                log_info("Keyerror in getting logging{}".format(ex.message))
                playbook_vars["logging"] = '{} {},'.format(logging_config, "}")
            if get_sg_use_views(self.cluster_config):
                playbook_vars["sg_use_views"] = '"use_views": true,'
            else:
                num_replicas = get_sg_replicas(self.cluster_config)
                playbook_vars["num_index_replicas"] = '"num_index_replicas": {},'.format(num_replicas)

            if is_x509_auth(cluster_config):
                playbook_vars[
                    "certpath"] = '"certpath": "/home/sync_gateway/certs/chain.pem",'
                playbook_vars[
                    "keypath"] = '"keypath": "/home/sync_gateway/certs/pkey.key",'
                playbook_vars[
                    "cacertpath"] = '"cacertpath": "/home/sync_gateway/certs/ca.pem",'
                playbook_vars["server_scheme"] = "couchbases"
                playbook_vars["server_port"] = ""
                playbook_vars["x509_auth"] = True
                generate_x509_certs(cluster_config, bucket_names)
            else:
                playbook_vars["username"] = '"username": "{}",'.format(
                    bucket_names[0])
                playbook_vars["password"] = '"password": "password",'
        else:
            playbook_vars["logging"] = '"log": ["*"],'
            playbook_vars["username"] = '"username": "{}",'.format(
                bucket_names[0])
            playbook_vars["password"] = '"password": "password",'

        if is_xattrs_enabled(self.cluster_config):
            playbook_vars["autoimport"] = '"import_docs": true,'
            playbook_vars["xattrs"] = '"enable_shared_bucket_access": true,'

        if no_conflicts_enabled(self.cluster_config):
            playbook_vars["no_conflicts"] = '"allow_conflicts": false,'
        try:
            revs_limit = get_revs_limit(self.cluster_config)
            playbook_vars["revs_limit"] = '"revs_limit": {},'.format(revs_limit)
        except KeyError:
            log_info("revs_limit no found in {}, Ignoring".format(self.cluster_config))
            playbook_vars["revs_limit"] = ''

        if is_delta_sync_enabled(self.cluster_config) and get_sg_version(self.cluster_config) >= "2.5.0":
            playbook_vars["delta_sync"] = '"delta_sync": { "enabled": true},'

        if is_ipv6(self.cluster_config):
            playbook_vars["couchbase_server_primary_node"] = "[{}]".format(playbook_vars["couchbase_server_primary_node"])
        if is_cbs_ssl_enabled(self.cluster_config) and get_sg_version(self.cluster_config) >= "1.5.0":
            playbook_vars["server_scheme"] = "couchbases"
            playbook_vars["server_port"] = 11207
            block_http_vars = {}
            port_list = [8091, 8092, 8093, 8094, 8095, 8096, 11210, 11211]
            for port in port_list:
                block_http_vars["port"] = port
                status = self.ansible_runner.run_ansible_playbook(
                    "block-http-ports.yml",
                    extra_vars=block_http_vars
                )
                if status != 0:
                    raise ProvisioningError("Failed to block port on SGW")

        status = self.ansible_runner.run_ansible_playbook(
            "reset-sync-gateway.yml",
            extra_vars=playbook_vars,
            subset=self.hostname
        )
        return status

    def verify_launched(self):
        r = requests.get(self.url)
        log.info("GET {} ".format(r.url))
        log.info("{}".format(r.text))
        r.raise_for_status()

    def create_db(self, name):
        return self.admin.create_db(name)

    def delete_db(self, name):
        return self.admin.delete_db(name)

    def reset(self):
        dbs = self.admin.get_dbs()
        for db in dbs:
            self.admin.delete_db(db)

    def start_push_replication(self,
                               target,
                               source_db,
                               target_db,
                               continuous=True,
                               use_remote_source=False,
                               channels=None,
                               async=False,
                               use_admin_url=False):

        if channels is None:
            channels = []

        sg_url = self.url
        if use_admin_url:
            sg_url = self.admin.admin_url

        data = {
            "target": "{}/{}".format(target, target_db),
            "continuous": continuous
        }
        if use_remote_source:
            data["source"] = "{}/{}".format(sg_url, source_db)
        else:
            data["source"] = "{}".format(source_db)

        if len(channels) > 0:
            data["filter"] = "sync_gateway/bychannel"
            data["query_params"] = channels

        if async is True:
            data["async"] = True

        r = requests.post("{}/_replicate".format(sg_url), headers=self._headers, data=json.dumps(data))
        log_request(r)
        log_response(r)
        r.raise_for_status()
        return r.json()

    def stop_push_replication(self,
                              target,
                              source_db,
                              target_db,
                              continuous=True,
                              use_remote_source=False,
                              use_admin_url=False):

        sg_url = self.url
        if use_admin_url:
            sg_url = self.admin.admin_url

        data = {
            "target": "{}/{}".format(target, target_db),
            "cancel": True,
            "continuous": continuous
        }
        if use_remote_source:
            data["source"] = "{}/{}".format(sg_url, source_db)
        else:
            data["source"] = "{}".format(source_db)
        r = requests.post("{}/_replicate".format(sg_url), headers=self._headers, data=json.dumps(data))
        log_request(r)
        log_response(r)
        r.raise_for_status()
        return r.json()

    def start_pull_replication(self,
                               source_url,
                               source_db,
                               target_db,
                               continuous=True,
                               use_remote_target=False,
                               use_admin_url=False):

        sg_url = self.url
        if use_admin_url:
            sg_url = self.admin.admin_url

        data = {
            "source": "{}/{}".format(source_url, source_db),
            "continuous": continuous
        }
        if use_remote_target:
            data["target"] = "{}/{}".format(sg_url, target_db)
        else:
            data["target"] = "{}".format(target_db)
        r = requests.post("{}/_replicate".format(sg_url), headers=self._headers, data=json.dumps(data))
        log_request(r)
        log_response(r)
        r.raise_for_status()
        return r.json()

    def stop_pull_replication(self,
                              source_url,
                              source_db,
                              target_db,
                              continuous=True,
                              use_remote_target=False,
                              use_admin_url=False):

        sg_url = self.url
        if use_admin_url:
            sg_url = self.admin.admin_url

        data = {
            "source": "{}/{}".format(source_url, source_db),
            "cancel": True,
            "continuous": continuous
        }
        if use_remote_target:
            data["target"] = "{}/{}".format(sg_url, target_db)
        else:
            data["target"] = "{}".format(target_db)
        r = requests.post("{}/_replicate".format(sg_url), headers=self._headers, data=json.dumps(data))
        log_request(r)
        log_response(r)
        r.raise_for_status()
        return r.json()

    def stop_replication_by_id(self, replication_id, use_admin_url=False):
        sg_url = self.url
        if use_admin_url:
            sg_url = self.admin.admin_url

        data = {
            "replication_id": "{}".format(replication_id),
            "cancel": True,
        }
        r = requests.post("{}/_replicate".format(sg_url), headers=self._headers, data=json.dumps(data))
        log_request(r)
        log_response(r)
        r.raise_for_status()

    def get_num_docs(self, db):
        r = requests.get("{}/{}/_all_docs".format(self.url, db))
        log_request(r)
        log_response(r)
        r.raise_for_status()
        resp_data = r.json()
        return resp_data["total_rows"]

    def __repr__(self):
        return "SyncGateway: {}:{}\n".format(self.hostname, self.ip)


def get_buckets_from_sync_gateway_config(sync_gateway_config_path):
    # Remove the sync function before trying to extract the bucket names

    with open(sync_gateway_config_path) as fp:
        conf_data = fp.read()

    fp.close()
    temp_config_path = ""
    temp_config = ""

    # Check if a sync function id defined between ` `
    if re.search('`', conf_data):
        log_info("Ignoring the sync function to extract bucket names")
        conf = re.split('`', conf_data)
        split_len = len(conf)

        # Replace the sync function with a string "function"
        for i in range(0, split_len, 2):
            if i == split_len - 1:
                temp_config += conf[i]
            else:
                temp_config += conf[i] + " \"function\" "

        temp_config_path = "/".join(sync_gateway_config_path.split('/')[:-2]) + '/temp_conf.json'

        with open(temp_config_path, 'w') as fp:
            fp.write(temp_config)

        config_path_full = os.path.abspath(temp_config_path)
    else:
        config_path_full = os.path.abspath(sync_gateway_config_path)

    config = Config(config_path_full)
    bucket_name_set = config.get_bucket_name_set()
    if os.path.exists(temp_config_path):
        os.remove(temp_config_path)
    return bucket_name_set


def wait_until_doc_in_changes_feed(sg, db, doc_id):

    max_tries = 10
    sleep_retry_seconds = 1

    for attempt in xrange(max_tries):
        changes_results = sg.admin.get_global_changes(db)
        for changes_result in changes_results:
            if changes_result["id"] == doc_id:
                return

        time.sleep(sleep_retry_seconds)

    raise Exception("Tried to wait until doc {} showed up on changes feed, gave up".format(doc_id))


def wait_until_active_tasks_empty(sg):

    max_tries = 10
    sleep_retry_seconds = 1

    for attempt in xrange(max_tries):
        active_tasks = sg.admin.get_active_tasks()
        if len(active_tasks) == 0:
            return
        time.sleep(sleep_retry_seconds)

    raise Exception("Tried to wait until _active_tasks were empty, but they were never empty")


def wait_until_active_tasks_non_empty(sg):

    max_tries = 10
    sleep_retry_seconds = 1

    for attempt in xrange(max_tries):
        active_tasks = sg.admin.get_active_tasks()
        if len(active_tasks) > 0:
            return
        time.sleep(sleep_retry_seconds)

    raise Exception("Tried to wait until _active_tasks were non-empty, but they were never non-empty")


def wait_until_docs_sync(sg_user, doc_ids):
    for doc_id in doc_ids:
        wait_until_doc_sync(sg_user, doc_id)


def wait_until_doc_sync(sg_user, doc_id):
    max_tries_per_doc = 100
    sleep_retry_per_doc_seconds = 1

    for attempt in xrange(max_tries_per_doc):
        try:
            sg_user.get_doc(doc_id)
            # if we got a doc, and no exception was thrown, we're done
            return
        except HTTPError:
            time.sleep(sleep_retry_per_doc_seconds)

    raise Exception("Waited for doc {} to sync, but it never did".format(doc_id))


def assert_does_not_have_doc(sg_user, doc_id):
    # Make sure the doc did not propagate to the target
    got_exception = False
    try:
        sg_user.get_doc(doc_id)
    except HTTPError:
        got_exception = True
    assert got_exception is True


def assert_has_doc(sg_user, doc_id):
    doc = sg_user.get_doc(doc_id)
    assert doc is not None
    assert doc["_id"] == doc_id
