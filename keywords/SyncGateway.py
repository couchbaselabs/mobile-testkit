import os
import json

import requests
from requests import Session
from jinja2 import Template
import time
import re
from keywords.constants import SYNC_GATEWAY_CONFIGS, SYNC_GATEWAY_CERT
from keywords.utils import version_is_binary, add_cbs_to_sg_config_server_field
from keywords.utils import log_r
from keywords.utils import version_and_build
from keywords.utils import hostname_for_url
from keywords.utils import log_info
from utilities.cluster_config_utils import get_revs_limit, is_x509_auth, generate_x509_certs, get_cbs_primary_nodes_str
from keywords.exceptions import ProvisioningError, Error
from libraries.provision.ansible_runner import AnsibleRunner
from utilities.cluster_config_utils import is_cbs_ssl_enabled, is_xattrs_enabled, no_conflicts_enabled, get_redact_level, get_sg_platform
from utilities.cluster_config_utils import get_sg_replicas, get_sg_use_views, get_sg_version, sg_ssl_enabled, get_cbs_version, is_delta_sync_enabled
from utilities.cluster_config_utils import is_hide_prod_version_enabled
from libraries.testkit.syncgateway import get_buckets_from_sync_gateway_config
from libraries.testkit.cluster import Cluster
from keywords.utils import host_for_url
from keywords import document
from keywords.utils import random_string
from utilities.cluster_config_utils import copy_sgconf_to_temp, replace_string_on_sgw_config, get_cluster
from utilities.cluster_config_utils import is_centralized_persistent_config_disabled, is_server_tls_skip_verify_enabled, is_admin_auth_disabled, is_tls_server_disabled


def validate_sync_gateway_mode(mode):
    """Verifies that the sync_gateway mode is either channel cache ('cc') or distributed index ('di')"""
    if mode != "cc" and mode != "di":
        raise ValueError("Sync Gateway mode must be 'cc' (channel cache) or 'di' (distributed index)")


def sync_gateway_config_path_for_mode(config_prefix, mode):
    """Construct a sync_gateway config path depending on a mode
    1. Check that mode is valid ("cc" or "di")
    2. Construct the config path relative to the root of the repository
    3. Make sure the config exists
    """

    validate_sync_gateway_mode(mode)

    # Construct expected config path
    config = "{}/{}_{}.json".format(SYNC_GATEWAY_CONFIGS, config_prefix, mode)
    if not os.path.isfile(config):
        raise ValueError("Could not file config: {}".format(config))

    return config


def get_sync_gateway_version(host):
    sg_scheme = "http"
    cluster_config = os.environ["CLUSTER_CONFIG"]
    if sg_ssl_enabled(cluster_config):
        sg_scheme = "https"

    resp = requests.get("{}://{}:4985".format(sg_scheme, host), verify=False)
    log_r(resp)
    resp.raise_for_status()
    resp_obj = resp.json()

    running_version = resp_obj["version"]
    running_version_parts = re.split("[ /(;)]", running_version)

    # Vendor version is parsed as a float, convert so it can be compared with full version strings
    running_vendor_version = str(resp_obj["vendor"]["version"])

    if running_version_parts[3] == "HEAD":
        # Example: resp_obj["version"] = Couchbase Sync Gateway/HEAD(nobranch)(e986c8a)
        running_version_formatted = running_version_parts[6]
    else:
        # Example: resp_obj["version"] = "Couchbase Sync Gateway/1.3.0(183;bfe61c7)"
        running_version_formatted = "{}-{}".format(running_version_parts[3], running_version_parts[4])

    # Returns the version as 338493 commit format or 1.2.1-4 version format
    return running_version_formatted, running_vendor_version


def verify_sync_gateway_product_info(host):
    """ Get the product information from host and verify for Sync Gateway:
    - vendor name in GET / request
    - Server header in response
    """
    sg_scheme = "http"
    cluster_config = os.environ["CLUSTER_CONFIG"]
    if sg_ssl_enabled(cluster_config):
        sg_scheme = "https"

    resp = requests.get("{}://{}:4984".format(sg_scheme, host), verify=False)
    log_r(resp)
    resp.raise_for_status()
    resp_obj = resp.json()

    server_header = resp.headers["server"]
    log_info("'server' header: {}".format(server_header))
    if not server_header.startswith("Couchbase Sync Gateway"):
        raise ProvisioningError("Wrong product info. Expected 'Couchbase Sync Gateway'")

    vendor_name = resp_obj["vendor"]["name"]
    log_info("vendor name: {}".format(vendor_name))
    if vendor_name != "Couchbase Sync Gateway":
        raise ProvisioningError("Wrong vendor name. Expected 'Couchbase Sync Gateway'")


def verify_sync_gateway_version(host, expected_sync_gateway_version):
    sg_released_version = {
        "1.4.1.3": "1",
        "1.5.0": "594",
        "1.5.1": "4",
        "2.0.0": "832",
        "2.1.0": "121",
        "2.1.1": "17",
        "2.1.2": "86",
        "2.1.3.1": "2",
        "2.5.0": "271",
        "2.6.0": "127",
        "2.7.0": "166",
        "2.8.0": "376",
        "2.8.0.1": "3",
        "2.8.2": "1"
    }
    version, build = version_and_build(expected_sync_gateway_version)
    if build is None:
        expected_sync_gateway_version = "{}-{}".format(version,
                                                       sg_released_version[version])
    running_sg_version, running_sg_vendor_version = get_sync_gateway_version(host)

    log_info("Expected sync_gateway Version: {}".format(expected_sync_gateway_version))
    log_info("Running sync_gateway Version: {}".format(running_sg_version))
    log_info("Running sync_gateway Vendor Version: {}".format(running_sg_vendor_version))

    if version_is_binary(expected_sync_gateway_version):
        # Example, 1.2.1-4
        if running_sg_version != expected_sync_gateway_version:
            raise ProvisioningError("Unexpected sync_gateway version!! Expected: {} Actual: {}".format(expected_sync_gateway_version, running_sg_version))
        # Running vendor version: ex. '1.2', check that the expected version start with the vendor version
        if not expected_sync_gateway_version.startswith(running_sg_vendor_version):
            raise ProvisioningError("Unexpected sync_gateway vendor version!! Expected: {} Actual: {}".format(expected_sync_gateway_version, running_sg_vendor_version))
    else:
        # Since sync_gateway does not return the full commit, verify the prefix
        if running_sg_version != expected_sync_gateway_version[:7]:
            raise ProvisioningError("Unexpected sync_gateway version!! Expected: {} Actual: {}".format(expected_sync_gateway_version, running_sg_version))


def get_sg_accel_version(host):
    sg_scheme = "http"
    cluster_config = os.environ["CLUSTER_CONFIG"]
    if sg_ssl_enabled(cluster_config):
        sg_scheme = "https"

    resp = requests.get("{}://{}:4985".format(sg_scheme, host), verify=False)
    log_r(resp)
    resp.raise_for_status()
    resp_obj = resp.json()

    running_version = resp_obj["version"]
    running_version_parts = re.split("[ /(;)]", running_version)

    if running_version_parts[3] == "HEAD":
        running_version_formatted = running_version_parts[6]
    else:
        running_version_formatted = "{}-{}".format(running_version_parts[3], running_version_parts[4])

    # Returns the version as 338493 commit format or 1.2.1-4 version format
    return running_version_formatted


def verify_sg_accel_product_info(host):
    """ Get the product information from host and verify for SG Accel:
    - vendor name in GET / request
    - Server header in response
    """
    sg_scheme = "http"
    cluster_config = os.environ["CLUSTER_CONFIG"]
    if sg_ssl_enabled(cluster_config):
        sg_scheme = "https"

    resp = requests.get("{}://{}:4985".format(sg_scheme, host), verify=False)
    log_r(resp)
    resp.raise_for_status()
    resp_obj = resp.json()

    server_header = resp.headers["server"]
    log_info("'server' header: {}".format(server_header))
    if not server_header.startswith("Couchbase SG Accel"):
        raise ProvisioningError("Wrong product info. Expected 'Couchbase SG Accel'")

    vendor_name = resp_obj["vendor"]["name"]
    log_info("vendor name: {}".format(vendor_name))
    if vendor_name != "Couchbase SG Accel":
        raise ProvisioningError("Wrong vendor name. Expected 'Couchbase SG Accel'")


def verify_sg_accel_version(host, expected_sg_accel_version):
    running_ac_version = get_sg_accel_version(host)

    log_info("Expected sg_accel Version: {}".format(expected_sg_accel_version))
    log_info("Running sg_accel Version: {}".format(running_ac_version))

    if version_is_binary(expected_sg_accel_version):
        # Example, 1.2.1-4
        if running_ac_version != expected_sg_accel_version:
            raise ProvisioningError("Unexpected sync_gateway version!! Expected: {} Actual: {}".format(expected_sg_accel_version, running_ac_version))
    else:
        # Since sync_gateway does not return the full commit, verify the prefix
        if running_ac_version != expected_sg_accel_version[:7]:
            raise ProvisioningError("Unexpected sync_gateway version!! Expected: {} Actual: {}".format(expected_sg_accel_version, running_ac_version))


def load_sync_gateway_config(sg_conf, server_url, cluster_config):
    """ Loads a syncgateway configuration for modification"""
    match_obj = re.match("(\w+?):\/\/(.*?):(\d+?)$", server_url)
    if match_obj:
        server_scheme = match_obj.group(1)
        server_ip = match_obj.group(2)
        server_port = match_obj.group(3)
    else:
        raise Exception("Regex pattern is not matching with server url format.")
    server_ip = server_ip.replace("//", "")

    with open(sg_conf) as default_conf:
        template = Template(default_conf.read())
        config_path = os.path.abspath(sg_conf)
        bucket_names = get_buckets_from_sync_gateway_config(config_path)
        sg_cert_path = os.path.abspath(SYNC_GATEWAY_CERT)
        cbs_cert_path = os.path.join(os.getcwd(), "certs")
        if is_xattrs_enabled(cluster_config):
            if get_sg_version(cluster_config) >= "2.1.0":
                autoimport_prop = '"import_docs": true,'
            else:
                autoimport_prop = '"import_docs": "continuous",'
            xattrs_prop = '"enable_shared_bucket_access": true,'
        else:
            autoimport_prop = ""
            xattrs_prop = ""
        if is_cbs_ssl_enabled(cluster_config):
            server_port = ""
            server_scheme = "couchbases"

        if is_x509_auth(cluster_config):
            server_port = ""
            server_scheme = "couchbases"

        sg_use_views_prop = ""
        num_index_replicas_prop = ""
        logging_prop = ""
        certpath_prop = ""
        x509_auth_prop = ""
        keypath_prop = ""
        cacertpath_prop = ""
        no_conflicts_prop = ""
        revs_limit_prop = ""
        sslcert_prop = ""
        sslkey_prop = ""
        delta_sync_prop = ""
        hide_prod_version_prop = ""
        disable_persistent_config_prop = ""
        server_tls_skip_verify_prop = ""
        disable_tls_server_prop = ""
        disable_admin_auth_prop = ""

        sg_platform = get_sg_platform(cluster_config)
        if get_sg_version(cluster_config) >= "2.1.0":
            logging_config = '"logging": {"debug": {"enabled": true}'
            try:
                redact_level = get_redact_level(cluster_config)
                logging_prop = '{}, "redaction_level": "{}" {},'.format(logging_config, redact_level, "}")
            except KeyError as ex:
                log_info("Keyerror in getting logging{}".format(str(ex)))
                logging_prop = '{} {},'.format(logging_config, "}")

            num_replicas = get_sg_replicas(cluster_config)
            num_index_replicas_prop = '"num_index_replicas": {},'.format(num_replicas)
            if get_sg_use_views(cluster_config):
                sg_use_views_prop = '"use_views": true,'

            if "macos" in sg_platform:
                sg_home_directory = "/Users/sync_gateway"
            elif sg_platform == "windows":
                sg_home_directory = "C:\\\\PROGRA~1\\\\Couchbase\\\\Sync Gateway"
            else:
                sg_home_directory = "/home/sync_gateway"

            if is_x509_auth(cluster_config):
                certpath_prop = '"certpath": "{}/certs/chain.pem",'.format(sg_home_directory)
                keypath_prop = '"keypath": "{}/certs/pkey.key",'.format(sg_home_directory)
                cacertpath_prop = '"cacertpath": "{}/certs/ca.pem",'.format(sg_home_directory)
                if sg_platform == "windows":
                    certpath_prop = certpath_prop.replace("/", "\\\\")
                    keypath_prop = keypath_prop.replace("/", "\\\\")
                    cacertpath_prop = cacertpath_prop.replace("/", "\\\\")
                server_scheme = "couchbases"
                server_port = ""
                x509_auth_prop = True
                generate_x509_certs(cluster_config, bucket_names, sg_platform)
            else:
                logging_prop = '"log": ["*"],'
            username = '"username": "{}",'.format(bucket_names[0])
            password = '"password": "password",'

        couchbase_server_primary_node = add_cbs_to_sg_config_server_field(cluster_config)
        couchbase_server_primary_node = get_cbs_primary_nodes_str(cluster_config, couchbase_server_primary_node)

        if sg_ssl_enabled(cluster_config):
            sslcert_prop = '"SSLCert": "sg_cert.pem",'
            sslkey_prop = '"SSLKey": "sg_privkey.pem",'

        if no_conflicts_enabled(cluster_config):
            no_conflicts_prop = '"allow_conflicts": false,'
        try:
            revs_limit = get_revs_limit(cluster_config)
            revs_limit_prop = '"revs_limit": {},'.format(revs_limit)
        except KeyError:
            log_info("revs_limit not found in {}, Ignoring".format(cluster_config))

        if is_delta_sync_enabled(cluster_config) and get_sg_version(cluster_config) >= "2.5.0":
            delta_sync_prop = '"delta_sync": { "enabled": true},'

        if is_hide_prod_version_enabled(cluster_config) and get_sg_version(cluster_config) >= "2.8.1":
            hide_prod_version_prop = '"hide_product_version": true,'

        if is_centralized_persistent_config_disabled(cluster_config) and get_sg_version(cluster_config) >= "3.0.0":
            disable_persistent_config_prop = '"disable_persistent_config": true,'

        if is_server_tls_skip_verify_enabled(cluster_config) and get_sg_version(cluster_config) >= "3.0.0":
            server_tls_skip_verify_prop = '"server_tls_skip_verify": true,'

        if is_tls_server_disabled(cluster_config) and get_sg_version(cluster_config) >= "3.0.0":
            disable_tls_server_prop = '"use_tls_server": false,'

        if is_admin_auth_disabled(cluster_config) and get_sg_version(cluster_config) >= "3.0.0":
            disable_admin_auth_prop = '"admin_interface_authentication": false,\n"metrics_interface_authentication": false,'

        temp = template.render(
            couchbase_server_primary_node=couchbase_server_primary_node,
            is_index_writer="false",
            server_scheme=server_scheme,
            server_port=server_port,
            autoimport=autoimport_prop,
            xattrs=xattrs_prop,
            sg_use_views=sg_use_views_prop,
            num_index_replicas=num_index_replicas_prop,
            logging=logging_prop,
            certpath=certpath_prop,
            keypath=keypath_prop,
            cacertpath=cacertpath_prop,
            x509_auth=x509_auth_prop,
            username=username,
            password=password,
            x509_certs_dir=cbs_cert_path,
            sg_cert_path=sg_cert_path,
            sslcert=sslcert_prop,
            sslkey=sslkey_prop,
            no_conflicts=no_conflicts_prop,
            revs_limit=revs_limit_prop,
            delta_sync=delta_sync_prop,
            hide_prod_version=hide_prod_version_prop,
            disable_persistent_config=disable_persistent_config_prop,
            server_tls_skip_verify=server_tls_skip_verify_prop,
            disable_tls_server=disable_tls_server_prop,
            disable_admin_auth=disable_admin_auth_prop
        )
        data = json.loads(temp)

    log_info("Loaded sync_gateway config: {}".format(data))
    return data


class SyncGateway(object):

    def __init__(self):
        self._session = Session()
        self.server_port = ""
        self.server_scheme = "couchbase"

    def install_sync_gateway(self, cluster_config, sync_gateway_version, sync_gateway_config, skip_bucketcreation=False):

        # Dirty hack -- these have to be put here in order to avoid circular imports
        from libraries.provision.install_sync_gateway import install_sync_gateway
        from libraries.provision.install_sync_gateway import SyncGatewayConfig

        if version_is_binary(sync_gateway_version):
            version, build = version_and_build(sync_gateway_version)
            log_info("VERSION: {} BUILD: {}".format(version, build))
            sg_config = SyncGatewayConfig(None, version, build, sync_gateway_config, "", skip_bucketcreation=skip_bucketcreation)
        else:
            sg_config = SyncGatewayConfig(sync_gateway_version, None, None, sync_gateway_config, "", skip_bucketcreation=skip_bucketcreation)

        install_sync_gateway(cluster_config=cluster_config, sync_gateway_config=sg_config)

        log_info("Verfying versions for cluster: {}".format(cluster_config))

        with open("{}.json".format(cluster_config)) as f:
            cluster_obj = json.loads(f.read())

        # Verify sync_gateway versions
        for sg in cluster_obj["sync_gateways"]:
            verify_sync_gateway_version(sg["ip"], sync_gateway_version)

        # Verify sg_accel versions, use the same expected version for sync_gateway for now
        for ac in cluster_obj["sg_accels"]:
            verify_sg_accel_version(ac["ip"], sync_gateway_version)

    def start_sync_gateways(self, cluster_config, url=None, config=None):
        """Start sync gateways in a cluster. If url is passed,
        start the sync gateway at that url
        """

        if config is None:
            raise ProvisioningError("Starting a Sync Gateway requires a config")

        ansible_runner = AnsibleRunner(cluster_config)
        config_path = os.path.abspath(config)
        sg_cert_path = os.path.abspath(SYNC_GATEWAY_CERT)
        cbs_cert_path = os.path.join(os.getcwd(), "certs")
        bucket_names = get_buckets_from_sync_gateway_config(config_path)
        couchbase_server_primary_node = add_cbs_to_sg_config_server_field(cluster_config)
        if is_cbs_ssl_enabled(cluster_config):
            self.server_port = ""
            self.server_scheme = "couchbases"

        if is_x509_auth(cluster_config):
            self.server_port = ""
            self.server_scheme = "couchbases"

        couchbase_server_primary_node = get_cbs_primary_nodes_str(cluster_config, couchbase_server_primary_node)
        playbook_vars = {
            "sync_gateway_config_filepath": config_path,
            "username": "",
            "password": "",
            "certpath": "",
            "keypath": "",
            "cacertpath": "",
            "x509_certs_dir": cbs_cert_path,
            "x509_auth": False,
            "sg_cert_path": sg_cert_path,
            "server_port": self.server_port,
            "server_scheme": self.server_scheme,
            "autoimport": "",
            "xattrs": "",
            "no_conflicts": "",
            "revs_limit": "",
            "sg_use_views": "",
            "num_index_replicas": "",
            "couchbase_server_primary_node": couchbase_server_primary_node,
            "delta_sync": "",
            "prometheus": "",
            "hide_product_version": "",
            "disable_persistent_config": "",
            "server_tls_skip_verify": "",
            "disable_tls_server": "",
            "disable_admin_auth": ""
        }
        sg_platform = get_sg_platform(cluster_config)
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

        if sg_ssl_enabled(cluster_config):
            playbook_vars["sslcert"] = '"SSLCert": "sg_cert.pem",'
            playbook_vars["sslkey"] = '"SSLKey": "sg_privkey.pem",'

        if no_conflicts_enabled(cluster_config):
            playbook_vars["no_conflicts"] = '"allow_conflicts": false,'
        try:
            revs_limit = get_revs_limit(cluster_config)
            playbook_vars["revs_limit"] = '"revs_limit": {},'.format(revs_limit)
        except KeyError:
            log_info("revs_limit not found in {}, Ignoring".format(cluster_config))

        if is_cbs_ssl_enabled(cluster_config) and get_sg_version(cluster_config) >= "1.5.0":
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

        if url is not None:
            target = hostname_for_url(cluster_config, url)
            log_info("Starting {} sync_gateway.".format(target))
            status = ansible_runner.run_ansible_playbook(
                "start-sync-gateway.yml",
                extra_vars=playbook_vars,
                subset=target
            )
        else:
            log_info("Starting all sync_gateways.")
            status = ansible_runner.run_ansible_playbook(
                "start-sync-gateway.yml",
                extra_vars=playbook_vars
            )
        if status != 0:
            raise ProvisioningError("Could not start sync_gateway")

    def stop_sync_gateways(self, cluster_config, url=None):
        """ Stop sync gateways in a cluster. If url is passed, shut down
        shut down the sync gateway at that url
        """
        ansible_runner = AnsibleRunner(cluster_config)

        if url is not None:
            target = hostname_for_url(cluster_config, url)
            log_info("Shutting down sync_gateway on {} ...".format(target))
            status = ansible_runner.run_ansible_playbook(
                "stop-sync-gateway.yml",
                subset=target
            )
        else:
            log_info("Shutting down all sync_gateways")
            status = ansible_runner.run_ansible_playbook(
                "stop-sync-gateway.yml",
            )
        if status != 0:
            raise ProvisioningError("Could not stop sync_gateway")

    def restart_sync_gateways(self, cluster_config, url=None):
        """ Restart sync gateways in a cluster. If url is passed, restart
         the sync gateway at that url
        """
        ansible_runner = AnsibleRunner(cluster_config)

        if url is not None:
            target = hostname_for_url(cluster_config, url)
            log_info("Restarting sync_gateway on {} ...".format(target))
            status = ansible_runner.run_ansible_playbook(
                "restart-sync-gateway.yml",
                subset=target
            )
        else:
            log_info("Restarting all sync_gateways")
            status = ansible_runner.run_ansible_playbook(
                "restart-sync-gateway.yml",
            )
        if status != 0:
            raise ProvisioningError("Could not restart sync_gateway")

    def upgrade_sync_gateway(self, sync_gateways, sync_gateway_version, sync_gateway_upgraded_version, sg_conf, cluster_config):
        log_info('------------------------------------------')
        log_info('START Sync Gateway cluster upgrade')
        log_info('------------------------------------------')

        for sg in sync_gateways:
            sg_ip = host_for_url(sg["admin"])
            log_info("Checking for sync gateway product info before upgrade")
            verify_sync_gateway_product_info(sg_ip)
            log_info("Checking for sync gateway version: {}".format(sync_gateway_version))
            verify_sync_gateway_version(sg_ip, sync_gateway_version)
            log_info("Upgrading sync gateway: {}".format(sg_ip))
            self.upgrade_sync_gateways(
                cluster_config=cluster_config,
                sg_conf=sg_conf,
                sync_gateway_version=sync_gateway_upgraded_version,
                url=sg_ip
            )

            time.sleep(10)  # After upgrading each sync gateway, it need few seconds to get product info
            log_info("Checking for sync gateway product info after upgrade")
            verify_sync_gateway_product_info(sg_ip)
            log_info("Checking for sync gateway version after upgrade: {}".format(sync_gateway_upgraded_version))
            verify_sync_gateway_version(sg_ip, sync_gateway_upgraded_version)

        log_info("Upgraded all the sync gateway nodes in the cluster")
        log_info('------------------------------------------')
        log_info('END Sync Gateway cluster upgrade')
        log_info('------------------------------------------')

    def upgrade_sync_gateways(self, cluster_config, sg_conf, sync_gateway_version, url=None):
        """ Upgrade sync gateways in a cluster. If url is passed, upgrade
            the sync gateway at that url
        """
        ansible_runner = AnsibleRunner(cluster_config)

        from libraries.provision.install_sync_gateway import SyncGatewayConfig
        version, build = version_and_build(sync_gateway_version)
        sg_config = SyncGatewayConfig(
            commit=None,
            version_number=version,
            build_number=build,
            config_path=sg_conf,
            build_flags="",
            skip_bucketcreation=False
        )
        sg_conf = os.path.abspath(sg_config.config_path)
        sg_cert_path = os.path.abspath(SYNC_GATEWAY_CERT)
        cbs_cert_path = os.path.join(os.getcwd(), "certs")
        couchbase_server_primary_node = add_cbs_to_sg_config_server_field(cluster_config)
        bucket_names = get_buckets_from_sync_gateway_config(sg_conf)

        if is_x509_auth(cluster_config) or is_cbs_ssl_enabled(cluster_config):
            self.server_port = ""
            self.server_scheme = "couchbases"

        couchbase_server_primary_node = get_cbs_primary_nodes_str(cluster_config, couchbase_server_primary_node)
        # Shared vars
        playbook_vars = {
            "sync_gateway_config_filepath": sg_conf,
            "username": "",
            "password": "",
            "certpath": "",
            "keypath": "",
            "cacertpath": "",
            "x509_auth": False,
            "sg_cert_path": sg_cert_path,
            "x509_certs_dir": cbs_cert_path,
            "server_port": self.server_port,
            "server_scheme": self.server_scheme,
            "autoimport": "",
            "xattrs": "",
            "no_conflicts": "",
            "revs_limit": "",
            "sg_use_views": "",
            "num_index_replicas": "",
            "couchbase_server_primary_node": couchbase_server_primary_node,
            "delta_sync": "",
            "prometheus": "",
            "hide_product_version": "",
            "disable_persistent_config": "",
            "server_tls_skip_verify": "",
            "disable_tls_server": "",
            "disable_admin_auth": ""
        }
        sync_gateway_base_url, sync_gateway_package_name, sg_accel_package_name = sg_config.sync_gateway_base_url_and_package()

        playbook_vars["couchbase_sync_gateway_package_base_url"] = sync_gateway_base_url
        playbook_vars["couchbase_sync_gateway_package"] = sync_gateway_package_name
        playbook_vars["couchbase_sg_accel_package"] = sg_accel_package_name
        playbook_vars["username"] = '"username": "{}",'.format(bucket_names[0])
        playbook_vars["password"] = '"password": "password",'

        server_version = get_cbs_version(cluster_config)
        cbs_version, cbs_build = version_and_build(server_version)

        if version >= "2.1.0":
            logging_config = '"logging": {"debug": {"enabled": true}'
            try:
                redact_level = get_redact_level(cluster_config)
                playbook_vars["logging"] = '{}, "redaction_level": "{}" {},'.format(logging_config, redact_level, "}")
            except KeyError as ex:
                log_info("Keyerror in getting logging{}".format(str(ex)))

                playbook_vars["logging"] = '{} {},'.format(logging_config, "}")

            if not get_sg_use_views(cluster_config) and cbs_version >= "5.5.0":
                num_replicas = get_sg_replicas(cluster_config)
                playbook_vars["num_index_replicas"] = '"num_index_replicas": {},'.format(num_replicas)
            else:
                playbook_vars["sg_use_views"] = '"use_views": true,'

            sg_platform = get_sg_platform(cluster_config)
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
        if is_xattrs_enabled(cluster_config) and cbs_version >= "5.0.0":
            if version >= "2.1.0":
                playbook_vars["autoimport"] = '"import_docs": true,'
            else:
                playbook_vars["autoimport"] = '"import_docs": "continuous",'
            playbook_vars["xattrs"] = '"enable_shared_bucket_access": true,'

        if sg_ssl_enabled(cluster_config):
            playbook_vars["sslcert"] = '"SSLCert": "sg_cert.pem",'
            playbook_vars["sslkey"] = '"SSLKey": "sg_privkey.pem",'

        if no_conflicts_enabled(cluster_config):
            playbook_vars["no_conflicts"] = '"allow_conflicts": false,'
        try:
            revs_limit = get_revs_limit(cluster_config)
            playbook_vars["revs_limit"] = '"revs_limit": {},'.format(revs_limit)
        except KeyError:
            log_info("revs_limit not found in {}, Ignoring".format(cluster_config))

        if is_delta_sync_enabled(cluster_config) and version >= "2.5.0":
            playbook_vars["delta_sync"] = '"delta_sync": { "enabled": true},'
        if version >= "2.8.0":
            playbook_vars["prometheus"] = '"metricsInterface": ":4986",'

        if is_hide_prod_version_enabled(cluster_config) and version >= "2.8.1":
            playbook_vars["hide_product_version"] = '"hide_product_version": true,'

        if is_centralized_persistent_config_disabled(cluster_config) and version >= "3.0.0":
            playbook_vars["disable_persistent_config"] = '"disable_persistent_config": true,'

        if is_server_tls_skip_verify_enabled(cluster_config) and version >= "3.0.0":
            playbook_vars["server_tls_skip_verify"] = '"server_tls_skip_verify": true,'

        if is_tls_server_disabled(cluster_config) and version >= "3.0.0":
            playbook_vars["disable_tls_server"] = '"use_tls_server": false,'

        if is_admin_auth_disabled(cluster_config) and version >= "3.0.0":
            playbook_vars["disable_admin_auth"] = '"admin_interface_authentication": false,    \n"metrics_interface_authentication": false,'
        if url is not None:
            target = hostname_for_url(cluster_config, url)
            log_info("Upgrading sync_gateway/sg_accel on {} ...".format(target))
            status = ansible_runner.run_ansible_playbook(
                "upgrade-sg-sgaccel-package.yml",
                subset=target,
                extra_vars=playbook_vars
            )
            log_info("Completed upgrading {}".format(url))
        else:
            log_info("Upgrading all sync_gateways/sg_accels")
            status = ansible_runner.run_ansible_playbook(
                "upgrade-sg-sgaccel-package.yml",
                extra_vars=playbook_vars
            )
            log_info("Completed upgrading all sync_gateways/sg_accels")
        log_info("upgrade status is {}".format(status))

        if status != 0:
            raise Exception("Could not upgrade sync_gateway/sg_accel")

    def redeploy_sync_gateway_config(self, cluster_config, sg_conf, url, sync_gateway_version, enable_import=False):
        """Deploy an SG config with xattrs enabled
            Will also enable import if enable_import is set to True
            It is used to enable xattrs and import in the SG config"""
        ansible_runner = AnsibleRunner(cluster_config)
        server_port = ""
        server_scheme = "couchbase"
        sg_cert_path = os.path.abspath(SYNC_GATEWAY_CERT)
        cbs_cert_path = os.path.join(os.getcwd(), "certs")
        bucket_names = get_buckets_from_sync_gateway_config(sg_conf)
        version, build = version_and_build(sync_gateway_version)

        if is_cbs_ssl_enabled(cluster_config):
            server_port = ""
            server_scheme = "couchbases"

        # Shared vars
        playbook_vars = {
            "username": "",
            "password": "",
            "certpath": "",
            "keypath": "",
            "cacertpath": "",
            "x509_auth": False,
            "x509_certs_dir": cbs_cert_path,
            "sg_cert_path": sg_cert_path,
            "sync_gateway_config_filepath": sg_conf,
            "server_port": server_port,
            "server_scheme": server_scheme,
            "autoimport": "",
            "sslkey": "",
            "sslcert": "",
            "num_index_replicas": "",
            "sg_use_views": "",
            "revs_limit": "",
            "xattrs": "",
            "no_conflicts": "",
            "delta_sync": "",
            "prometheus": "",
            "hide_product_version": "",
            "disable_persistent_config": "",
            "server_tls_skip_verify": "",
            "disable_tls_server": "",
            "disable_admin_auth": ""
        }

        playbook_vars["username"] = '"username": "{}",'.format(bucket_names[0])
        playbook_vars["password"] = '"password": "password",'

        if version >= "2.1.0":
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

            sg_platform = get_sg_platform(cluster_config)
            if "macos" in sg_platform:
                sg_home_directory = "/Users/sync_gateway"
            elif sg_platform == "windows":
                sg_home_directory = "C:\\\\PROGRA~1\\\\Couchbase\\\\Sync Gateway"
            else:
                sg_home_directory = "/home/sync_gateway"

            if is_x509_auth(cluster_config):
                playbook_vars[
                    "certpath"] = '"certpath": "{}/certs "{}/certs/chain.pem",'.format(sg_home_directory)
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
            playbook_vars["logging"] = '"log": ["*"],'

        if is_xattrs_enabled(cluster_config):
            playbook_vars["xattrs"] = '"enable_shared_bucket_access": true,'

        if is_xattrs_enabled(cluster_config) and enable_import:
            if version >= "2.1.0":
                playbook_vars["autoimport"] = '"import_docs": true,'
            else:
                playbook_vars["autoimport"] = '"import_docs": "continuous",'

        if no_conflicts_enabled(cluster_config):
            playbook_vars["no_conflicts"] = '"allow_conflicts": false,'

        if sg_ssl_enabled(cluster_config):
            playbook_vars["sslcert"] = '"SSLCert": "sg_cert.pem",'
            playbook_vars["sslkey"] = '"SSLKey": "sg_privkey.pem",'

        try:
            revs_limit = get_revs_limit(cluster_config)
            playbook_vars["revs_limit"] = '"revs_limit": {},'.format(revs_limit)
        except KeyError:
            log_info("revs_limit not found in {}, Ignoring".format(cluster_config))

        if is_delta_sync_enabled(cluster_config) and version >= "2.5.0":
            playbook_vars["delta_sync"] = '"delta_sync": { "enabled": true},'

        if version >= "2.8.0":
            playbook_vars["prometheus"] = '"metricsInterface": ":4986",'

        if is_hide_prod_version_enabled(cluster_config) and version >= "2.8.1":
            playbook_vars["hide_product_version"] = '"hide_product_version": true,'

        if is_centralized_persistent_config_disabled(cluster_config) and version >= "3.0.0":
            playbook_vars["disable_persistent_config"] = '"disable_persistent_config": true,'

        if is_server_tls_skip_verify_enabled(cluster_config) and version >= "3.0.0":
            playbook_vars["server_tls_skip_verify"] = '"server_tls_skip_verify": true,'

        if is_tls_server_disabled(cluster_config) and version >= "3.0.0":
            playbook_vars["disable_tls_server"] = '"use_tls_server": false,'

        if is_admin_auth_disabled(cluster_config) and version >= "3.0.0":
            playbook_vars["disable_admin_auth"] = '"admin_interface_authentication": false,    \n"metrics_interface_authentication": false,'

        # Deploy config
        if url is not None:
            target = hostname_for_url(cluster_config, url)
            log_info("Deploying sync_gateway config on {} ...".format(target))
            status = ansible_runner.run_ansible_playbook(
                "deploy-sync-gateway-config.yml",
                subset=target,
                extra_vars=playbook_vars
            )
        else:
            log_info("Deploying config on all sync_gateways")
            status = ansible_runner.run_ansible_playbook(
                "deploy-sync-gateway-config.yml",
                extra_vars=playbook_vars
            )
        if status != 0:
            raise Exception("Could not deploy config to sync_gateway")

    def create_directory(self, cluster_config, url, dir_name):
        if dir_name is None:
            raise Error("Please provide a directory to delete")

        if url is not None:
            target = hostname_for_url(cluster_config, url)
            ansible_runner = AnsibleRunner(cluster_config)
            log_info("Deleting and creating {} on Sync Gateway {} ...".format(dir_name, url))
            playbook_vars = {
                "directory": dir_name
            }

            status = ansible_runner.run_ansible_playbook(
                "create-directory.yml",
                extra_vars=playbook_vars,
                subset=target
            )
        else:
            log_info("Deleting and creating {} on all Sync Gateways ...".format(dir_name))
            status = ansible_runner.run_ansible_playbook(
                "create-directory.yml",
                extra_vars=playbook_vars
            )

        if status != 0:
            raise ProvisioningError("Could not create the directory on sync_gateway")

    def create_empty_file(self, cluster_config, url, file_name, file_size):
        if file_name is None or file_size is None:
            raise Error("Please provide a file name and the file size to create")

        if url is not None:
            target = hostname_for_url(cluster_config, url)
            ansible_runner = AnsibleRunner(cluster_config)
            log_info("Deleting and creating {} on Sync Gateway {} ...".format(file_name, url))

            playbook_vars = {
                "file_name": file_name,
                "file_size": file_size,
                "owner": "sync_gateway",
                "group": "sync_gateway"
            }

            status = ansible_runner.run_ansible_playbook(
                "create-empty-file.yml",
                subset=target,
                extra_vars=playbook_vars
            )
        else:
            log_info("Deleting and creating {} on all Sync Gateways ...".format(file_name))
            status = ansible_runner.run_ansible_playbook(
                "create-empty-file.yml",
                extra_vars=playbook_vars
            )

        if status != 0:
            raise ProvisioningError("Could not create an empty file on sync_gateway")


def create_sync_gateways(cluster_config, sg_config_path):

    """
    @summary:
    Get the ips from cluster config and generate two sync gateways and return the objects
    """
    cluster = Cluster(config=cluster_config)
    cluster.reset(sg_config_path=sg_config_path)
    sg1 = cluster.sync_gateways[0]
    sg2 = cluster.sync_gateways[1]

    return sg1, sg2


def create_docs_via_sdk(cbs_url, cbs_cluster, bucket_name, num_docs, doc_name='doc_set_two'):
    cbs_host = host_for_url(cbs_url)
    log_info("Adding docs via SDK...")
    if cbs_cluster.ipv6:
        connection_url = "couchbase://{}?ipv6=allow".format(re.sub(r'[\[\]]', '', cbs_host))
    else:
        connection_url = 'couchbase://{}'.format(cbs_host)
    sdk_client = get_cluster(connection_url, bucket_name)

    sdk_doc_bodies = document.create_docs(doc_name, num_docs)
    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    sdk_client.upsert_multi(sdk_docs)

    log_info("Adding docs done on CBS")
    return sdk_docs, sdk_client


def setup_replications_on_sgconfig(remote_sg_url, sg_db, remote_user, remote_password, direction="pushAndPull", channels=None, continuous=False, replication_id=None):

    # replication = {}
    repl1 = {}
    if replication_id is None:
        replication_id = "sgw_repl_{}".format(random_string(length=10, digit=True))
    remote_sg_url = remote_sg_url.replace("://", "://{}:{}@".format(remote_user, remote_password))
    remote_sg_url = "{}/{}".format(remote_sg_url, sg_db)
    # remote_sg_url = "{}/{}".format(remote_sg_url)
    repl1["remote"] = "{}".format(remote_sg_url)
    repl1["direction"] = direction
    repl1["continuous"] = continuous
    if channels is not None:
        repl1["filter"] = "sync_gateway/bychannel"
        repl1["query_params"] = channels
    # replication[replication_id] = repl1
    repl1_string = json.dumps(repl1)
    repl1_string = repl1_string.replace("\"True\"", "true")
    replication_string = "\"{}\": {}".format(replication_id, repl1_string)
    return replication_string, replication_id


def setup_sgreplicate1_on_sgconfig(source_sg_url, sg_db1, remote_sg_url, sg_db2, channels=None, continuous=False):

    # replication = {}
    repl = {}
    replication_id = "sgw_repl_{}".format(random_string(length=10, digit=True))
    # source_sg_url = source_sg_url.replace("://", "://{}:{}@".format(remote_user, remote_password))
    source_sg_url = "{}/{}".format(source_sg_url, sg_db1)
    # remote_sg_url = remote_sg_url.replace("://", "://{}:{}@".format(remote_user, remote_password))
    remote_sg_url = "{}/{}".format(remote_sg_url, sg_db2)
    # remote_sg_url = "{}/{}".format(remote_sg_url)
    repl["replication_id"] = "{}".format(replication_id)
    repl["source"] = "{}".format(source_sg_url)
    repl["target"] = "{}".format(remote_sg_url)
    repl["continuous"] = continuous
    if channels is not None:
        repl["filter"] = "sync_gateway/bychannel"
        repl["query_params"] = channels
    # replication[replication_id] = repl1
    repl_string = json.dumps(repl)
    repl_string = repl_string.replace("\"True\"", "true")
    return repl_string, replication_id


def update_replication_in_sgw_config(sg_conf_name, sg_mode, repl_remote, repl_remote_db, repl_remote_user, repl_remote_password, repl_repl_id, repl_direction="push_and_pull", repl_conflict_resolution_type="default", repl_continuous=None, repl_filter_query_params=None, custom_conflict_js_function=None):
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)
    temp_sg_config, _ = copy_sgconf_to_temp(sg_config, sg_mode)
    if "4984" in repl_remote:
        if repl_remote_user and repl_remote_password:
            remote_url = repl_remote.replace("://", "://{}:{}@".format(repl_remote_user, repl_remote_password))
            remote_url = "{}/{}".format(remote_url, repl_remote_db)
        else:
            raise Exception("No remote node's username and password provided ")
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ repl_remote }}", "{}".format(remote_url))
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ repl_direction }}", "\"{}\"".format(repl_direction))
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ repl_conflict_resolution_type }}", "\"{}\"".format(repl_conflict_resolution_type))
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ repl_repl_id }}", "\"{}\"".format(repl_repl_id))
    if repl_continuous is not None:
        cont = "true"
        temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ repl_continuous }}", "\"continuous\": {},".format(cont))
    else:
        temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ repl_continuous }}", "")
    if repl_filter_query_params is not None:
        temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ repl_filter_query_params }}", "\"{}\",".format(repl_filter_query_params))
    else:
        temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ repl_filter_query_params }}", "")
    if repl_conflict_resolution_type == "custom":
        custom_conflict_key = "custom_conflict_resolver"
        custom_conflict_key_value = "\"{}\":`{}`".format(custom_conflict_key, custom_conflict_js_function)
        temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ custom_conflict_js_function }}", "{}".format(custom_conflict_key_value))
    return temp_sg_config


def wait_until_docs_imported_from_server(sg_admin_url, sg_client, sg_db, expected_docs, prev_import_count, timeout=5):
    sg_expvars = sg_client.get_expvars(sg_admin_url)
    sg_import_count = sg_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"]
    count = 0
    while True:
        sg_expvars = sg_client.get_expvars(sg_admin_url)
        sg_import_count = sg_expvars["syncgateway"]["per_db"][sg_db]["shared_bucket_import"]["import_count"]
        import_count = sg_import_count - prev_import_count
        if count > timeout or import_count >= expected_docs:
            break
        time.sleep(1)
        count += 1


def replace_xattrs_sync_func_in_config(sg_config, channel, enable_xattrs_key=True):
    # Sample config how it looks after it constructs the config here
    """function (doc, oldDoc, meta){
    if(meta.xattrs.channel1 != undefined){
        channel(meta.xattrs.channel1);
        console.log("channel1 is defined");
        console.log(meta.xattrs.channel1);
        console.log(doc._id);
    }
    }"""
    mode = "cc"
    sync_func_string = """ `function (doc, oldDoc, meta){
    if(meta.xattrs.""" + channel + """ != undefined){
        channel(meta.xattrs.""" + channel + """);
    }
    }` """
    temp_sg_config, _ = copy_sgconf_to_temp(sg_config, mode)
    if enable_xattrs_key:
        user_xattrs_string = """ "user_xattr_key": "{}", """.format(channel)
    else:
        user_xattrs_string = ""
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ user_xattrs_key }}", user_xattrs_string)
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ sync_func }}", sync_func_string)
    return temp_sg_config


def replace_flag_with_config(sg_config, flag, property):
    mode = "cc"
    temp_sg_config, _ = copy_sgconf_to_temp(sg_config, mode)
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, flag, property)
    return temp_sg_config
