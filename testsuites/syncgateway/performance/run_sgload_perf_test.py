
# This is intended to replace run_perf_test.py once gateload has been replaced by sgload

from __future__ import print_function

import sys
import os

from libraries.provision.ansible_runner import AnsibleRunner
from keywords.exceptions import ProvisioningError

from libraries.utilities.provisioning_config_parser import hosts_for_tag

from keywords.utils import log_info
from keywords.RemoteExecutor import RemoteExecutor


import argparse


def build_sgload(ansible_runner):

    ansible_status = ansible_runner.run_ansible_playbook(
        "build-sgload.yml",
        extra_vars={},
    )
    if ansible_status != 0:
        raise ProvisioningError("Failed to build sgload")


def run_sgload_on_single_loadgenerator(lgs_hosts, sgload_arg_list, sg_host):
    """
    This method blocks until sgload completes execution.  It only runs
    sgload on the first lg host. (for now)
    """
    lg_host = lgs_hosts[0]
    execute_sgload(lg_host, sgload_arg_list, sg_host)


def execute_sgload(lgs_host, sgload_arg_list, sg_host):

    # Update the arg list the the appropriate SG
    sgload_arg_list_modified = add_sync_gateway_url(sgload_arg_list, sg_host)

    # convert from list -> string
    # eg, ["--createreaders", "--numreaders", "100"] -> "--createreaders --numreaders 100"
    sgload_args_str = " ".join(sgload_arg_list_modified)

    rex = RemoteExecutor(lgs_host)

    # Build sgload command to pass to ssh client
    # eg, "sgload --createreaders --numreaders 100"
    log_info("sgload {}".format(sgload_args_str))
    command = "sgload {}".format(sgload_args_str)
    rex.must_execute(command)

    log_info("execute_sgload done.")


def stream_output(stdio_file_pointer, dest_file_pointer, abort_if_panic=False):

    for line in stdio_file_pointer:
        print(line, file=dest_file_pointer)
        if abort_if_panic and "panic" in line:
            raise Exception("Detected panic: {}".format(line))


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


def add_sync_gateway_url(sgload_arg_list, sg_host):
    """
    Add ['--sg-url', 'http://..'] to the list of args that will be passed to sgload
    """
    sgload_arg_list_copy = sgload_arg_list[:]  # make copy to avoid modifying the original list
    sgload_arg_list_copy.append("--sg-url")
    sgload_arg_list_copy.append("http://{}:4984/db/".format(sg_host))  # TODO: don't hardcode port or DB name
    return sgload_arg_list_copy


def run_sgload_perf_test(cluster_config, sgload_arg_list_main, skip_build_sgload):

    print("Running sgload perf test against cluster: {}".format(cluster_config))
    main_ansible_runner = AnsibleRunner(cluster_config)

    # Install + configure telegraf
    status = main_ansible_runner.run_ansible_playbook("install-telegraf.yml")
    if status != 0:
        raise ProvisioningError("Failed to install telegraf")

    # build_sgload (ansible)
    if not skip_build_sgload:
        build_sgload(main_ansible_runner)

    # get load generator and sg hostnames
    lg_hosts_main = get_load_generators_hosts(cluster_config)
    sg_hosts_main = get_sync_gateways_hosts(cluster_config)

    # Get the first SG host from the list of SG hosts
    sg_host_main = sg_hosts_main[0]

    run_sgload_on_single_loadgenerator(
        lg_hosts_main,
        sgload_arg_list_main,
        sg_host_main
    )

    log_info("Finished")


if __name__ == "__main__":

    # There is some complex argument parsing going on in order to be able to capture
    # certain arguments and process them, and pass through the rest of the arguments
    # down to sgload being invoked.
    #
    # The parse_known_args() call will essentially extract any arguments added via
    # parser.add_argument(), and the rest of the arguments will get read into
    # sgload_arg_list_main and then passed to sgload when invoked

    parser = argparse.ArgumentParser()
    parser.add_argument('--skip-build-sgload', action='store_true')
    args = parser.parse_known_args()
    known_args, sgload_arg_list_main = args  # unroll this tuple into named args

    try:
        main_cluster_config = os.environ["CLUSTER_CONFIG"]
    except KeyError:
        print ("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        sys.exit(1)

    run_sgload_perf_test(
        main_cluster_config,
        sgload_arg_list_main,
        known_args.skip_build_sgload,
    )
