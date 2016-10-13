
# This is intended to replace run_perf_test.py once gateload has been replaced by sgload

import requests
import time
import sys
import os
import paramiko

from provision.ansible_runner import AnsibleRunner
from keywords.exceptions import ProvisioningError

from libraries.utilities.provisioning_config_parser import hosts_for_tag

from keywords.utils import log_info
from libraries.utilities.log_expvars import wait_for_endpoints_alive_or_raise


def build_sgload(ansible_runner):

    status = ansible_runner.run_ansible_playbook(
        "build-sgload.yml",
        extra_vars={},
    )
    if status != 0:
        raise ProvisioningError("Failed to build sgload")


def start_sgload(lgs_hosts):
    for lgs_host in lgs_hosts:

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        log_info("SSH connection to {}".format(lgs_host))
        ssh.connect(lgs_host, username="vagrant") # TODO!! get this from ansible.cfg
        stdin, stdout, stderr = ssh.exec_command("sgload")
        log_info("stdout: {}".format(stdout.read()))
        log_info("stderr: {}".format(stderr.read()))


def wait_for_endpoints_dead(endpoints, num_attempts=1000, num_secs_between_attepts=5):
    """
    Wait for the given endpoints to be down
    """
    for i in range(num_attempts):
        endpoints_down = {}
        for endpoint in endpoints:
            endpoint_url = endpoint
            if not endpoint_url.startswith("http"):
                endpoint_url = "http://{}".format(endpoint_url)

            try:
                log_info("Checking if endpoint is down: {}".format(endpoint_url))
                requests.get(endpoint_url)
            except Exception as e:
                endpoints_down[endpoint_url] = True
                log_info("Endpoint is down. Got exception: {}".format(e))

        if len(endpoints_down) == len(endpoints):
            return

        time.sleep(num_secs_between_attepts)

    raise Exception("Give up waiting for endpoints to go down after {} attempts".format(num_attempts))


def get_load_generators_hosts(cluster_config):
    # Get gateload ips from ansible inventory
    lgs_hosts = hosts_for_tag(cluster_config, "load_generators")
    lgs = [lg["ansible_host"] for lg in lgs_hosts]
    return lgs

def get_load_generators_expvar_urls(cluster_config):
    lgs = get_load_generators_hosts(cluster_config)
    return [lg + ":9876/debug/vars" for lg in lgs]

if __name__ == "__main__":

    try:
        main_cluster_config = os.environ["CLUSTER_CONFIG"]
    except KeyError:
        print ("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        sys.exit(1)

    print("Running perf test against cluster: {}".format(main_cluster_config))
    main_ansible_runner = AnsibleRunner(main_cluster_config)

    # build_sgload (ansible)
    # build_sgload(main_ansible_runner)

    # call start-sgload.yml (ansible) -- just hardcode params in start-sgload.yml
    main_lgs_hosts = get_load_generators_hosts(main_cluster_config)
    start_sgload(main_lgs_hosts)

    # polling loop until can connect to expvars
    lgs_expvar_endpoints = get_load_generators_expvar_urls(main_cluster_config)
    wait_for_endpoints_alive_or_raise(lgs_expvar_endpoints, num_attempts=5)

    # polling loop until no longer listening on expvars port
    wait_for_endpoints_dead(lgs_expvar_endpoints)
