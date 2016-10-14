
# This is intended to replace run_perf_test.py once gateload has been replaced by sgload

import requests
import time
import sys
import os
import paramiko
import traceback
import random

from provision.ansible_runner import AnsibleRunner
from keywords.exceptions import ProvisioningError

from libraries.utilities.provisioning_config_parser import hosts_for_tag

from keywords.utils import log_info
from keywords.utils import log_error

from ansible import constants

import concurrent.futures
import argparse

def build_sgload(ansible_runner):

    status = ansible_runner.run_ansible_playbook(
        "build-sgload.yml",
        extra_vars={},
    )
    if status != 0:
        raise ProvisioningError("Failed to build sgload")

def run_sgload_on_loadgenerators(lgs_hosts, sgload_arg_list):
    """
    This method blocks until sgload completes execution on all of the hosts
    specified in lgs_hosts
    """
    futures = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=20) as executor:
        for lgs_host in lgs_hosts:
            future = executor.submit(execute_sgload, lgs_host, sgload_arg_list)
            futures.append(future)

    for future in futures:
        if future.exception() is not None:
            log_error("Exception running run_sgload_on_loadgenerators: {}".format(future.exception()))
            raise future.exception()

def execute_sgload(lgs_host, sgload_arg_list):

    try:

        # convert from list -> string
        # eg, ["--createreaders", "--numreaders", "100"] -> "--createreaders --numreaders 100"
        sgload_args_str = " ".join(sgload_arg_list)

        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect SSH client to remote machine
        log_info("SSH connection to {}".format(lgs_host))
        ssh.connect(lgs_host, username=constants.DEFAULT_REMOTE_USER)

        # Build sgload command to pass to ssh client
        # eg, "sgload --createreaders --numreaders 100"
        log_info("sgload {}".format(sgload_args_str))
        command = "sgload {}".format(sgload_args_str)

        # Run comamnd on remote machine
        stdin, stdout, stderr = ssh.exec_command(command)

        # Print out output to console
        log_info("{}".format(stdout.read()))
        log_error("{}".format(stderr.read()))

        # Close the connection since we're done with it
        ssh.close()

        log_info("execute_sgload done.")

    except Exception as e:
        log_error("Exception calling execute_sgload: {}".format(e))
        log_error(traceback.format_exc())
        raise e


def get_load_generators_hosts(cluster_config):
    # Get load generator ips from ansible inventory
    return get_hosts_by_type(cluster_config, "load_generators")

def get_sync_gateways_hosts(cluster_config):
    # Get sync gateway ips from ansible inventory
    return get_hosts_by_type(cluster_config, "sync_gateways")

def get_hosts_by_type(cluster_config, host_type="load_generators"):
    lgs_hosts = hosts_for_tag(cluster_config, host_type)
    lgs = [lg["ansible_host"] for lg in lgs_hosts]
    return lgs

def add_sync_gateway_url(cluster_config, sgload_arg_list):
    """
    Add ['--sg-url', 'http://..'] to the list of args that will be passed to sgload
    """
    sg_hosts = get_sync_gateways_hosts(cluster_config)
    if len(sg_hosts) == 0:
        raise Exception("Did not find any SG hosts")
    sgload_arg_list.append("--sg-url")
    sgload_arg_list.append("http://{}:4984/db/".format(sg_hosts[0]))  ## TODO: don't hardcode port or DB name
    return sgload_arg_list

def get_lg2sg_map(lg_hosts, sg_hosts):
    """
    Assign load generators to sync gateways and return a map
    with the assignments where key=lg, val=sg:

    {'192.168.33.13': '192.168.33.11'}
    """

    lg2sgmap = {}
    for lg_host in lg_hosts:
        r = random.Random()
        highest_sg_index = len(sg_hosts) - 1
        sg_index = r.randint(0, highest_sg_index)
        sg_host = sg_hosts[sg_index]
        lg2sgmap[lg_host] = sg_host
    return lg2sgmap


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--skip-build-sgload', action='store_true')
    args = parser.parse_known_args()
    known_args, sgload_arg_list = args  # unroll this tuple into named args
    log_info("known_args: {}".format(known_args))
    log_info("sgload_args: {}".format(sgload_arg_list))

    try:
        main_cluster_config = os.environ["CLUSTER_CONFIG"]
    except KeyError:
        print ("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        sys.exit(1)

    # TODO: this should assign sync gateways to different load generators
    sgload_arg_list = add_sync_gateway_url(main_cluster_config, sgload_arg_list)
    log_info("sgload_args w/ sg url: {}".format(sgload_arg_list))

    print("Running perf test against cluster: {}".format(main_cluster_config))
    main_ansible_runner = AnsibleRunner(main_cluster_config)

    # build_sgload (ansible)
    if not known_args.skip_build_sgload:
        build_sgload(main_ansible_runner)

    # get load generator and sg hostnames
    lg_hosts = get_load_generators_hosts(main_cluster_config)
    sg_hosts = get_sync_gateways_hosts(main_cluster_config)

    # Get a map from load generator hostnames to sync gateway hostnames
    # eg, {'192.168.33.13': '192.168.33.11'} key=lg, val=sg
    lg2sg = get_lg2sg_map(lg_hosts, sg_hosts)

    run_sgload_on_loadgenerators(
        lg_hosts,
        sgload_arg_list
    )

    log_info("Finished")


