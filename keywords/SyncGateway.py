import re
import os
import json

import requests
from requests import Session
from jinja2 import Template

from keywords.constants import SYNC_GATEWAY_CONFIGS, SYNC_GATEWAY_CERT
from keywords.utils import version_is_binary, add_cbs_to_sg_config_server_field
from keywords.utils import log_r
from keywords.utils import version_and_build
from keywords.utils import hostname_for_url
from keywords.utils import log_info
from utilities.cluster_config_utils import get_revs_limit, is_ipv6, is_x509_auth, generate_x509_certs
from keywords.exceptions import ProvisioningError, Error
from libraries.provision.ansible_runner import AnsibleRunner
from utilities.cluster_config_utils import is_cbs_ssl_enabled, is_xattrs_enabled, no_conflicts_enabled, get_redact_level, get_sg_platform
from utilities.cluster_config_utils import get_sg_replicas, get_sg_use_views, get_sg_version, sg_ssl_enabled, get_cbs_version, is_delta_sync_enabled
from libraries.testkit.syncgateway import get_buckets_from_sync_gateway_config


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

    resp = requests.get("{}://{}:4984".format(sg_scheme, host), verify=False)
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
        "2.5.0": "271"
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
    server_scheme, server_ip, server_port = server_url.split(":")
    server_ip = server_ip.replace("//", "")

    with open(sg_conf) as default_conf:
        template = Template(default_conf.read())
        config_path = os.path.abspath(sg_conf)
        bucket_names = get_buckets_from_sync_gateway_config(config_path)
        sg_cert_path = os.path.abspath(SYNC_GATEWAY_CERT)
        cbs_cert_path = os.path.join(os.getcwd(), "certs")
        if is_xattrs_enabled(cluster_config):
            autoimport_prop = '"import_docs": "continuous",'
            xattrs_prop = '"enable_shared_bucket_access": true,'
        else:
            autoimport_prop = ""
            xattrs_prop = ""
        if is_cbs_ssl_enabled(cluster_config):
            server_port = 18091
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

        sg_platform = get_sg_platform(cluster_config)
        if get_sg_version(cluster_config) >= "2.1.0":
            logging_config = '"logging": {"debug": {"enabled": true}'
            try:
                redact_level = get_redact_level(cluster_config)
                logging_prop = '{}, "redaction_level": "{}" {},'.format(logging_config, redact_level, "}")
            except KeyError as ex:
                log_info("Keyerror in getting logging{}".format(ex.message))
                logging_prop = '{} {},'.format(logging_config, "}")

            num_replicas = get_sg_replicas(cluster_config)
            num_index_replicas_prop = '"num_index_replicas": {},'.format(num_replicas)
            if get_sg_use_views(cluster_config):
                sg_use_views_prop = '"use_views": true,'

            if sg_platform == "macos":
                sg_home_directory = "/Users/sync_gateway"
            else:
                sg_home_directory = "/home/sync_gateway"

            if is_x509_auth(cluster_config):
                certpath_prop = '"certpath": "{}/certs/chain.pem",'.format(sg_home_directory)
                keypath_prop = '"keypath": "{}/certs/pkey.key",'.format(sg_home_directory)
                cacertpath_prop = '"cacertpath": "{}/certs/ca.pem",'.format(sg_home_directory)
                server_scheme = "couchbases"
                server_port = ""
                x509_auth_prop = True
                generate_x509_certs(cluster_config, bucket_names)
            else:
                logging_prop = '"log": ["*"],'
            username = '"username": "{}",'.format(bucket_names[0])
            password = '"password": "password",'

        couchbase_server_primary_node = add_cbs_to_sg_config_server_field(cluster_config)
        if is_ipv6(cluster_config):
            couchbase_server_primary_node = "[{}]".format(couchbase_server_primary_node)

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
            delta_sync=delta_sync_prop
        )
        data = json.loads(temp)

    log_info("Loaded sync_gateway config: {}".format(data))
    return data


class SyncGateway(object):

    def __init__(self):
        self._session = Session()
        self.server_port = 8091
        self.server_scheme = "http"

    def install_sync_gateway(self, cluster_config, sync_gateway_version, sync_gateway_config):

        # Dirty hack -- these have to be put here in order to avoid circular imports
        from libraries.provision.install_sync_gateway import install_sync_gateway
        from libraries.provision.install_sync_gateway import SyncGatewayConfig

        if version_is_binary(sync_gateway_version):
            version, build = version_and_build(sync_gateway_version)
            log_info("VERSION: {} BUILD: {}".format(version, build))
            sg_config = SyncGatewayConfig(None, version, build, sync_gateway_config, "", False)
        else:
            sg_config = SyncGatewayConfig(sync_gateway_version, None, None, sync_gateway_config, "", False)

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
            self.server_port = 18091
            self.server_scheme = "couchbases"

        if is_x509_auth(cluster_config):
            self.server_port = ""
            self.server_scheme = "couchbases"

        if is_ipv6(cluster_config):
            couchbase_server_primary_node = "[{}]".format(couchbase_server_primary_node)
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
            "delta_sync": ""
        }
        sg_platform = get_sg_platform(cluster_config)
        if get_sg_version(cluster_config) >= "2.1.0":
            logging_config = '"logging": {"debug": {"enabled": true}'
            try:
                redact_level = get_redact_level(cluster_config)
                playbook_vars["logging"] = '{}, "redaction_level": "{}" {},'.format(logging_config, redact_level, "}")
            except KeyError as ex:
                log_info("Keyerror in getting logging{}".format(ex.message))
                playbook_vars["logging"] = '{} {},'.format(logging_config, "}")

            if get_sg_use_views(cluster_config):
                playbook_vars["sg_use_views"] = '"use_views": true,'
            else:
                num_replicas = get_sg_replicas(cluster_config)
                playbook_vars["num_index_replicas"] = '"num_index_replicas": {},'.format(num_replicas)

            if sg_platform == "macos":
                sg_home_directory = "/Users/sync_gateway"
            else:
                sg_home_directory = "/home/sync_gateway"

            if is_x509_auth(cluster_config):
                playbook_vars[
                    "certpath"] = '"certpath": "{}/certs/chain.pem",'.format(sg_home_directory)
                playbook_vars[
                    "keypath"] = '"keypath": "{}/certs/pkey.key",'.format(sg_home_directory)
                playbook_vars[
                    "cacertpath"] = '"cacertpath": "{}/certs/ca.pem",'.format(sg_home_directory)
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

        if is_xattrs_enabled(cluster_config):
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
        couchbase_server_primary_node = add_cbs_to_sg_config_server_field(cluster_config)
        bucket_names = get_buckets_from_sync_gateway_config(sg_conf)

        if is_cbs_ssl_enabled(cluster_config):
            self.server_port = 18091
            self.server_scheme = "https"

        if is_x509_auth(cluster_config):
            self.server_port = ""
            self.server_scheme = "couchbases"

        if is_ipv6(cluster_config):
            couchbase_server_primary_node = "[{}]".format(couchbase_server_primary_node)

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
            "server_port": self.server_port,
            "server_scheme": self.server_scheme,
            "autoimport": "",
            "xattrs": "",
            "no_conflicts": "",
            "revs_limit": "",
            "sg_use_views": "",
            "num_index_replicas": "",
            "couchbase_server_primary_node": couchbase_server_primary_node,
            "delta_sync": ""
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
                log_info("Keyerror in getting logging{}".format(ex.message))
                playbook_vars["logging"] = '{} {},'.format(logging_config, "}")

            if not get_sg_use_views(cluster_config) and cbs_version >= "5.5.0":
                num_replicas = get_sg_replicas(cluster_config)
                playbook_vars["num_index_replicas"] = '"num_index_replicas": {},'.format(num_replicas)
            else:
                playbook_vars["sg_use_views"] = '"use_views": true,'
        else:
            playbook_vars["logging"] = '"log": ["*"],'

        if is_xattrs_enabled(cluster_config) and cbs_version >= "5.0.0":
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
        server_port = 8091
        server_scheme = "http"
        sg_cert_path = os.path.abspath(SYNC_GATEWAY_CERT)
        bucket_names = get_buckets_from_sync_gateway_config(sg_conf)
        version, build = version_and_build(sync_gateway_version)

        if is_cbs_ssl_enabled(cluster_config):
            server_port = 18091
            server_scheme = "https"

        # Shared vars
        playbook_vars = {
            "username": "",
            "password": "",
            "certpath": "",
            "keypath": "",
            "cacertpath": "",
            "x509_auth": False,
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
            "delta_sync": ""
        }

        playbook_vars["username"] = '"username": "{}",'.format(bucket_names[0])
        playbook_vars["password"] = '"password": "password",'

        if version >= "2.1.0":
            logging_config = '"logging": {"debug": {"enabled": true}'
            try:
                redact_level = get_redact_level(cluster_config)
                playbook_vars["logging"] = '{}, "redaction_level": "{}" {},'.format(logging_config, redact_level, "}")
            except KeyError as ex:
                log_info("Keyerror in getting logging{}".format(ex.message))
                playbook_vars["logging"] = '{} {},'.format(logging_config, "}")

            if get_sg_use_views(cluster_config):
                playbook_vars["sg_use_views"] = '"use_views": true,'
            else:
                num_replicas = get_sg_replicas(cluster_config)
                playbook_vars["num_index_replicas"] = '"num_index_replicas": {},'.format(num_replicas)
        else:
            playbook_vars["logging"] = '"log": ["*"],'

        if is_xattrs_enabled(cluster_config):
            playbook_vars["xattrs"] = '"enable_shared_bucket_access": true,'

        if is_xattrs_enabled(cluster_config) and enable_import:
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
