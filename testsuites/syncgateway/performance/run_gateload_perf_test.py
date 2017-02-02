import os
import shutil
import time
import sys
from optparse import OptionParser
from libraries.provision.ansible_runner import AnsibleRunner
import generate_gateload_configs
from keywords.exceptions import ProvisioningError
from libraries.utilities.log_expvars import log_expvars
from libraries.utilities.fetch_sync_gateway_profile import fetch_sync_gateway_profile


def run_gateload_perf_test(number_pullers,
                           number_pushers,
                           gen_gateload_config,
                           test_id,
                           doc_size,
                           runtime_ms,
                           rampup_interval_ms,
                           feed_type):

    try:
        cluster_config = os.environ["CLUSTER_CONFIG"]
    except KeyError:
        print ("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        sys.exit(1)

    print("Running perf test against cluster: {}".format(cluster_config))
    ansible_runner = AnsibleRunner(cluster_config)

    # Install + configure telegraf
    status = ansible_runner.run_ansible_playbook("install-telegraf.yml")
    if status != 0:
        raise ProvisioningError("Failed to install telegraf")

    test_run_id = "{}_{}".format(test_id, time.strftime("%Y-%m-%d-%H-%M-%S"))

    # Create test results directory
    os.makedirs("testsuites/syncgateway/performance/results/{}".format(test_run_id))

    # Copy provisioning_config to performance_results/ folder
    shutil.copy("{}".format(cluster_config), "testsuites/syncgateway/performance/results/{}".format(test_run_id))

    if int(number_pullers) > 0 and not gen_gateload_config:
        raise Exception("You specified --num-pullers but did not set --gen-gateload-config")

    # Build gateload
    print(">>> Building gateload")
    status = ansible_runner.run_ansible_playbook(
        "build-gateload.yml",
        extra_vars={},
    )
    assert status == 0, "Could not build gateload"

    # Generate gateload config
    print(">>> Generate gateload configs")
    if gen_gateload_config:
        generate_gateload_configs.main(
            cluster_config=cluster_config,
            number_of_pullers=number_pullers,
            number_of_pushers=number_pushers,
            test_id=test_run_id,
            doc_size=doc_size,
            runtime_ms=runtime_ms,
            rampup_interval_ms=rampup_interval_ms,
            feed_type=feed_type
        )


    print(">>> Starting profile collection scripts")
    status = ansible_runner.run_ansible_playbook(
        "start-profile-collection.yml",
        extra_vars={},
    )
    assert status == 0, "Could not start profiling collection scripts"

    # Start gateload
    print(">>> Starting gateload with {0} pullers and {1} pushers".format(number_pullers, number_pushers))
    status = ansible_runner.run_ansible_playbook(
        "start-gateload.yml",
        extra_vars={},
    )
    assert status == 0, "Could not start gateload"

    # write expvars to file, will exit when gateload scenario is done
    print(">>> Logging expvars")
    log_expvars(cluster_config, test_run_id)

    print(">>> Fetch Sync Gateway profile")
    fetch_sync_gateway_profile(cluster_config, test_run_id)


if __name__ == "__main__":
    usage = """usage: run_perf_test.py
    --number-pullers=<number_pullers>
    --number-pushers<number_pushers>
    --reset-sync-gw
    --gen-gateload-config
    --cb-collect-info
    --test-id="test_1"
    --doc-size=1024
    --runtime-ms=2400000
    --rampup-interval-ms=120000
    --feed-type="continuous"
    """

    parser = OptionParser(usage=usage)

    parser.add_option("", "--number-pullers",
                      action="store", type="string", dest="number_pullers", default=8000,
                      help="number of pullers")

    parser.add_option("", "--number-pushers",
                      action="store", type="int", dest="number_pushers", default=5000,
                      help="number of pushers")

    parser.add_option("", "--gen-gateload-config",
                      action="store_true", dest="gen_gateload_config", default=True,
                      help="flag to set to generate gateload config")

    parser.add_option("", "--cb-collect-info",
                      action="store_true", dest="cb_collect_info", default=False,
                      help="calls cbcollect_info and pushes to http://supportal.couchbase.com/customer/mobileperf/")

    parser.add_option("", "--test-id",
                      action="store", dest="test_id", default=None,
                      help="test identifier to identify results of performance test")

    parser.add_option("", "--doc-size",
                      action="store", dest="doc_size",
                      default="1024",
                      help="Document size in bytes")

    parser.add_option("", "--runtime-ms",
                      action="store", dest="runtime_ms",
                      default="2400000",
                      help="How long to run for, in milliseconds")

    parser.add_option("", "--rampup-interval-ms",
                      action="store", dest="rampup_interval_ms",
                      default="120000",
                      help="How long to ramp up for, in milliseconds")

    parser.add_option("", "--feed-type",
                      action="store", dest="feed_type",
                      default=None,
                      help="The type of on feed to use for changes, 'continuous' or 'longpoll'")

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    if opts.test_id is None:
        print("You must provide a test identifier to run the test")
        sys.exit(1)

    # Validate feed_type
    valid_feed_types = ["continuous", "longpoll"]
    if opts.feed_type not in valid_feed_types:
        raise ProvisioningError("Make sure you provide a valid feed type!")

    # Start load generator
    run_gateload_perf_test(
        number_pullers=opts.number_pullers,
        number_pushers=opts.number_pushers,
        gen_gateload_config=opts.gen_gateload_config,
        test_id=opts.test_id,
        doc_size=opts.doc_size,
        runtime_ms=opts.runtime_ms,
        rampup_interval_ms=opts.rampup_interval_ms,
        feed_type=opts.feed_type
    )
