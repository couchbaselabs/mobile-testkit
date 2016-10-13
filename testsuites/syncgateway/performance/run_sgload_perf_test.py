
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
from keywords.utils import log_error

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
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        for lgs_host in lgs_hosts:
            executor.submit(execute_sgload, lgs_host, sgload_arg_list)

def execute_sgload(lgs_host, sgload_arg_list):

    # convert from list -> string
    # eg, ["--createreaders", "--numreaders", "100"] -> "--createreaders --numreaders 100"
    sgload_args_str = " ".join(sgload_arg_list)

    # Create SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Connect SSH client to remote machine
    log_info("SSH connection to {}".format(lgs_host))
    ssh.connect(lgs_host, username="vagrant")  # TODO!! get this from ansible.cfg

    # Build sgload command to pass to ssh client
    # eg, "sgload --createreaders --numreaders 100"
    command = "sgload {}".format(sgload_args_str)

    # Run comamnd on remote machine
    stdin, stdout, stderr = ssh.exec_command(command)

    # Print out output to console
    log_info("{}".format(stdout.read()))
    log_error("{}".format(stderr.read()))

    log_info("execute_sgload done.")

def get_load_generators_hosts(cluster_config):
    # Get gateload ips from ansible inventory
    lgs_hosts = hosts_for_tag(cluster_config, "load_generators")
    lgs = [lg["ansible_host"] for lg in lgs_hosts]
    return lgs

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--skip-build', action='store_true')
    args = parser.parse_known_args()
    known_args, sgload_arg_list = args  # unroll this tuple into named args
    log_info("known_args: {}".format(known_args))
    log_info("sgload_args: {}".format(sgload_arg_list))

    try:
        main_cluster_config = os.environ["CLUSTER_CONFIG"]
    except KeyError:
        print ("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        sys.exit(1)

    print("Running perf test against cluster: {}".format(main_cluster_config))
    main_ansible_runner = AnsibleRunner(main_cluster_config)

    # build_sgload (ansible)
    if not known_args.skip_build:
        build_sgload(main_ansible_runner)

    # call start-sgload.yml (ansible) -- just hardcode params in start-sgload.yml
    load_generator_hostnames = get_load_generators_hosts(main_cluster_config)
    run_sgload_on_loadgenerators(
        load_generator_hostnames,
        sgload_arg_list
    )

    log_info("Finished")


