import logging
import os

import requests

import libraries.testkit.settings
from libraries.provision.ansible_runner import AnsibleRunner
from utilities.cluster_config_utils import is_cbs_ssl_enabled, is_xattrs_enabled, no_conflicts_enabled, get_revs_limit
from utilities.cluster_config_utils import get_sg_replicas, get_sg_use_views, get_sg_version, sg_ssl_enabled, get_logging
from keywords.utils import add_cbs_to_sg_config_server_field, log_info
from keywords.constants import SYNC_GATEWAY_CERT


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
            "logging": "",
            "autoimport": "",
            "xattrs": "",
            "no_conflicts": "",
            "revs_limit": "",
            "num_index_replicas": "",
            "sg_use_views": "",
            "logging": "",
            "sslcert": "",
            "sslkey": "",
            "couchbase_server_primary_node": couchbase_server_primary_node
        }

        if get_sg_version(self.cluster_config) >= "2.1.0":
            logging_config = '"logging": {"debug": {"enabled": true}'
            try:
                redact_level = get_logging(self.cluster_config)
                playbook_vars["logging"] = '{}, "redaction_level": "{}" {},'.format(logging_config, redact_level, "}")
            except KeyError as ex:
                log_info("Keyerror in getting logging{}".format(ex.message))
                playbook_vars["logging"] = '{} {},'.format(logging_config, "}")
            if get_sg_use_views(self.cluster_config):
                playbook_vars["sg_use_views"] = '"use_views": true,'
            else:
                num_replicas = get_sg_replicas(self.cluster_config)
                playbook_vars["num_index_replicas"] = '"num_index_replicas": {},'.format(num_replicas)
        else:
            playbook_vars["logging"] = '"log": ["*"],'

        if is_xattrs_enabled(self.cluster_config):
            playbook_vars["autoimport"] = '"import_docs": "continuous",'
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

        status = self.ansible_runner.run_ansible_playbook(
            "start-sg-accel.yml",
            extra_vars=playbook_vars,
            subset=self.hostname
        )
        return status

    def __repr__(self):
        return "SgAccel: {}:{}\n".format(self.hostname, self.ip)
