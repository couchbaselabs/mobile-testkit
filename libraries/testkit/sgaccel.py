import logging
import os

import requests

import libraries.testkit.settings
from libraries.provision.ansible_runner import AnsibleRunner
from utilities.cluster_config_utils import is_cbs_ssl_enabled, is_xattrs_enabled, no_conflicts_enabled, get_revs_limit
from utilities.cluster_config_utils import get_sg_replicas, get_sg_use_views, get_sg_version, get_redact_level, is_delta_sync_enabled
from keywords.utils import add_cbs_to_sg_config_server_field, log_info
from keywords.constants import SYNC_GATEWAY_CERT
from utilities.cluster_config_utils import sg_ssl_enabled
from keywords.exceptions import ProvisioningError

log = logging.getLogger(libraries.testkit.settings.LOGGER)


class SgAccel:

    def __init__(self, cluster_config, target):
        self.ansible_runner = AnsibleRunner(cluster_config)
        self.ip = target["ip"]
        self.url = "http://{}:4985".format(target["ip"])
        self.hostname = target["name"]
        self.cluster_config = cluster_config
        self.server_port = 8091
        self.server_scheme = "http"
        self.sync_gateway_ssl = sg_ssl_enabled(self.cluster_config)

        if is_cbs_ssl_enabled(self.cluster_config):
            self.server_port = 18091
            self.server_scheme = "https"

    def info(self):
        r = requests.get(self.url)
        r.raise_for_status()
        return r.text

    def stop(self):
        status = self.ansible_runner.run_ansible_playbook(
            "stop-sg-accel.yml",
            subset=self.hostname
        )
        return status

    def start(self, config):
        conf_path = os.path.abspath(config)
        log.info(">>> Starting sg_accel with configuration: {}".format(conf_path))

        couchbase_server_primary_node = add_cbs_to_sg_config_server_field(self.cluster_config)
        sg_cert_path = os.path.abspath(SYNC_GATEWAY_CERT)

        playbook_vars = {
            "sync_gateway_config_filepath": conf_path,
            "server_port": self.server_port,
            "server_scheme": self.server_scheme,
            "sg_cert_path": sg_cert_path,
            "autoimport": "",
            "xattrs": "",
            "no_conflicts": "",
            "revs_limit": "",
            "num_index_replicas": "",
            "sg_use_views": "",
            "sslcert": "",
            "sslkey": "",
            "logging": "",
            "couchbase_server_primary_node": couchbase_server_primary_node,
            "delta_sync": ""
        }

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
        else:
            playbook_vars["logging"] = '"log": ["*"],'

        if is_xattrs_enabled(self.cluster_config):
            playbook_vars["autoimport"] = '"import_docs": true,'
            playbook_vars["xattrs"] = '"enable_shared_bucket_access": true,'

        if self.sync_gateway_ssl:
            playbook_vars["sslcert"] = '"SSLCert": "sg_cert.pem",'
            playbook_vars["sslkey"] = '"SSLKey": "sg_privkey.pem",'

        if no_conflicts_enabled(self.cluster_config):
            playbook_vars["no_conflicts"] = '"allow_conflicts": false,'
        try:
            revs_limit = get_revs_limit(self.cluster_config)
            playbook_vars["revs_limit"] = '"revs_limit": {},'.format(revs_limit)
        except KeyError:
            log.info("revs_limit no found in {}, Ignoring".format(self.cluster_config))
            playbook_vars["revs_limit"] = ''

        if is_delta_sync_enabled(self.cluster_config) and get_sg_version(self.cluster_config) >= "2.5.0":
            playbook_vars["delta_sync"] = '"delta_sync": { "enabled": true},'

        if get_sg_version(self.cluster_config) >= "2.8.0":
            playbook_vars["prometheous"] = '"metricsInterface": ":4986",'

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
            "start-sg-accel.yml",
            extra_vars=playbook_vars,
            subset=self.hostname
        )
        return status

    def __repr__(self):
        return "SgAccel: {}:{}\n".format(self.hostname, self.ip)
