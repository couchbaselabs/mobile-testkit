import json
import logging
import os
import time
import re

import requests
from jinja2 import Template
from requests import HTTPError

import libraries.testkit.settings
from libraries.provision.ansible_runner import AnsibleRunner
from libraries.testkit.admin import Admin
from libraries.testkit.config import Config, seperate_sgw_and_db_config
from libraries.testkit.debug import log_request, log_response
from utilities.cluster_config_utils import is_cbs_ssl_enabled, is_xattrs_enabled, no_conflicts_enabled, sg_ssl_enabled, get_cbs_primary_nodes_str
from utilities.cluster_config_utils import get_revs_limit, get_redact_level, is_delta_sync_enabled, get_sg_platform, get_bucket_list_cpc
from utilities.cluster_config_utils import is_hide_prod_version_enabled, is_centralized_persistent_config_disabled
from utilities.cluster_config_utils import get_sg_replicas, get_sg_use_views, get_sg_version, is_x509_auth, generate_x509_certs
from keywords.utils import add_cbs_to_sg_config_server_field, log_info, random_string
from keywords.constants import SYNC_GATEWAY_CERT, SGW_DB_CONFIGS, SYNC_GATEWAY_CONFIGS, SYNC_GATEWAY_CONFIGS_CPC
from keywords.exceptions import ProvisioningError
from keywords.remoteexecutor import RemoteExecutor
from utilities.cluster_config_utils import is_server_tls_skip_verify_enabled, is_admin_auth_disabled, is_tls_server_disabled

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
        self.server_port = ""
        self.server_scheme = "couchbase"

        if is_cbs_ssl_enabled(self.cluster_config):
            self.server_port = ""
            self.server_scheme = "couchbases"

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
        # c_cluster = cluster.Cluster(self.cluster_config)
        if get_sg_version(self.cluster_config) >= "3.0.0" and not is_centralized_persistent_config_disabled(self.cluster_config):
            playbook_vars, db_config_json, sgw_config_data = setup_sgwconfig_db_config(self.cluster_config, config)
        else:
            conf_path = os.path.abspath(config)
            log.info(">>> Starting sync_gateway with configuration: {}".format(conf_path))
            sg_cert_path = os.path.abspath(SYNC_GATEWAY_CERT)
            bucket_names = get_buckets_from_sync_gateway_config(conf_path, self.cluster_config)
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
                "delta_sync": "",
                "prometheus": "",
                "hide_product_version": "",
                "tls": "",
                "disable_persistent_config": "",
                "server_tls_skip_verify": "",
                "disable_tls_server": "",
                "disable_admin_auth": ""
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
                    log_info("Keyerror in getting logging{}".format(ex.args))
                    playbook_vars["logging"] = '{} {},'.format(logging_config, "}")

                if get_sg_use_views(self.cluster_config):
                    playbook_vars["sg_use_views"] = '"use_views": true,'
                else:
                    num_replicas = get_sg_replicas(self.cluster_config)
                    playbook_vars["num_index_replicas"] = '"num_index_replicas": {},'.format(num_replicas)

                if "macos" in sg_platform:
                    sg_home_directory = "/Users/sync_gateway"
                elif sg_platform == "windows":
                    sg_home_directory = "C:\\\\PROGRA~1\\\\Couchbase\\\\Sync Gateway"
                else:
                    sg_home_directory = "/home/sync_gateway"

                if is_x509_auth(self.cluster_config):
                    playbook_vars[
                        "certpath"] = '"certpath": "{}/certs/chain.pem",'.format(sg_home_directory)
                    playbook_vars[
                        "keypath"] = '"keypath": "{}/certs/pkey.key",'.format(sg_home_directory)
                    playbook_vars[
                        "cacertpath"] = '"cacertpath": "{}/certs/ca.pem",'.format(sg_home_directory)
                    if sg_platform == "windows":
                        playbook_vars["certpath"] = playbook_vars["certpath"].replace("/", "\\\\")
                        playbook_vars["keypath"] = playbook_vars["keypath"].replace("/", "\\\\")
                        playbook_vars["cacertpath"] = playbook_vars["cacertpath"].replace("/", "\\\\")
                    playbook_vars["server_scheme"] = "couchbases"
                    playbook_vars["server_port"] = ""
                    playbook_vars["x509_auth"] = True
                    generate_x509_certs(self.cluster_config, bucket_names, sg_platform)
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
                if get_sg_version(self.cluster_config) >= "2.1.0":
                    playbook_vars["autoimport"] = '"import_docs": true,'
                else:
                    playbook_vars["autoimport"] = '"import_docs": "continuous",'
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

            if get_sg_version(self.cluster_config) >= "2.8.0":
                playbook_vars["prometheus"] = '"metricsInterface": ":4986",'

            if is_hide_prod_version_enabled(self.cluster_config) and get_sg_version(self.cluster_config) >= "2.8.1":
                playbook_vars["hide_product_version"] = '"hide_product_version": true,'

            if is_centralized_persistent_config_disabled(self.cluster_config) and get_sg_version(self.cluster_config) >= "3.0.0":
                playbook_vars["disable_persistent_config"] = '"disable_persistent_config": true,'

            if is_server_tls_skip_verify_enabled(self.cluster_config) and get_sg_version(self.cluster_config) >= "3.0.0":
                playbook_vars["server_tls_skip_verify"] = '"server_tls_skip_verify": true,'

            if is_tls_server_disabled(self.cluster_config) and get_sg_version(self.cluster_config) >= "3.0.0":
                playbook_vars["disable_tls_server"] = '"use_tls_server": false,'

            if is_admin_auth_disabled(self.cluster_config) and get_sg_version(self.cluster_config) >= "3.0.0":
                playbook_vars["disable_admin_auth"] = '"admin_interface_authentication": false,    \n"metrics_interface_authentication": false,'

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
        if status == 0:
            if get_sg_version(self.cluster_config) >= "3.0.0" and not is_centralized_persistent_config_disabled(self.cluster_config):
                # Now create rest API for all database configs
                sgw_list = [self]
                send_dbconfig_as_restCall(db_config_json, sgw_list, sgw_config_data)
        return status

    def restart(self, config, cluster_config=None):

        if cluster_config is None:
            cluster_config = self.cluster_config
        # c_cluster = cluster.Cluster(self.cluster_config)
        if get_sg_version(cluster_config) >= "3.0.0" and not is_centralized_persistent_config_disabled(cluster_config):
            playbook_vars, db_config_json, sgw_config_data = setup_sgwconfig_db_config(cluster_config, config)
        else:
            conf_path = os.path.abspath(config)
            log.info(">>> Restarting sync_gateway with configuration: {}".format(conf_path))
            sg_cert_path = os.path.abspath(SYNC_GATEWAY_CERT)
            bucket_names = get_buckets_from_sync_gateway_config(conf_path, cluster_config)

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
                "delta_sync": "",
                "prometheus": "",
                "hide_product_version": "",
                "tls": "",
                "disable_persistent_config": "",
                "server_tls_skip_verify": "",
                "disable_tls_server": "",
                "disable_admin_auth": ""
            }
            sg_platform = get_sg_platform(cluster_config)

            if sg_ssl_enabled(cluster_config):
                playbook_vars["sslcert"] = '"SSLCert": "sg_cert.pem",'
                playbook_vars["sslkey"] = '"SSLKey": "sg_privkey.pem",'

            if get_sg_version(cluster_config) >= "2.1.0":
                logging_config = '"logging": {"debug": {"enabled": true}'
                try:
                    redact_level = get_redact_level(cluster_config)
                    playbook_vars["logging"] = '{}, "redaction_level": "{}" {},'.format(logging_config, redact_level, "}")
                except KeyError as ex:

                    log_info("Keyerror in getting logging{}".format(str(ex)))

                    playbook_vars["logging"] = '{} {},'.format(logging_config, "}")
                if get_sg_use_views(cluster_config):
                    playbook_vars["sg_use_views"] = '"use_views": true,'
                else:
                    num_replicas = get_sg_replicas(cluster_config)
                    playbook_vars["num_index_replicas"] = '"num_index_replicas": {},'.format(num_replicas)

                if "macos" in sg_platform:
                    sg_home_directory = "/Users/sync_gateway"
                elif sg_platform == "windows":
                    sg_home_directory = "C:\\\\PROGRA~1\\\\Couchbase\\\\Sync Gateway"
                else:
                    sg_home_directory = "/home/sync_gateway"

                if is_x509_auth(cluster_config):
                    playbook_vars[
                        "certpath"] = '"certpath": "{}/certs/chain.pem",'.format(sg_home_directory)
                    playbook_vars[
                        "keypath"] = '"keypath": "{}/certs/pkey.key",'.format(sg_home_directory)
                    playbook_vars[
                        "cacertpath"] = '"cacertpath": "{}/certs/ca.pem",'.format(sg_home_directory)
                    if sg_platform == "windows":
                        playbook_vars["certpath"] = playbook_vars["certpath"].replace("/", "\\\\")
                        playbook_vars["keypath"] = playbook_vars["keypath"].replace("/", "\\\\")
                        playbook_vars["cacertpath"] = playbook_vars["cacertpath"].replace("/", "\\\\")
                    playbook_vars["server_scheme"] = "couchbases"
                    playbook_vars["server_port"] = ""
                    playbook_vars["x509_auth"] = True
                    generate_x509_certs(cluster_config, bucket_names, sg_platform)
                else:
                    playbook_vars["username"] = '"username": "{}",'.format(
                        bucket_names[0])
                    playbook_vars["password"] = '"password": "password",'

            else:
                playbook_vars["logging"] = '"log": ["*"],'
                playbook_vars["username"] = '"username": "{}",'.format(
                    bucket_names[0])
                playbook_vars["password"] = '"password": "password",'

            if is_xattrs_enabled(cluster_config):
                if get_sg_version(cluster_config) >= "2.1.0":
                    playbook_vars["autoimport"] = '"import_docs": true,'
                else:
                    playbook_vars["autoimport"] = '"import_docs": "continuous",'
            playbook_vars["xattrs"] = '"enable_shared_bucket_access": true,'

            if no_conflicts_enabled(cluster_config):
                playbook_vars["no_conflicts"] = '"allow_conflicts": false,'
            try:
                revs_limit = get_revs_limit(cluster_config)
                playbook_vars["revs_limit"] = '"revs_limit": {},'.format(revs_limit)
            except KeyError:
                log_info("revs_limit no found in {}, Ignoring".format(cluster_config))
                playbook_vars["revs_limit"] = ''

            if is_delta_sync_enabled(cluster_config) and get_sg_version(cluster_config) >= "2.5.0":
                playbook_vars["delta_sync"] = '"delta_sync": { "enabled": true},'

            if get_sg_version(cluster_config) >= "2.8.0":
                playbook_vars["prometheus"] = '"metricsInterface": ":4986",'

            if is_hide_prod_version_enabled(cluster_config) and get_sg_version(cluster_config) >= "2.8.1":
                playbook_vars["hide_product_version"] = '"hide_product_version": true,'

            if is_centralized_persistent_config_disabled(cluster_config) and get_sg_version(cluster_config) >= "3.0.0":
                playbook_vars["disable_persistent_config"] = '"disable_persistent_config": true,'

            if is_server_tls_skip_verify_enabled(cluster_config) and get_sg_version(cluster_config) >= "3.0.0":
                playbook_vars["server_tls_skip_verify"] = '"server_tls_skip_verify": true,'

            if is_tls_server_disabled(cluster_config) and get_sg_version(cluster_config) >= "3.0.0":
                playbook_vars["disable_tls_server"] = '"use_tls_server": false,'

            if is_admin_auth_disabled(cluster_config) and get_sg_version(cluster_config) >= "3.0.0":
                playbook_vars["disable_admin_auth"] = '"admin_interface_authentication": false,    \n"metrics_interface_authentication": false,'

            if is_cbs_ssl_enabled(cluster_config) and get_sg_version(cluster_config) >= "1.5.0":
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
        if status == 0:
            if get_sg_version(cluster_config) >= "3.0.0" and not is_centralized_persistent_config_disabled(cluster_config):
                # Now create rest API for all database configs
                sgw_list = [self]
                print("sgw_config_data before sending rest call ", sgw_config_data)
                send_dbconfig_as_restCall(db_config_json, sgw_list, sgw_config_data)
                try:
                    send_dbconfig_as_restCall(db_config_json, sgw_list, sgw_config_data)
                except Exception as ex:
                    status = -1
                    # This is to work similiar to non persistent config to avoid updates on regression tests
                    log.info("if db fails, setting status to -1", str(ex))
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
                               repl_async=False,
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

        if repl_async is True:
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
                               use_admin_url=False,
                               target_user_name=None,
                               target_password=None,
                               channels=None):

        sg_url = self.url
        if use_admin_url:
            sg_url = self.admin.admin_url

        if channels is None:
            channels = []

        if "4984" in source_url:
            if not target_user_name or not target_password:
                raise Exception("username and password not provided for the source")
            source_url = source_url.replace("://", "://{}:{}@".format(target_user_name, target_password))
        data = {
            "source": "{}/{}".format(source_url, source_db),
            "continuous": continuous
        }
        if use_remote_target:
            data["target"] = "{}/{}".format(sg_url, target_db)
        else:
            data["target"] = "{}".format(target_db)

        if len(channels) > 0:
            data["filter"] = "sync_gateway/bychannel"
            data["query_params"] = channels

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

    def start_replication(self,
                          remote_url,
                          current_db,
                          remote_db,
                          direction="push",
                          continuous=True,
                          channels=None,
                          target_user_name=None,
                          target_password=None,
                          replication_id=None):

        sg_url = self.admin.admin_url
        if "4984" in remote_url:
            if not target_user_name or not target_password:
                raise Exception("username and password not provided for the source")
            remote_url = remote_url.replace("://", "://{}:{}@".format(target_user_name, target_password))
        if direction == "push":
            source_url = self.url
            source_url = source_url.replace("4984", "4985")
            data = {
                "source": "{}/{}".format(source_url, current_db),
                "continuous": continuous,
                "target": "{}/{}".format(remote_url, remote_db)
            }
        else:
            # remote_url = remote_url.replace("4984", "4985")
            # target_url = self.admin.admin_url
            data = {
                "source": "{}/{}".format(remote_url, remote_db),
                "continuous": continuous,
                "target": "{}/{}".format(self.admin.admin_url, current_db)
            }
        if channels is not None:
            data["filter"] = "sync_gateway/bychannel"
            data["query_params"] = channels
        if replication_id is not None:
            data["replication_id"] = replication_id
        r = requests.post("{}/_replicate".format(sg_url), headers=self._headers, data=json.dumps(data))
        log_request(r)
        log_response(r)
        r.raise_for_status()
        return r.json()

    def start_replication2(self, local_db, remote_url, remote_db, remote_user, remote_password, direction="pushAndPull", purge_on_removal=None, continuous=False, channels=None, conflict_resolution_type="default", custom_conflict_resolver=None, adhoc=False, delta_sync=False, replication_id=None, max_backoff_time=None, user_credentials_url=True):
        '''
           Required values : remote, direction, conflict_resolution_type
           default values : continuous=false
           optional values : filter
        '''
        sg_url = self.admin.admin_url
        if replication_id is None:
            replication_id = "sgw_repl_{}".format(random_string(length=10, digit=True))
        if "4984" in remote_url:
            if remote_user and remote_password:
                if user_credentials_url:
                    remote_url = remote_url.replace("://", "://{}:{}@".format(remote_user, remote_password))
                remote_url = "{}/{}".format(remote_url, remote_db)
            else:
                raise Exception("No remote node's username and password provided ")
        data = {
            "remote": remote_url,
            "direction": direction,
            "conflict_resolution_type": conflict_resolution_type
        }
        data["continuous"] = continuous
        if purge_on_removal:
            data["purge_on_removal"] = purge_on_removal
        if channels is not None:
            data["filter"] = "sync_gateway/bychannel"
            data["query_params"] = channels
        if adhoc:
            data["adhoc"] = adhoc
        if delta_sync:
            data["enable_delta_sync"] = delta_sync
        if max_backoff_time:
            data["max_backoff_time"] = max_backoff_time
        if conflict_resolution_type == "custom":
            if custom_conflict_resolver is None:
                raise Exception("conflict_resolution_type is selected as custom, but did not provide conflict resolver")
            else:
                data["custom_conflict_resolver"] = custom_conflict_resolver
        if not user_credentials_url:
            data["username"] = remote_user
            data["password"] = remote_password
        # print("starting sg replicate2 rest end point ..")
        # print("json dumps of replication is ", json.dumps(data))
        r = requests.put("{}/{}/_replication/{}".format(sg_url, local_db, replication_id), headers=self._headers, data=json.dumps(data))
        # log.info("PUT {}".format(r.url))
        # log.info("status code {}".format(r.status_code))
        # log.info("text of response {}".format(r.text))
        log_request(r)
        log_response(r)
        r.raise_for_status()
        time.sleep(1)
        return replication_id

    def stop_replication2_by_id(self, replication_id, db):
        sg_url = self.admin.admin_url
        r = requests.delete("{}/{}/_replication/{}".format(sg_url, db, replication_id))
        log_request(r)
        log_response(r)
        r.raise_for_status()

    def modify_replication2_status(self, replication_id, db, action):
        sg_url = self.admin.admin_url
        if action == "reset":
            self.reset_replication2_checkpoint(sg_url, replication_id, db)
        else:
            r = requests.put("{}/{}/_replicationStatus/{}?action={}".format(sg_url, db, replication_id, action))
            log_request(r)
            log_response(r)
            r.raise_for_status()

    def reset_replication2_checkpoint(self, sg_url, replication_id, db):
        r = requests.put("{}/{}/_replicationStatus/{}?action=stop".format(sg_url, db, replication_id))
        log_request(r)
        log_response(r)
        r.raise_for_status()
        time.sleep(1)
        r = requests.put("{}/{}/_replicationStatus/{}?action=reset".format(sg_url, db, replication_id))
        log_request(r)
        log_response(r)
        r.raise_for_status()
        time.sleep(1)
        r = requests.put("{}/{}/_replicationStatus/{}?action=start".format(sg_url, db, replication_id))
        log_request(r)
        log_response(r)
        r.raise_for_status()
        time.sleep(1)

    def get_replication2(self, db):
        sg_url = self.admin.admin_url
        r = requests.get("{}/{}/_replication".format(sg_url, db))
        log_request(r)
        log_response(r)
        r.raise_for_status()
        return r.json()

    def __repr__(self):
        return "SyncGateway: {}:{}\n".format(self.hostname, self.ip)


def setup_sgwconfig_db_config(cluster_config, sg_config_path):
    # Parse config and grab bucket names
    ansible_runner = AnsibleRunner(cluster_config)
    config_path_full = os.path.abspath(sg_config_path)
    config = Config(config_path_full, cluster_config)
    # bucket_name_set = config.get_bucket_name_set()
    sg_cert_path = os.path.abspath(SYNC_GATEWAY_CERT)
    cbs_cert_path = os.path.join(os.getcwd(), "certs")
    bucket_names = get_buckets_from_sync_gateway_config(sg_config_path, cluster_config)
    sg_conf_name = "sync_gateway_default"
    mode = "cc"
    from keywords.SyncGateway import sync_gateway_config_path_for_mode
    cpc_sgw_config_path = sync_gateway_config_path_for_mode(sg_conf_name, mode, cpc=True)
    cpc_config_path_full = os.path.abspath(cpc_sgw_config_path)
    # common_bucket_user = "bucket-admin"
    # self.sync_gateway_config = config

    """ if bucket_creation:
        log_info(">>> Creating buckets on: {}".format(cluster.servers[0].url))
        log_info(">>> Creating buckets {}".format(bucket_name_set))
        cluster.servers[0].create_buckets(bucket_names=bucket_name_set, cluster_config=cluster_config, ipv6=cluster.ipv6)

        # Create read_bucker_user for all buckets
        for bucket_name in bucket_names:
            cluster.servers[0]._create_internal_rbac_user_by_roles(bucket_name, cluster_config, read_bucket_user, "data_reader")

        log_info(">>> Waiting for Server: {} to be in a healthy state".format(cluster.servers[0].url))
        cluster.servers[0].wait_for_ready_state() """

    log_info(">>> Starting sync_gateway with configuration: {}".format(cpc_config_path_full))

    with open(config_path_full, "r") as config:
        sgw_config_data = config.read()

    server_port_var = 8091
    server_scheme_var = "http"
    couchbase_server_primary_node = add_cbs_to_sg_config_server_field(cluster_config)
    if is_cbs_ssl_enabled(cluster_config):
        server_port_var = ""
        server_scheme_var = "couchbases"

    couchbase_server_primary_node = get_cbs_primary_nodes_str(cluster_config, couchbase_server_primary_node)
    # Assign default values to all configs
    x509_auth_var = False
    password_var = ""
    username_playbook_var = ""
    tls_var = ""
    sslcert_var = ""
    sslkey_var = ""
    hide_product_version_var = ""
    bucket_list_var = ""
    disable_persistent_config_var = ""
    prometheus_var = ""

    certpath_var = ""
    keypath_var = ""
    cacertpath_var = ""
    server_scheme_var = ""
    server_port_var = ""
    username_var = ""
    sg_use_views_var = ""
    num_index_replicas_var = ""
    autoimport_var = ""
    xattrs_var = ""
    no_conflicts_var = ""
    revs_limit_var = ""
    delta_sync_var = ""
    disable_persistent_config_var = ""
    server_tls_skip_verify_var = ""
    disable_tls_server_var = ""
    disable_admin_auth_var = ""

    sg_platform = get_sg_platform(cluster_config)

    logging_config = '"logging": {"debug": {"enabled": true}'
    try:
        redact_level = get_redact_level(cluster_config)
        logging_var = '{}, "redaction_level": "{}" {},'.format(logging_config, redact_level, "}")
    except KeyError as ex:
        log_info("Keyerror in getting logging{}".format(ex))
        logging_var = '{} {},'.format(logging_config, "}")

    if "macos" in sg_platform:
        sg_home_directory = "/Users/sync_gateway"
    elif sg_platform == "windows":
        sg_home_directory = "C:\\\\PROGRA~1\\\\Couchbase\\\\Sync Gateway"
    else:
        sg_home_directory = "/home/sync_gateway"

    if is_x509_auth(cluster_config):
        certpath_var = '"x509_cert_path": "{}/certs/chain.pem",'.format(sg_home_directory)
        keypath_var = '"x509_key_path": "{}/certs/pkey.key",'.format(sg_home_directory)
        cacertpath_var = '"ca_cert_path": "{}/certs/ca.pem",'.format(sg_home_directory)

        if sg_platform == "windows":
            certpath_var = certpath_var.replace("/", "\\\\")
            keypath_var = keypath_var.replace("/", "\\\\")
            cacertpath_var = cacertpath_var.replace("/", "\\\\")

        server_scheme_var = "couchbases"
        server_port_var = ""
        generate_x509_certs(cluster_config, bucket_names, sg_platform)
        x509_auth_var = True

    else:
        # username_playbook_var = '"username": "{}",'.format(read_bucket_user)
        username_playbook_var = '"username": "{}",'.format(bucket_names[0])
        username_var = bucket_names[0]
        password_var = "password"

    if is_cbs_ssl_enabled(cluster_config):
        server_scheme_var = "couchbases"
        server_port_var = "11207"
        block_http_vars = {}
        port_list = [8091, 8092, 8093, 8094, 8095, 8096, 11210, 11211]
        for port in port_list:
            block_http_vars["port"] = port
            status = ansible_runner.run_ansible_playbook(
                "block-http-ports.yml",
                extra_vars=block_http_vars
            )
            if status != 0:
                raise ProvisioningError("Failed to block port on SGW")

    if sg_ssl_enabled(cluster_config):
        if is_centralized_persistent_config_disabled(cluster_config):
                sslcert_var = '"SSLCert": "sg_cert.pem",'
                sslkey_var = '"SSLKey": "sg_privkey.pem",'
        else:
            tls_var = """ "https": {
                            "tls_cert_path": "sg_cert.pem",
                            "tls_key_path": "sg_privkey.pem"
                        }, """

        
    if is_hide_prod_version_enabled(cluster_config):
        hide_product_version_var = '"hide_product_version": true,'
    bucket_list_var = '"buckets": {},'.format(bucket_names)

    if is_centralized_persistent_config_disabled(cluster_config) and get_sg_version(cluster_config) >= "3.0.0":
        disable_persistent_config_var = '"disable_persistent_config": true,'

    if is_server_tls_skip_verify_enabled(cluster_config) and get_sg_version(cluster_config) >= "3.0.0":
        server_tls_skip_verify_var = '"server_tls_skip_verify": true,'

    if is_tls_server_disabled(cluster_config) and get_sg_version(cluster_config) >= "3.0.0":
        disable_tls_server_var = '"use_tls_server": false,'

    if is_admin_auth_disabled(cluster_config) and get_sg_version(cluster_config) >= "3.0.0":
        disable_admin_auth_var = '"admin_interface_authentication": false,    \n"metrics_interface_authentication": false,'

    if get_sg_version(cluster_config) >= "2.8.0":
        prometheus_var = '"metricsInterface": ":4986",'

    if get_sg_use_views(cluster_config):
        sg_use_views_var = '"use_views": true,'
    else:
        num_replicas = get_sg_replicas(cluster_config)
        num_index_replicas_var = '"num_index_replicas": {},'.format(num_replicas)

    # Add configuration to run with xattrs
    if is_xattrs_enabled(cluster_config):
        autoimport_var = '"import_docs": true,'
        xattrs_var = '"enable_shared_bucket_access": true,'

    if no_conflicts_enabled(cluster_config):
        no_conflicts_var = '"allow_conflicts": false,'

    try:
        revs_limit = get_revs_limit(cluster_config)
        revs_limit_var = '"revs_limit": {},'.format(revs_limit)

    except KeyError:
        log_info("revs_limit not found in {}, Ignoring".format(cluster_config))

    if is_delta_sync_enabled(cluster_config) and get_sg_version(cluster_config) >= "2.5.0":
        delta_sync_var = '"delta_sync": { "enabled": true},'

    db_username_var = '"username": "{}",'.format(username_var)
    db_password_var = '"password": "{}",'.format(password_var)
    db_bucket_var = '"bucket": "{}",'.format(bucket_names[0])

    template = Template(sgw_config_data)
    sgw_config_data = template.render(
        couchbase_server_primary_node=couchbase_server_primary_node,
        logging=logging_var,
        bootstrap_username=username_playbook_var,
        server_port=server_port_var,
        server_scheme=server_scheme_var,
        sg_cert_path=sg_cert_path,
        sslcert=sslcert_var,
        sslkey=sslkey_var,
        prometheus=prometheus_var,
        hide_product_version=hide_product_version_var,
        tls=tls_var,
        bucket_list=bucket_list_var,
        disable_persistent_config=disable_persistent_config_var,
        x509_certs_dir=cbs_cert_path,
        certpath=certpath_var,
        keypath=keypath_var,
        cacertpath=cacertpath_var,
        username=db_username_var,
        password=db_password_var,
        bucket=db_bucket_var,
        sg_use_views=sg_use_views_var,
        num_index_replicas=num_index_replicas_var,
        autoimport=autoimport_var,
        xattrs=xattrs_var,
        no_conflicts=no_conflicts_var,
        revs_limit=revs_limit_var,
        delta_sync=delta_sync_var,
        server_tls_skip_verify=server_tls_skip_verify_var,
        disable_tls_server=disable_tls_server_var,
        disable_admin_auth=disable_admin_auth_var
    )

    print("config_path _full is ", config_path_full)
    sg_config_path, database_config = seperate_sgw_and_db_config(sgw_config_data)
    # sg_config_path_full = os.path.abspath(sg_config_path)
    # Create bootstrap playbook vars
    bootstrap_playbook_vars = {
        "sync_gateway_config_filepath": cpc_config_path_full,
        "server_port": server_port_var,
        "server_scheme": server_scheme_var,
        "username": username_playbook_var,
        "password": db_password_var,
        "sg_cert_path": sg_cert_path,
        "sslcert": sslcert_var,
        "sslkey": sslkey_var,
        "prometheus": prometheus_var,
        "hide_product_version": hide_product_version_var,
        "tls": tls_var,
        "bucket_list": bucket_list_var,
        "disable_persistent_config": disable_persistent_config_var,
        "x509_auth": x509_auth_var,
        "x509_certs_dir": cbs_cert_path,
        "couchbase_server_primary_node": couchbase_server_primary_node,
        "logging": logging_var,
        "autoimport": autoimport_var,
        "xattrs": xattrs_var,
        "no_conflicts": no_conflicts_var,
        "sg_use_views": sg_use_views_var,
        "num_index_replicas": num_index_replicas_var,
        "disable_tls_server": disable_tls_server_var,
        "certpath": certpath_var,
        "keypath": keypath_var,
        "cacertpath": cacertpath_var,
        "delta_sync": delta_sync_var,
        "revs_limit": revs_limit_var,
        "server_tls_skip_verify": server_tls_skip_verify_var,
        "disable_admin_auth": disable_admin_auth_var
    }

    # config_path_full = os.path.abspath(sg_config_path)
    # convert database config to json data and create database config via rest api
    """ with open(database_config) as f:
        db_config_json = json.loads(f.read()) """

    # Sleep for a few seconds for the indexes to teardown
    time.sleep(5)

    """ status = ansible_runner.run_ansible_playbook(
        "start-sync-gateway.yml",
        extra_vars=bootstrap_playbook_vars
    )
    assert status == 0, "Failed to start to Sync Gateway"
    self.sync_gateways[0].admin.put_db_config(self, sg_db, db_config_json) """

    return bootstrap_playbook_vars, database_config, sgw_config_data


def get_buckets_from_sync_gateway_config(sync_gateway_config_path, cluster_config=None):
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

    config = Config(config_path_full, cluster_config)
    bucket_name_set = config.get_bucket_name_set()
    if os.path.exists(temp_config_path):
        os.remove(temp_config_path)
    return bucket_name_set


# TODO : Remove this if not required for now
def get_sync_gateway_dbconfig_path(config_prefix):
    """ Get SGW Database config path """
    config = "{}/{}_{}.json".format(SGW_DB_CONFIGS, config_prefix, "db")
    if not os.path.isfile(config):
        raise ValueError("Could not file config: {}".format(config))

    return config


def wait_until_doc_in_changes_feed(sg, db, doc_id):

    max_tries = 10
    sleep_retry_seconds = 1

    for attempt in range(max_tries):
        changes_results = sg.admin.get_global_changes(db)
        for changes_result in changes_results:
            if changes_result["id"] == doc_id:
                return

        time.sleep(sleep_retry_seconds)

    raise Exception("Tried to wait until doc {} showed up on changes feed, gave up".format(doc_id))


def wait_until_active_tasks_empty(sg):

    max_tries = 10
    sleep_retry_seconds = 1

    for attempt in range(max_tries):
        active_tasks = sg.admin.get_active_tasks()
        if len(active_tasks) == 0:
            return
        time.sleep(sleep_retry_seconds)

    raise Exception("Tried to wait until _active_tasks were empty, but they were never empty")


def wait_until_active_tasks_non_empty(sg):

    max_tries = 10
    sleep_retry_seconds = 1

    for attempt in range(max_tries):
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

    for attempt in range(max_tries_per_doc):
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


def send_dbconfig_as_restCall(db_config_json, sync_gateways, sgw_config_data):
    # convert database config for each sg db and send to rest end point
    # sg_dbs = database_config.keys()
    # time.sleep(30)

    for sgw in sync_gateways:
        print("db config json for sgw : ", sgw)
        sgw_db_config = db_config_json
        print("sgw_db_config.keys ", sgw_db_config.keys())
        # sync_func = None
        # imp_fltr_func = None
        roles_exist = False
        users_exist = False
        db_list = sgw.admin.get_dbs()
        print("db_list is ", db_list)
        """ import_filter_exist = False
        if "\"sync\":" in sgw_config_data:
            sync_func = sgw_config_data.split("\"sync\": `")[1]
            sync_func = sync_func.split("`")[0]
        if "\"import_filter\":" in sgw_config_data:
            imp_fltr_func = sgw_config_data.split("\"import_filter\": `")[1]
            imp_fltr_func = imp_fltr_func.split("`")[0]
            print("import filter with split: ", imp_fltr_func) """
        for sg_db in sgw_db_config.keys():
            """ if sg_db in db_list:
                print("deleting the sg db now... ", sg_db)
                print(sgw)
                sgw.admin.delete_db(sg_db) """
            # TODO : Should look for better place to delete 'server' key if tests usese old config
            if "server" in sgw_db_config[sg_db].keys():
                del sgw_db_config[sg_db]["server"]
            if "username" in sgw_db_config[sg_db].keys():
                del sgw_db_config[sg_db]["username"]
            if "password" in sgw_db_config[sg_db].keys():
                del sgw_db_config[sg_db]["password"]
            if "ca_cert_path" in sgw_db_config[sg_db].keys():
                del sgw_db_config[sg_db]["ca_cert_path"]
            if "x509_key_path" in sgw_db_config[sg_db].keys():
                del sgw_db_config[sg_db]["x509_key_path"]
            if "x509_cert_path" in sgw_db_config[sg_db].keys():
                del sgw_db_config[sg_db]["x509_cert_path"]
            if "roles" in sgw_db_config[sg_db].keys():
                roles_cfg = sgw_db_config[sg_db]["roles"]
                roles_exist = True
                del sgw_db_config[sg_db]["roles"]
            if "users" in sgw_db_config[sg_db].keys():
                users_cfg = sgw_db_config[sg_db]["users"]
                users_exist = True
                del sgw_db_config[sg_db]["users"]
            """if "sync" in sgw_db_config[sg_db].keys():
                sync_func = sgw_db_config[sg_db]["sync"]
                print("sync cfg func after extracting from sgw_db_config: ", sync_func)
                sync_func_exist = True
            if "import_filter" in sgw_db_config[sg_db].keys():
                imp_fltr_func = sgw_db_config[sg_db]["import_filter"]
                print("import filter cfg func after extracting from sgw_db_config: ", imp_fltr_func)
                import_filter_exist = True """
            try:
                sgw.admin.create_db(sg_db, sgw_db_config[sg_db])
            except HTTPError as e:
                """sgw.admin.delete_db(sg_db)
                time.sleep(1)
                sgw.admin.create_db(sg_db, sgw_db_config[sg_db])"""
                print("ignorning if db already exists in sync gateway", str(e))
                sgw.admin.put_db_config(sg_db, sgw_db_config[sg_db])
            db_info = sgw.admin.get_db_info(sg_db)
            if db_info["state"] == "Online":
                """ if sync_func_exist:
                    sgw.admin.create_sync_func(sg_db, sync_func) """
                if roles_exist:
                    for role in roles_cfg:
                        sgw.admin.create_role(sg_db, role, roles_cfg[role]['admin_channels'])
                if users_exist:
                    for user in users_cfg:
                        if roles_exist:
                            sgw.admin.register_user(sgw.ip, sg_db, user, users_cfg[user]['password'], channels=users_cfg[user]['admin_channels'], roles=users_cfg[user]['admin_roles'])
                        else:
                            sgw.admin.register_user(sgw.ip, sg_db, user, users_cfg[user]['password'], channels=users_cfg[user]['admin_channels'])
                """ if import_filter_exist:
                    sgw.admin.create_imp_fltr_func(sg_db, imp_fltr_func) """

            # TODO : Put back one CPC config works
            # sgw.admin.create_db_with_rest(sg_db, sgw_db_config[sg_db])
            # sgw.admin.put_db_config(sg_db, sgw_db_config[sg_db])


def create_logging_config(logging_config_json, sync_gateways):
    # convert database config for each sg db and send to rest end point
    # sg_dbs = database_config.keys()
    # time.sleep(30)
    from keywords.MobileRestClient import MobileRestClient
    client = MobileRestClient()
    for sgw in sync_gateways:
        print("logging config json for sgw : ", logging_config_json)
        client.create_logging_with_rest(sgw.admin.admin_url, logging_config_json)


def get_cpc_sgw_config(sg_config_path):
    # Get relavant cpc config for sgw config
    if SYNC_GATEWAY_CONFIGS_CPC not in sg_config_path and "temp_sg_config" not in sg_config_path:
        sg_config_path = sg_config_path.replace(SYNC_GATEWAY_CONFIGS, SYNC_GATEWAY_CONFIGS_CPC)
    return sg_config_path


def construct_dbconfig_json(db_config_file, cluster_config, sg_platform, sgw_config):
    db_config_path = "{}/{}.json".format(SGW_DB_CONFIGS, db_config_file)
    if not os.path.isfile(db_config_path):
        raise ValueError("Could not file config: {}".format(db_config_path))
    couchbase_server_primary_node = add_cbs_to_sg_config_server_field(cluster_config)
    couchbase_server_primary_node = get_cbs_primary_nodes_str(cluster_config, couchbase_server_primary_node)
    # bucket_names = get_buckets_from_sync_gateway_config(db_config_path, cluster_config)
    bucket_names = get_bucket_list_cpc(sgw_config)
    with open(db_config_path, "r") as config:
        db_config_data = config.read()

    autoimport_var = ""
    xattrs_var = ""
    no_conflicts_var = ""
    sg_use_views_var = ""
    num_index_replicas_var = ""
    username_var = ""
    password_var = "password"
    cacertpath_var = ""
    certpath_var = ""
    keypath_var = ""
    delta_sync_var = ""
    server_scheme_var = ""
    server_port_var = ""
    # x509_auth_var = False
    revs_limit_var = ""
    bucket_var = bucket_names[0]

    if "macos" in sg_platform:
        sg_home_directory = "/Users/sync_gateway"
    elif sg_platform == "windows":
        sg_home_directory = "C:\\\\PROGRA~1\\\\Couchbase\\\\Sync Gateway"
    else:
        sg_home_directory = "/home/sync_gateway"

    if is_x509_auth(cluster_config):
        certpath_var = '"certpath": "{}/certs/chain.pem",'.format(sg_home_directory)
        keypath_var = '"keypath": "{}/certs/pkey.key",'.format(sg_home_directory)
        cacertpath_var = '"cacertpath": "{}/certs/ca.pem",'.format(sg_home_directory)

        if sg_platform == "windows":
            certpath_var = certpath_var.replace("/", "\\\\")
            keypath_var = keypath_var.replace("/", "\\\\")
            cacertpath_var = cacertpath_var.replace("/", "\\\\")

        server_scheme_var = "couchbases"
        server_port_var = ""
        generate_x509_certs(cluster_config, bucket_names, sg_platform)
        # x509_auth_var = True

    else:
        username_var = bucket_names[0]

    if is_cbs_ssl_enabled(cluster_config):
        server_scheme_var = "couchbases"
        server_port_var = "11207"
    if get_sg_use_views(cluster_config):
        sg_use_views_var = '"use_views": true,'
    else:
        num_replicas = get_sg_replicas(cluster_config)
        num_index_replicas_var = '"num_index_replicas": {},'.format(num_replicas)

    # Add configuration to run with xattrs
    if is_xattrs_enabled(cluster_config):
        autoimport_var = '"import_docs": true,'
        xattrs_var = '"enable_shared_bucket_access": true,'

    if no_conflicts_enabled(cluster_config):
        no_conflicts_var = '"allow_conflicts": false,'

    try:
        revs_limit = get_revs_limit(cluster_config)
        revs_limit_var = '"revs_limit": {},'.format(revs_limit)

    except KeyError:
        log_info("revs_limit not found in {}, Ignoring".format(cluster_config))

    if is_delta_sync_enabled(cluster_config) and get_sg_version(cluster_config) >= "2.5.0":
        delta_sync_var = '"delta_sync": { "enabled": true},'

    db_username_var = '"username": "{}",'.format(username_var)
    db_password_var = '"password": "{}",'.format(password_var)
    db_bucket_var = '"bucket": "{}",'.format(bucket_var)
    template = Template(db_config_data)
    db_config_data = template.render(
        couchbase_server_primary_node=couchbase_server_primary_node,
        server_port=server_port_var,
        server_scheme=server_scheme_var,
        certpath=certpath_var,
        keypath=keypath_var,
        cacertpath=cacertpath_var,
        username=db_username_var,
        password=db_password_var,
        bucket=db_bucket_var,
        sg_use_views=sg_use_views_var,
        num_index_replicas=num_index_replicas_var,
        autoimport=autoimport_var,
        xattrs=xattrs_var,
        no_conflicts=no_conflicts_var,
        revs_limit=revs_limit_var,
        delta_sync=delta_sync_var
    )
    return db_config_data


def start_sgbinary(sg1, sg_platform, adminInterface=None, interface=None, cacertpath=None, certpath=None, configServer=None, dbname=None, defaultLogFilePath=None, disable_persistent_config=None, keypath=None, log=None, logFilePath=None, profileInterface=None, url=None):
    """-adminInterface string
    Address to bind admin interface to (default "127.0.0.1:4985")
  -cacertpath string
    Root CA certificate path
  -certpath string
    Client certificate path
  -configServer string
    URL of server that can return database configs
  -dbname string
    Name of Couchbase Server database (defaults to name of bucket)
  -defaultLogFilePath string
    Path to log files, if not overridden by --logFilePath, or the config
  -deploymentID string
    Customer/project identifier for stats reporting
  -disable_persistent_config
    Can be set to false to disable persistent config handling, and read all configuration from a legacy config file. (default true)
  -interface string
    Address to bind to (default ":4984")
  -keypath string
    Client certificate key path
  -log string
    Log keys, comma separated
  -logFilePath string
    Path to log files
  -pretty
    Pretty-print JSON responses
  -profileInterface string
    Address to bind profile interface to
  -url string
    Address of Couchbase server
  -verbose
    Log more info about requests """
    c_adminInterface = ""
    c_interface = ""
    c_cacertpath = ""
    c_certpath = ""
    c_configServer = ""
    c_dbname = ""
    c_defaultLogFilePath = ""
    c_disable_persistent_config = ""
    c_keypath = ""
    c_log = ""
    c_logFilePath = ""
    c_profileInterface = ""
    c_url = ""
    if adminInterface is not None:
        c_adminInterface = "-adminInterface=" + adminInterface
    if interface is not None:
        c_interface = "-interface=" + interface
    if cacertpath is not None:
        c_cacertpath = "-cacertpath=" + cacertpath
    if certpath is not None:
        c_certpath = "-certpath=" + certpath
    if configServer is not None:
        c_configServer = "-configServer=" + configServer
    if dbname is not None:
        c_dbname = "-dbname=" + dbname
    if defaultLogFilePath is not None:
        c_defaultLogFilePath = "-defaultLogFilePath=" + defaultLogFilePath
    if disable_persistent_config is not None:
        c_disable_persistent_config = "-disable_persistent_config={}".format(disable_persistent_config)
    if keypath is not None:
        c_keypath = "-keypath=" + keypath
    if log is not None:
        c_log = "-log=" + log
    if logFilePath is not None:
        c_logFilePath = "-logFilePath=" + logFilePath
    if profileInterface is not None:
        c_profileInterface = "-profileInterface " + profileInterface
    if url is not None:
        c_url = "-url=" + url
    remote_executor = RemoteExecutor(sg1.ip)
    if "macos" in sg_platform:
        sg_home_directory = "/Users/sync_gateway"
    elif sg_platform == "windows":
        sg_home_directory = "C:\\\\PROGRA~1\\\\Couchbase\\\\Sync Gateway"
    else:
        sg_home_directory = "/home/sync_gateway"
    command = "/opt/couchbase-sync-gateway/bin/sync_gateway {} {} {} {} {} {} {} {} {} {} {} {} {} {}/sync_gateway.json &".format(c_adminInterface, c_interface, c_cacertpath, c_certpath, c_configServer, c_dbname, c_defaultLogFilePath, c_disable_persistent_config, c_keypath, c_log, c_logFilePath, c_profileInterface, c_url, sg_home_directory)
    _, stdout, _ = remote_executor.execute(command)
    return stdout
