import os
import subprocess
import sys
import shutil
import time

from optparse import OptionParser
from lib.cluster import Cluster

from provision.ansible_runner import run_ansible_playbook


import generate_gateload_configs

from utilities.fetch_machine_stats import fetch_machine_stats
from utilities.log_expvars import log_expvars
from utilities.analyze_perf_results import analze_perf_results
from utilities.fetch_sg_logs import fetch_sync_gateway_logs
from utilities.fetch_sync_gateway_profile import fetch_sync_gateway_profile
from utilities.push_cbcollect_info_supportal import push_cbcollect_info_supportal


def run_tests(number_pullers, number_pushers, use_gateload, gen_gateload_config, test_id):
    if use_gateload:
        print "Using Gateload"
        print ">>> Starting gateload with {0} pullers and {1} pushers".format(number_pullers, number_pushers)

        if int(number_pullers) > 0 and not gen_gateload_config:
            raise Exception("You specified --num-pullers but did not set --gen-gateload-config")
            

        os.chdir("performance_tests/ansible/playbooks")

        # Build gateload
        subprocess.call(["ansible-playbook", "-i", "../../../provisioning_config", "build-gateload.yml"])

        # Generate gateload config
        if gen_gateload_config:
            generate_gateload_configs.main(number_pullers, number_pushers, test_id)

        # Start gateload
        subprocess.call(["ansible-playbook", "-i", "../../../provisioning_config", "start-gateload.yml"])

        os.chdir("../../..")

    else:
        print "Using Gatling"
        print ">>> Starting gatling with {0} pullers and {1} pushers".format(number_pullers, number_pushers)
        os.chdir("performance_tests/ansible/playbooks")

        # Configure gatling
        subprocess.call(["ansible-playbook", "-i", "../../../provisioning_config", "configure-gatling.yml"])

        # Run Gatling
        subprocess.call([
            "ansible-playbook", 
            "-i", "../../../provisioning_config",
            "run-gatling-theme.yml",
            "--extra-vars", "number_of_pullers={0} number_of_pushers={1}".format(number_pullers, number_pushers)
        ])

if __name__ == "__main__":
    usage = """usage: run_tests.py
    --number-pullers=<number_pullers>
    --number-pushers<number_pushers>
    --reset-sync-gw
    --use-gateload
    --gen-gateload-config
    --cb-collect-info
    """

    parser = OptionParser(usage=usage)

    parser.add_option("", "--number-pullers",
                      action="store", type="string", dest="number_pullers", default=8000,
                      help="number of pullers")

    parser.add_option("", "--number-pushers",
                      action="store", type="int", dest="number_pushers", default=5000,
                      help="number of pushers")

    parser.add_option("", "--use-gateload",
                      action="store_true", dest="use_gateload", default=False,
                      help="flag to set to use gateload")

    parser.add_option("", "--gen-gateload-config",
                      action="store_true", dest="gen_gateload_config", default=False,
                      help="flag to set to generate gateload config")

    parser.add_option("", "--reset-sync-gw",
                      action="store_true", dest="reset_sync_gateway", default=False,
                      help="reset CBS buckets, delete SG logs, restart SG")

    parser.add_option("", "--cb-collect-info",
                      action="store_true", dest="cb_collect_info", default=False,
                      help="calls cbcollect_info and pushes to http://supportal.couchbase.com/customer/mobileperf/")
    
    parser.add_option("", "--test-id",
                      action="store", dest="test_id", default=None,
                      help="test identifier to identify results of performance test")

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)
    
    if opts.test_id is None:
        print "You must provide a test identifier to run the test"
        sys.exit(1)

    test_run_id = "{}_{}".format(opts.test_id, time.strftime("%Y-%m-%d-%H-%M-%S"))

    # Create test results directory
    os.makedirs("performance_results/{}".format(test_run_id))

    if opts.reset_sync_gateway:
        print "Resetting Sync Gateway"
        cluster = Cluster()
        mode = cluster.reset("performance/sync_gateway_default_performance.json")
        print("Running in mode: {}".format(mode))

    # Copy provisioning_config to performance_results/ folder
    shutil.copy("provisioning_config", "performance_results/{}".format(test_run_id))

    # Start load generator
    run_tests(
        number_pullers=opts.number_pullers,
        number_pushers=opts.number_pushers,
        use_gateload=opts.use_gateload,
        gen_gateload_config=opts.gen_gateload_config,
        test_id=test_run_id
    )

    # write expvars to file, will exit when gateload scenario is done
    log_expvars(test_run_id)

    # Killing sync_gateway and sg_accel will trigger collection of
    #    1) machine_stats
    #    2) sync_gateway profile data
    run_ansible_playbook("stop-sync-gateway.yml")
    run_ansible_playbook("stop-sg-accel.yml")

    # HACK: refresh interval for resource stat collection is 10 seconds.
    #  Make sure enough time has passed before collecting json
    time.sleep(300)

    fetch_machine_stats(test_run_id)

    # Fetch profile for sync_gateway while the endpoints are still running
    fetch_sync_gateway_profile(test_run_id)

    # Generate graphs of the expvars and CPU
    analze_perf_results(test_run_id)

    # Copy sync_gateway logs to test results directory
    fetch_sync_gateway_logs(test_run_id, is_perf_run=True)

    # Invoke cb-collect-info and push to support portal
    if opts.cb_collect_info:
        push_cbcollect_info_supportal()
