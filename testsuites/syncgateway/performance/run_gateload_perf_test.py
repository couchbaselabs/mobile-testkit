import os
import shutil
import time
import sys
import collections

from optparse import OptionParser
from libraries.provision.ansible_runner import AnsibleRunner
import generate_gateload_configs
from keywords.exceptions import ProvisioningError
from libraries.utilities.log_expvars import log_expvars
from libraries.utilities.fetch_sync_gateway_profile import fetch_sync_gateway_profile
from kill_gateload import kill_gateload

GateloadParams = collections.namedtuple(
    "GateloadParams",
    [
        "number_pullers",
        "number_pushers",
        "doc_size",
        "runtime_ms",
        "rampup_interval_ms",
        "feed_type",
        "sleep_time_ms",
        "channel_active_users",
        "channel_concurrent_users"
    ]
)


def run_gateload_perf_test(gen_gateload_config, test_id, gateload_params, delay_profiling_secs, delay_expvar_collect_secs):

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

    if int(gateload_params.number_pullers) > 0 and not gen_gateload_config:
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
            test_id=test_run_id,
            gateload_params=gateload_params
        )

    print(">>> Starting profile collection scripts")
    runtime_s = int(gateload_params.runtime_ms) // 1000
    status = ansible_runner.run_ansible_playbook(
        "start-profile-collection.yml",
        extra_vars={
            "stats_run_time": runtime_s,
            "delay_profiling_secs": int(delay_profiling_secs)
        },
    )
    assert status == 0, "Could not start profiling collection scripts"

    # Start gateload
    print(">>> Starting gateload with {0} pullers and {1} pushers".format(
        gateload_params.number_pullers, gateload_params.number_pushers
    ))
    status = ansible_runner.run_ansible_playbook(
        "start-gateload.yml",
        extra_vars={
            "delay_expvar_collect_secs": int(delay_expvar_collect_secs)
        },
    )
    assert status == 0, "Could not start gateload"

    # write expvars to file, will exit when gateload scenario is done
    print(">>> Logging expvars")
    gateload_finished_successfully = log_expvars(cluster_config, test_run_id)

    print(">>> Fetch Sync Gateway profile")
    fetch_sync_gateway_profile(cluster_config, test_run_id)

    print(">>> Shutdown gateload")
    kill_gateload()

    if not gateload_finished_successfully:
        raise RuntimeError("It appears that gateload did not finish successfully.  Check logs for details")


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
    --sleep-time-ms=10000
    --channel-active-users=40
    --channel-concurrent-users=40
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

    parser.add_option("", "--sleep-time-ms",
                      action="store", dest="sleep_time_ms",
                      default=None,
                      help="Default sleep time for pusher between ops")

    parser.add_option("", "--channel-active-users",
                      action="store", dest="channel_active_users",
                      default=None,
                      help="Number of users for a given channel")

    parser.add_option("", "--channel-concurrent-users",
                      action="store", dest="channel_concurrent_users",
                      default=None,
                      help="The number of active users assigned to a channel")

    parser.add_option("", "--delay-profiling-secs",
                      action="store", dest="delay_profiling_secs",
                      default=None,
                      help="The delay time between profiling")

    parser.add_option("", "--delay-expvar-collect-secs",
                      action="store", dest="delay_expvar_collect_secs",
                      default=None,
                      help="The delay time between expvar collection")

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    if opts.test_id is None:
        print("You must provide a test identifier to run the test")
        sys.exit(1)

    # Validate feed_type
    valid_feed_types = ["continuous", "longpoll"]
    if opts.feed_type not in valid_feed_types:
        raise ProvisioningError("Make sure you provide a valid feed type!")

    # Wrap gateload params into a named tuple
    gateload_params_from_args = GateloadParams(
        number_pullers=opts.number_pullers,
        number_pushers=opts.number_pushers,
        doc_size=opts.doc_size,
        runtime_ms=opts.runtime_ms,
        rampup_interval_ms=opts.rampup_interval_ms,
        feed_type=opts.feed_type,
        sleep_time_ms=opts.sleep_time_ms,
        channel_active_users=opts.channel_active_users,
        channel_concurrent_users=opts.channel_concurrent_users
    )

    # Start load generator
    run_gateload_perf_test(
        gen_gateload_config=opts.gen_gateload_config,
        test_id=opts.test_id,
        gateload_params=gateload_params_from_args,
        delay_profiling_secs=opts.delay_profiling_secs,
        delay_expvar_collect_secs=opts.delay_expvar_collect_secs
    )
