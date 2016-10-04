import os.path
import shutil
import sys
from optparse import OptionParser

from keywords.utils import log_info

from provision.ansible_runner import AnsibleRunner


def fetch_machine_stats(cluster_config, folder_name):

    ansible_runner = AnsibleRunner(config=cluster_config)

    print("\n")

    print("Pulling logs")
    # fetch logs from sync_gateway instances
    status = ansible_runner.run_ansible_playbook("fetch-machine-stats.yml")
    assert status == 0, "Failed to fetch machine stats"

    # zip logs and timestamp
    if os.path.isdir("/tmp/perf_logs"):

        # Move perf logs to performance_results
        shutil.move("/tmp/perf_logs", "testsuites/syncgateway/performance/results/{}/".format(folder_name))

    print("\n")


if __name__ == "__main__":
    usage = """usage: fetch_machine_stats.py
    --test-id=<test-id>
    """

    parser = OptionParser(usage=usage)

    parser.add_option("", "--test-id",
                      action="store", type="string", dest="test_id", default=None,
                      help="Test id to generate graphs for")

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    try:
        cluster_conf = os.environ["CLUSTER_CONFIG"]
    except KeyError as ke:
        log_info("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        raise KeyError("CLUSTER_CONFIG not defined. Unable to provision cluster.")

    if opts.test_id is None:
        print("You must provide a test identifier to run the test")
        sys.exit(1)

    fetch_machine_stats(cluster_conf, opts.test_id)
