import re
import os
import json

import requests
from requests import Session

from keywords.constants import SYNC_GATEWAY_CONFIGS
from keywords.utils import version_is_binary
from keywords.utils import log_r
from keywords.utils import version_and_build
from keywords.utils import hostname_for_url
from keywords.utils import log_info
from keywords.utils import log_warn
from keywords.utils import host_for_url
from exceptions import ProvisioningError

from libraries.provision.ansible_runner import AnsibleRunner
from jinja2 import Template


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
    resp = requests.get("http://{}:4984".format(host))
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


def verify_sync_gateway_version(host, expected_sync_gateway_version):
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
    resp = requests.get("http://{}:4985".format(host))
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


def load_sg_accel_config(sync_gateway_config, server_url):
    """ Loads a sg_accel configuration for modification"""
    with open(sync_gateway_config) as default_conf:
        server_ip = host_for_url(server_url)
        template = Template(default_conf.read())
        temp = template.render(
            couchbase_server_primary_node=server_ip,
            is_index_writer="true"
        )
        data = json.loads(temp)

    log_info("Loaded sg_accel config: {}".format(data))
    return data


class SyncGateway:

    def __init__(self, url=None):
        self._session = Session()
        self.url = url

    def install_sync_gateway(self, cluster_config, sync_gateway_version, sync_gateway_config):

        # Dirty hack -- these have to be put here in order to avoid circular imports
        from libraries.provision.install_sync_gateway import install_sync_gateway
        from libraries.provision.install_sync_gateway import SyncGatewayConfig

        if version_is_binary(sync_gateway_version):
            version, build = version_and_build(sync_gateway_version)
            print("VERSION: {} BUILD: {}".format(version, build))
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

    def start_sync_gateway(self, cluster_config, url, config):
        target = hostname_for_url(cluster_config, url)

        log_info("Starting sync_gateway on {} ...".format(target))
        ansible_runner = AnsibleRunner(cluster_config)
        config_path = os.path.abspath(config)
        status = ansible_runner.run_ansible_playbook(
            "start-sync-gateway.yml",
            extra_vars={
                "sync_gateway_config_filepath": config_path
            },
            subset=target
        )

        if status != 0:
            raise ProvisioningError("Could not start sync_gateway")

        running_status = self.is_sync_gateway_running(cluster_config, url)
        if not running_status:
            # if running_status  != 0, sync gateway is not running
            log_warn("Status of sync_gateway service start was returned as zero but sync_gateway is not running")
            raise ProvisioningError("Could not start sync_gateway")

        return 0

    def stop_sync_gateway(self, cluster_config, url):
        target = hostname_for_url(cluster_config, url)
        log_info("Shutting down sync_gateway on {} ...".format(target))
        ansible_runner = AnsibleRunner(cluster_config)
        status = ansible_runner.run_ansible_playbook(
            "stop-sync-gateway.yml",
            subset=target
        )
        if status != 0:
            raise ProvisioningError("Could not stop sync_gateway")

        running_status = self.is_sync_gateway_running(cluster_config, url)
        if running_status:
            # if running_status  == 0, sync gateway is still running
            log_warn("Status of sync_gateway service stop was returned as zero but sync_gateway is still running")
            raise ProvisioningError("Could not stop sync_gateway")

        return 0

    def is_sync_gateway_running(self, cluster_config, url):
        target = hostname_for_url(cluster_config, url)
        log_info("Checking sync_gateway status on {} ...".format(target))
        ansible_runner = AnsibleRunner(cluster_config)
        status = ansible_runner.run_ansible_playbook(
            "check-sync-gateway.yml",
            subset=target
        )

        # Running
        if status == 0:
            return True

        # Not running
        return False


class SGAccel:

    def __init__(self, url=None):
            self._session = Session()
            self.url = url

    def start_sg_accel(self, cluster_config, url, config):
        target = hostname_for_url(cluster_config, url)

        log_info("Starting sg_accel on {} ...".format(target))
        ansible_runner = AnsibleRunner(cluster_config)
        config_path = os.path.abspath(config)
        status = ansible_runner.run_ansible_playbook(
            "start-sg-accel.yml",
            extra_vars={
                "sync_gateway_config_filepath": config_path
            },
            subset=target
        )

        if status != 0:
            raise ProvisioningError("Could not start sg_accel")

        running_status = self.is_sg_accel_running(cluster_config, url)
        if not running_status:
            # if running_status  != 0, sync gateway is not running
            log_warn("Status of sg_accel service start was returned as zero but sg_accel is not running")
            raise ProvisioningError("Could not start sg_accel")

        return 0

    def stop_sg_accel(self, cluster_config, url):
        target = hostname_for_url(cluster_config, url)
        log_info("Shutting down sg_accel on {} ...".format(target))
        ansible_runner = AnsibleRunner(cluster_config)
        status = ansible_runner.run_ansible_playbook(
            "stop-sg-accel.yml",
            subset=target
        )
        if status != 0:
            raise ProvisioningError("Could not stop sg_accel")

        running_status = self.is_sg_accel_running(cluster_config, url)
        if running_status:
            # if running_status  == 0, sync gateway is still running
            log_warn("Status of sg_accel service stop was returned as zero but sg_accel is still running")
            raise ProvisioningError("Could not stop sg_accel")

        return 0

    def is_sg_accel_running(self, cluster_config, url):
        target = hostname_for_url(cluster_config, url)
        log_info("Checking sg_accel status on {} ...".format(target))
        ansible_runner = AnsibleRunner(cluster_config)
        status = ansible_runner.run_ansible_playbook(
            "check-sg-accel.yml",
            subset=target
        )

        # Running
        if status == 0:
            return True

        # Not running
        return False
