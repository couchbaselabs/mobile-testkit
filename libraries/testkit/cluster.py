import json
import os
import time
from jinja2 import Template
from requests.exceptions import ConnectionError

import keywords.exceptions
from keywords.couchbaseserver import CouchbaseServer
from keywords.exceptions import ProvisioningError
from keywords.utils import log_info, add_cbs_to_sg_config_server_field
from keywords.utils import version_and_build
from libraries.provision.ansible_runner import AnsibleRunner
from libraries.testkit.admin import Admin
from libraries.testkit.config import Config, seperate_sgw_and_db_config
from libraries.testkit.sgaccel import SgAccel
# from libraries.testkit.syncgateway import SyncGateway, send_dbconfig_as_restCall, create_logging_config
from libraries.testkit.syncgateway import SyncGateway, send_dbconfig_as_restCall
from libraries.testkit.syncgateway import get_buckets_from_sync_gateway_config
from utilities.cluster_config_utils import is_load_balancer_enabled, get_revs_limit, get_redact_level, is_load_balancer_with_two_clusters_enabled
from utilities.cluster_config_utils import get_load_balancer_ip, no_conflicts_enabled, is_delta_sync_enabled, get_sg_platform
from utilities.cluster_config_utils import generate_x509_certs, is_x509_auth, get_cbs_primary_nodes_str, is_hide_prod_version_enabled
from keywords.constants import SYNC_GATEWAY_CERT
from utilities.cluster_config_utils import get_sg_replicas, get_sg_use_views, get_sg_version
from utilities.cluster_config_utils import is_centralized_persistent_config_disabled, is_server_tls_skip_verify_enabled, is_admin_auth_disabled, is_tls_server_disabled


class Cluster:
    """
    An older remnant of first pass of Python API

    Before using or extending this, check keywords/ClusterKeywords.py to see if it already
    has this functionality
    """

    def __init__(self, config):

        self._cluster_config = config
        sgs = []
        cbs_urls = []
        acs = []

        if not os.path.isfile(self._cluster_config):
            log_info("Cluster config not found in 'resources/cluster_configs/'")
            raise IOError("Cluster config not found in 'resources/cluster_configs/'")

        log_info(self._cluster_config)

        # Load resources/cluster_configs/<cluster_config>.json
        with open("{}.json".format(config)) as f:
            cluster = json.loads(f.read())
        # Get load balancer IP
        lb_ip = None
        if is_load_balancer_with_two_clusters_enabled(self._cluster_config):
            # If load balancer is defined,
            # Switch all SG URLs to that of load balancer
            count = 0
            total_sgs_count = cluster["environment"]["sgw_cluster1_count"] + cluster["environment"]["sgw_cluster2_count"]
            for sg in cluster["sync_gateways"]:
                if count < cluster["environment"]["sgw_cluster1_count"]:
                    lb1_ip = cluster["load_balancers"][0]["ip"]
                    if cluster["environment"]["ipv6_enabled"]:
                        lb1_ip = "[{}]".format(lb1_ip)
                    sgs.append({"name": sg["name"], "ip": lb1_ip})
                elif count < total_sgs_count:
                    lb2_ip = cluster["load_balancers"][1]["ip"]
                    if cluster["environment"]["ipv6_enabled"]:
                        lb2_ip = "[{}]".format(lb2_ip)
                    sgs.append({"name": sg["name"], "ip": lb2_ip})
                count += 1
        elif is_load_balancer_enabled(self._cluster_config):
            # If load balancer is defined,
            # Switch all SG URLs to that of load balancer
            lb_ip = get_load_balancer_ip(self._cluster_config)

            for sg in cluster["sync_gateways"]:
                if cluster["environment"]["ipv6_enabled"]:
                    lb_ip = "[{}]".format(lb_ip)
                sgs.append({"name": sg["name"], "ip": lb_ip})
            log_info("Using load balancer IP as the SG IP: {}".format(sgs))
        else:
            for sg in cluster["sync_gateways"]:
                if cluster["environment"]["ipv6_enabled"]:
                    sg["ip"] = "[{}]".format(sg["ip"])
                sgs.append({"name": sg["name"], "ip": sg["ip"]})

        for ac in cluster["sg_accels"]:
            if cluster["environment"]["ipv6_enabled"]:
                ac["ip"] = "[{}]".format(ac["ip"])
            acs.append({"name": ac["name"], "ip": ac["ip"]})

        self.cbs_ssl = cluster["environment"]["cbs_ssl_enabled"]
        self.xattrs = cluster["environment"]["xattrs_enabled"]
        self.sync_gateway_ssl = cluster["environment"]["sync_gateway_ssl"]
        self.centralized_persistent_config = not cluster["environment"]["disable_persistent_config"]
        self.ipv6 = cluster["environment"]["ipv6_enabled"]

        if self.cbs_ssl:
            for cbs in cluster["couchbase_servers"]:
                if cluster["environment"]["ipv6_enabled"]:
                    cbs["ip"] = "[{}]".format(cbs["ip"])
                cbs_urls.append("https://{}:18091".format(cbs["ip"]))
        else:
            for cbs in cluster["couchbase_servers"]:
                if cluster["environment"]["ipv6_enabled"]:
                    cbs["ip"] = "[{}]".format(cbs["ip"])
                cbs_urls.append("http://{}:8091".format(cbs["ip"]))

        log_info("cbs: {}".format(cbs_urls))
        log_info("sgs: {}".format(sgs))
        log_info("acs: {}".format(acs))
        log_info("ssl: {}".format(self.cbs_ssl))

        self.sync_gateways = [SyncGateway(cluster_config=self._cluster_config, target=sg) for sg in sgs]
        self.sg_accels = [SgAccel(cluster_config=self._cluster_config, target=ac) for ac in acs]
        self.servers = [CouchbaseServer(url=cb_url) for cb_url in cbs_urls]
        self.sync_gateway_config = None  # will be set to Config object when reset() called

    def reset(self, sg_config_path, bucket_list=[], use_config=False, sgdb_creation=True):

        ansible_runner = AnsibleRunner(self._cluster_config)

        log_info(">>> Reseting cluster ...")
        log_info(">>> CBS SSL enabled: {}".format(self.cbs_ssl))
        log_info(">>> Using xattrs: {}".format(self.xattrs))

        # Stop sync_gateways
        log_info(">>> Stopping sync_gateway")
        status = ansible_runner.run_ansible_playbook("stop-sync-gateway.yml")
        assert status == 0, "Failed to stop sync gateway"

        # Stop sync_gateway accels
        log_info(">>> Stopping sg_accel")
        status = ansible_runner.run_ansible_playbook("stop-sg-accel.yml")
        assert status == 0, "Failed to stop sg_accel"

        # Deleting sync_gateway artifacts
        log_info(">>> Deleting sync_gateway artifacts")
        status = ansible_runner.run_ansible_playbook("delete-sync-gateway-artifacts.yml")
        assert status == 0, "Failed to delete sync_gateway artifacts"

        # Deleting sg_accel artifacts
        log_info(">>> Deleting sg_accel artifacts")
        status = ansible_runner.run_ansible_playbook("delete-sg-accel-artifacts.yml")
        assert status == 0, "Failed to delete sg_accel artifacts"

        # Delete buckets
        log_info(">>> Deleting buckets on: {}".format(self.servers[0].url))
        self.servers[0].delete_buckets()
        # Parse config and grab bucket names
        config_path_full = os.path.abspath(sg_config_path)
        config = Config(config_path_full, self._cluster_config, bucket_list=bucket_list)
        self.sync_gateway_config = config
        mode = config.get_mode()

        if get_sg_version(self._cluster_config) >= "3.0.0" and not is_centralized_persistent_config_disabled(self._cluster_config):
            playbook_vars, db_config_json, sgw_config_data = self.setup_server_and_sgw(sg_config_path=sg_config_path, bucket_list=bucket_list, use_config=use_config)
        else:
            bucket_name_set = config.get_bucket_name_set()
            sg_cert_path = os.path.abspath(SYNC_GATEWAY_CERT)
            cbs_cert_path = os.path.join(os.getcwd(), "certs")
            bucket_names = get_buckets_from_sync_gateway_config(sg_config_path, self._cluster_config)

            is_valid, reason = validate_cluster(self.sync_gateways, self.sg_accels, config)
            if not is_valid:
                raise ProvisioningError(reason)

            log_info(">>> Creating buckets on: {}".format(self.servers[0].url))
            log_info(">>> Creating buckets {}".format(bucket_name_set))
            self.servers[0].create_buckets(bucket_names=bucket_name_set,
                                           cluster_config=self._cluster_config,
                                           ipv6=self.ipv6)

            # Wait for server to be in a warmup state to work around
            # https://github.com/couchbase/sync_gateway/issues/1745
            log_info(">>> Waiting for Server: {} to be in a healthy state".format(self.servers[0].url))
            self.servers[0].wait_for_ready_state()

            log_info(">>> Starting sync_gateway with configuration: {}".format(config_path_full))

            server_port = 8091
            server_scheme = "http"
            couchbase_server_primary_node = add_cbs_to_sg_config_server_field(self._cluster_config)
            if self.cbs_ssl:
                server_port = 18091
                server_scheme = "https"

            couchbase_server_primary_node = get_cbs_primary_nodes_str(self._cluster_config, couchbase_server_primary_node)

            # Start sync-gateway
            playbook_vars = {
                "sync_gateway_config_filepath": config_path_full,
                "username": "",
                "password": "",
                "certpath": "",
                "keypath": "",
                "cacertpath": "",
                "x509_certs_dir": cbs_cert_path,
                "x509_auth": False,
                "sg_cert_path": sg_cert_path,
                "server_port": server_port,
                "server_scheme": server_scheme,
                "autoimport": "",
                "xattrs": "",
                "no_conflicts": "",
                "revs_limit": "",
                "sslcert": "",
                "sslkey": "",
                "num_index_replicas": "",
                "sg_use_views": "",
                "couchbase_server_primary_node": couchbase_server_primary_node,
                "delta_sync": "",
                "prometheus": "",
                "hide_product_version": "",
                "tls": "",
                "disable_persistent_config": "",
                "server_tls_skip_verify": "",
                "disable_tls_server": "",
                "disable_admin_auth": ""
            }

            sg_platform = get_sg_platform(self._cluster_config)
            if get_sg_version(self._cluster_config) >= "2.1.0":
                logging_config = '"logging": {"debug": {"enabled": true}'
                try:
                    redact_level = get_redact_level(self._cluster_config)
                    playbook_vars["logging"] = '{}, "redaction_level": "{}" {},'.format(logging_config, redact_level, "}")
                except KeyError as ex:
                    log_info("Keyerror in getting logging{}".format(ex))
                    playbook_vars["logging"] = '{} {},'.format(logging_config, "}")
                if get_sg_use_views(self._cluster_config):
                    playbook_vars["sg_use_views"] = '"use_views": true,'
                else:
                    num_replicas = get_sg_replicas(self._cluster_config)
                    playbook_vars["num_index_replicas"] = '"num_index_replicas": {},'.format(num_replicas)

                if "macos" in sg_platform:
                    sg_home_directory = "/Users/sync_gateway"
                elif sg_platform == "windows":
                    sg_home_directory = "C:\\\\PROGRA~1\\\\Couchbase\\\\Sync Gateway"
                else:
                    sg_home_directory = "/home/sync_gateway"

                if is_x509_auth(self._cluster_config):
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
                    generate_x509_certs(self._cluster_config, bucket_names, sg_platform)
                else:
                    playbook_vars["username"] = '"username": "{}",'.format(
                        bucket_names[0])
                    playbook_vars["password"] = '"password": "password",'
            else:
                playbook_vars["logging"] = '"log": ["*"],'
                playbook_vars["username"] = '"username": "{}",'.format(
                    bucket_names[0])
                playbook_vars["password"] = '"password": "password",'

            if self.cbs_ssl and get_sg_version(self._cluster_config) >= "1.5.0":
                playbook_vars["server_scheme"] = "couchbases"
                playbook_vars["server_port"] = 11207
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
            # Add configuration to run with xattrs
            if self.xattrs:
                if get_sg_version(self._cluster_config) >= "2.1.0":
                    playbook_vars["autoimport"] = '"import_docs": true,'
                else:
                    playbook_vars["autoimport"] = '"import_docs": "continuous",'
                playbook_vars["xattrs"] = '"enable_shared_bucket_access": true,'

            if self.sync_gateway_ssl:
                if self.centralized_persistent_config:
                    playbook_vars["tls"] = """ "https": {
                             "tls_cert_path": "sg_cert.pem",
                             "tls_key_path": "sg_privkey.pem"
                            }, """
                else:
                    playbook_vars["sslcert"] = '"SSLCert": "sg_cert.pem",'
                    playbook_vars["sslkey"] = '"SSLKey": "sg_privkey.pem",'

            if no_conflicts_enabled(self._cluster_config):
                playbook_vars["no_conflicts"] = '"allow_conflicts": false,'
            try:
                revs_limit = get_revs_limit(self._cluster_config)
                playbook_vars["revs_limit"] = '"revs_limit": {},'.format(revs_limit)
            except KeyError:
                log_info("revs_limit not found in {}, Ignoring".format(self._cluster_config))
                playbook_vars["revs_limit"] = ''

            if is_delta_sync_enabled(self._cluster_config) and get_sg_version(self._cluster_config) >= "2.5.0":
                playbook_vars["delta_sync"] = '"delta_sync": { "enabled": true},'

            if get_sg_version(self._cluster_config) >= "2.8.0":
                playbook_vars["prometheus"] = '"metricsInterface": ":4986",'

            if is_hide_prod_version_enabled(self._cluster_config) and get_sg_version(self._cluster_config) >= "2.8.1":
                playbook_vars["hide_product_version"] = '"hide_product_version": true,'

            if is_centralized_persistent_config_disabled(self._cluster_config) and get_sg_version(self._cluster_config) >= "3.0.0":
                playbook_vars["disable_persistent_config"] = '"disable_persistent_config": true,'

            if is_server_tls_skip_verify_enabled(self._cluster_config) and get_sg_version(self._cluster_config) >= "3.0.0":
                playbook_vars["server_tls_skip_verify"] = '"server_tls_skip_verify": true,'

            if is_tls_server_disabled(self._cluster_config) and get_sg_version(self._cluster_config) >= "3.0.0":
                playbook_vars["disable_tls_server"] = '"use_tls_server": false,'

            if is_admin_auth_disabled(self._cluster_config) and get_sg_version(self._cluster_config) >= "3.0.0":
                playbook_vars["disable_admin_auth"] = '"admin_interface_authentication": false,    \n"metrics_interface_authentication": false,'

            # Sleep for a few seconds for the indexes to teardown
            time.sleep(5)
            # time.sleep(30)

        status = ansible_runner.run_ansible_playbook(
            "start-sync-gateway.yml",
            extra_vars=playbook_vars
        )
        assert status == 0, "Failed to start to Sync Gateway"

        # HACK - only enable sg_accel for distributed index tests
        # revise this with https://github.com/couchbaselabs/sync-gateway-testcluster/issues/222
        if mode == "di":
            # Start sg-accel
            status = ansible_runner.run_ansible_playbook(
                "start-sg-accel.yml",
                extra_vars=playbook_vars
            )
            assert status == 0, "Failed to start sg_accel"

        # Validate CBGT
        if mode == "di":
            if not self.validate_cbgt_pindex_distribution_retry(len(self.sg_accels)):
                self.save_cbgt_diagnostics()
                raise Exception("Failed to validate CBGT Pindex distribution")
            log_info(">>> Detected valid CBGT Pindex distribution")
        else:
            log_info(">>> Running in channel cache")

        if status == 0 and sgdb_creation:
            time.sleep(5)  # give a time afer restart to create db config, change to 60 if it fails
            if get_sg_version(self._cluster_config) >= "3.0.0" and not is_centralized_persistent_config_disabled(self._cluster_config):
                # Now create rest API for all database configs
                send_dbconfig_as_restCall(self._cluster_config, db_config_json, self.sync_gateways, sgw_config_data)

        return mode

    def setup_server_and_sgw(self, sg_config_path, bucket_creation=True, bucket_list=[], use_config=False, sync_gateway_version=None):
        # Parse config and grab bucket names
        ansible_runner = AnsibleRunner(self._cluster_config)
        sg_conf_name = "sync_gateway_default"
        mode = "cc"
        if sync_gateway_version:
            version, _ = version_and_build(sync_gateway_version)
        else:
            version = get_sg_version(self._cluster_config)
        # cannot import at file level due to conflicts, this is needed just for this method
        from keywords.SyncGateway import sync_gateway_config_path_for_mode, get_cpc_config_from_config_path
        cpc_sgw_config_path = sync_gateway_config_path_for_mode(sg_conf_name, mode, cpc=True)
        if use_config:
            if use_config is True:
                cpc_sgw_config_path = get_cpc_config_from_config_path(sg_config_path, mode)
                sg_config_path = sync_gateway_config_path_for_mode(sg_conf_name, mode)
            else:
                cpc_sgw_config_path = sg_config_path
                sg_config_path = use_config

        cpc_config_path_full = os.path.abspath(cpc_sgw_config_path)
        config_path_full = os.path.abspath(sg_config_path)
        config = Config(config_path_full, self._cluster_config, bucket_list=bucket_list)
        if not bucket_list:
            bucket_name_set = config.get_bucket_name_set()
        else:
            bucket_name_set = bucket_list
        sg_cert_path = os.path.abspath(SYNC_GATEWAY_CERT)
        cbs_cert_path = os.path.join(os.getcwd(), "certs")

        bucket_names = bucket_name_set
        common_bucket_user = "bucket-admin"
        self.sync_gateway_config = config

        if bucket_creation:
            log_info(">>> Creating buckets on: {}".format(self.servers[0].url))
            log_info(">>> Creating buckets {}".format(bucket_name_set))
            self.servers[0].create_buckets(bucket_names=bucket_name_set, cluster_config=self._cluster_config, ipv6=self.ipv6)
            log_info(">>> Waiting for Server: {} to be in a healthy state".format(self.servers[0].url))
            self.servers[0].wait_for_ready_state()
        self.servers[0]._create_internal_rbac_user_by_roles('*', self._cluster_config, common_bucket_user, "mobile_sync_gateway")
        log_info(">>> Starting sync_gateway with configuration using setup_server_and_sgw: {}".format(cpc_config_path_full))

        # Extracing sgw config from sgw config file
        with open(config_path_full, "r") as config:
            sgw_config_data = config.read()

        # Extracting cluster from cluster config
        with open("{}.json".format(self._cluster_config)) as f:
            cluster = json.loads(f.read())

        server_scheme_var = "couchbase"
        server_port_var = ""
        couchbase_server_primary_node = add_cbs_to_sg_config_server_field(self._cluster_config)
        if self.cbs_ssl:
            server_port_var = 18091
            server_scheme_var = "https"

        couchbase_server_primary_node = get_cbs_primary_nodes_str(self._cluster_config, couchbase_server_primary_node)
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
        username_var = ""
        sg_use_views_var = ""
        num_index_replicas_var = ""
        autoimport_var = '"import_docs": false,'
        xattrs_var = '"enable_shared_bucket_access": false,'
        no_conflicts_var = ""
        revs_limit_var = ""
        delta_sync_var = ""
        disable_persistent_config_var = ""
        server_tls_skip_verify_var = ""
        disable_tls_server_var = ""
        disable_admin_auth_var = ""
        group_id_var = ""
        webhook_ip_var = cluster["webhook_ip"][0]["ip"]

        sg_platform = get_sg_platform(self._cluster_config)

        logging_config = '"logging": {"debug": {"enabled": true}'
        try:
            redact_level = get_redact_level(self._cluster_config)
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

        if is_x509_auth(self._cluster_config):
            certpath_var = '"x509_cert_path": "{}/certs/chain.pem",'.format(sg_home_directory)
            keypath_var = '"x509_key_path": "{}/certs/pkey.key",'.format(sg_home_directory)
            cacertpath_var = '"ca_cert_path": "{}/certs/ca.pem",'.format(sg_home_directory)

            if sg_platform == "windows":
                certpath_var = certpath_var.replace("/", "\\\\")
                keypath_var = keypath_var.replace("/", "\\\\")
                cacertpath_var = cacertpath_var.replace("/", "\\\\")

            server_scheme_var = "couchbases"
            server_port_var = ""
            generate_x509_certs(self._cluster_config, bucket_names, sg_platform)
            x509_auth_var = True

        else:
            username_playbook_var = '"username": "{}",'.format(common_bucket_user)
            username_var = '"username": "{}",'.format(bucket_names[0])
            password_var = '"password": "password",'

        if self.cbs_ssl:
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

        if self.sync_gateway_ssl:
            if not is_centralized_persistent_config_disabled(self._cluster_config):
                tls_var = """ "https": {
                             "tls_cert_path": "sg_cert.pem",
                             "tls_key_path": "sg_privkey.pem"
                            }, """
            else:
                sslcert_var = '"SSLCert": "sg_cert.pem",'
                sslkey_var = '"SSLKey": "sg_privkey.pem",'
        if is_hide_prod_version_enabled(self._cluster_config):
            hide_product_version_var = '"hide_product_version": true,'
        bucket_list_var = '"buckets": {},'.format(bucket_names)

        group_id_var = '"group_id": "{}",'.format(bucket_names[0])
        if is_centralized_persistent_config_disabled(self._cluster_config) and version >= "3.0.0":
            disable_persistent_config_var = '"disable_persistent_config": true,'

        if is_server_tls_skip_verify_enabled(self._cluster_config) and version >= "3.0.0":
            server_tls_skip_verify_var = '"server_tls_skip_verify": true,'

        if is_tls_server_disabled(self._cluster_config) and version >= "3.0.0":
            disable_tls_server_var = '"use_tls_server": false,'

        if is_admin_auth_disabled(self._cluster_config) and version >= "3.0.0":
            disable_admin_auth_var = '"admin_interface_authentication": false,    \n"metrics_interface_authentication": false,'

        if version >= "2.8.0":
            prometheus_var = '"metrics_interface": ":4986",'

        if get_sg_use_views(self._cluster_config):
            sg_use_views_var = '"use_views": true,'
        else:
            num_replicas = get_sg_replicas(self._cluster_config)
            num_index_replicas_var = '"num_index_replicas": {},'.format(num_replicas)

        # Add configuration to run with xattrs
        if self.xattrs:
            if version >= "2.1.0":
                autoimport_var = '"import_docs": true,'
            else:
                autoimport_var = '"import_docs": "continuous",'
            xattrs_var = '"enable_shared_bucket_access": true,'

        if no_conflicts_enabled(self._cluster_config):
            no_conflicts_var = '"allow_conflicts": false,'

        try:
            revs_limit = get_revs_limit(self._cluster_config)
            revs_limit_var = '"revs_limit": {},'.format(revs_limit)

        except KeyError:
            log_info("revs_limit not found in {}, Ignoring".format(self._cluster_config))

        if is_delta_sync_enabled(self._cluster_config) and version >= "2.5.0":
            delta_sync_var = '"delta_sync": { "enabled": true},'

        db_bucket_var = '"bucket": "{}",'.format(bucket_names[0])
        # Replace values with string on sgw config data

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
            username=username_var,
            password=password_var,
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
            disable_admin_auth=disable_admin_auth_var,
            webhook_ip=webhook_ip_var,
            groupid=group_id_var
        )
        sg_config_path, database_config = seperate_sgw_and_db_config(sgw_config_data)
        db_config_json = database_config
        # Create bootstrap playbook vars
        bootstrap_playbook_vars = {
            "sync_gateway_config_filepath": cpc_config_path_full,
            "server_port": server_port_var,
            "server_scheme": server_scheme_var,
            "username": username_playbook_var,
            "password": password_var,
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
            "disable_admin_auth": disable_admin_auth_var,
            "webhook_ip": webhook_ip_var,
            "groupid": group_id_var
        }
        # Sleep for a few seconds for the indexes to teardown
        time.sleep(5)
        return bootstrap_playbook_vars, db_config_json, sgw_config_data

    def restart_services(self):
        ansible_runner = AnsibleRunner(self._cluster_config)
        status = ansible_runner.run_ansible_playbook(
            "restart-services.yml",
            extra_vars={}
        )
        assert status == 0, "Failed to restart services"

    def save_cbgt_diagnostics(self):

        # CBGT REST Admin API endpoint
        for sync_gateway_writer in self.sg_accels:

            adminApi = Admin(sync_gateway_writer)
            cbgt_diagnostics = adminApi.get_cbgt_diagnostics()
            adminApi.get_cbgt_config()

            # dump raw diagnostics
            pretty_print_json = json.dumps(cbgt_diagnostics, sort_keys=True, indent=4, separators=(',', ': '))
            log_info("SG {} CBGT diagnostic output: {}".format(sync_gateway_writer, pretty_print_json))

    def validate_cbgt_pindex_distribution_retry(self, num_running_sg_accels):
        """
        Validates the CBGT pindex distribution by looking for nodes that don't have
        any pindexes assigned to it
        """
        for i in range(10):
            is_valid = self.validate_cbgt_pindex_distribution(num_running_sg_accels)
            if is_valid:
                return True
            else:
                log_info("Could not validate CBGT Pindex distribution.  Will retry after sleeping ..")
                time.sleep(5)

        return False

    def validate_cbgt_pindex_distribution(self, num_running_sg_accels):

        if num_running_sg_accels < 1:
            raise keywords.exceptions.ClusterError("Need at least one sg_accel running to verify pindexes")

        # build a map of node -> num_pindexes
        node_defs_pindex_counts = {}

        # CBGT REST Admin API endpoint
        adminApi = Admin(self.sg_accels[0])
        cbgt_cfg = adminApi.get_cbgt_config()

        # loop over the planpindexes and update the count for the node where it lives
        # this will end up with a dictionary like:
        #  {'74c818f04b99b169': 32, '11886131c807a30e': 32}  (each node uuid has 32 pindexes)
        plan_pindexes = cbgt_cfg.p_indexes
        for data_bucket_key, data_bucket_val in plan_pindexes.items():

            # get the nodes where this pindex lives
            nodes = data_bucket_val["nodes"]
            # it should only live on one node.  if not, abort.
            if len(nodes) > 1:
                raise Exception("Unexpected: a CBGT Pindex was assigned to more than one node")
            # loop over the nodes where this pindex lives and increment the count
            for node in nodes:

                # add a key for this node if we don't already have one
                if node not in node_defs_pindex_counts:
                    node_defs_pindex_counts[node] = 0

                current_pindex_count = node_defs_pindex_counts[node]
                current_pindex_count += 1
                node_defs_pindex_counts[node] = current_pindex_count

        log_info("CBGT node to pindex counts: {}".format(node_defs_pindex_counts))

        # make sure number of unique node uuids is equal to the number of sync gateway writers
        if len(node_defs_pindex_counts) != num_running_sg_accels:
            log_info("CBGT len(unique_node_uuids) != len(self.sync_gateway_writers) ({} != {})".format(
                len(node_defs_pindex_counts),
                num_running_sg_accels
            ))
            return False

        # make sure that all of the nodes have approx the same number of pindexes assigneed to them
        i = 0
        num_pindex_first_node = 0
        for node_def_uuid, num_pindexes in node_defs_pindex_counts.items():

            if i == 0:
                # it's the first node we've looked at, just record number of pindexes and continue
                num_pindex_first_node = num_pindexes
                i += 1
                continue

            # ok, it's the 2nd+ node, make sure the delta with the first node is less than or equal to 1
            # (the reason we can't compare for equality is that sometimes the pindexes can't be
            # divided evenly across the cluster)
            delta = abs(num_pindex_first_node - num_pindexes)
            if delta > 1:
                log_info("CBGT Sync Gateway node {} has {} pindexes, but other node has {} pindexes.".format(
                    node_def_uuid,
                    num_pindexes,
                    num_pindex_first_node
                ))
                return False

        return True

    def verify_alive(self, mode="cc"):
        errors = []
        for sg in self.sync_gateways:
            try:
                info = sg.info()
                log_info(" verify_alive sync_gateway : {}, info: {}".format(sg.url, info))
            except ConnectionError as e:
                log_info("verify_alive sync_gateway down: {}".format(e))
                errors.append((sg, e))

        if mode == "di":
            for sa in self.sg_accels:
                try:
                    info = sa.info()
                    log_info("sg_accel: {}, info: {}".format(sa.url, info))
                except ConnectionError as e:
                    log_info("sg_accel down: {}".format(e))
                    errors.append((sa, e))

        return errors

    def stop_sg_and_accel(self):

        # Stop sync_gateways
        log_info(">>> Stopping sync_gateway")
        for sg in self.sync_gateways:
            status = sg.stop()
            assert status == 0, "Failed to stop sync gateway for host {}".format(sg.hostname)

        # Stop sync_gateway accels
        log_info(">>> Stopping sg_accel")
        for sgaccel in self.sg_accels:
            status = sgaccel.stop()
            assert status == 0, "Failed to stop sync gateway for host {}".format(sgaccel.hostname)

    def __repr__(self):
        s = "\n\n"
        s += "Sync Gateways\n"
        for sg in self.sync_gateways:
            s += str(sg)
        s += "\nSync Gateway Accels\n"
        for sgw in self.sg_accels:
            s += str(sgw)
        s += "\nCouchbase Servers\n"
        for server in self.servers:
            s += str(server)
        s += "\n"
        return s


def validate_cluster(sync_gateways, sg_accels, config):

    # Validate sync gateways
    if len(sync_gateways) == 0:
        return False, "Functional tests require at least 1 index reader"

    # If we are using a Distributed Index config, make sure that we have sg-accels
    if config.mode == "di" and len(sg_accels) == 0:
        return False, "INVALID CONFIG: Running in Distributed Index mode but no sg_accels are defined."

    return True, ""
