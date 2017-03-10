import json
import datetime
import os
import sys
import matplotlib
import matplotlib.pyplot as plt

from optparse import OptionParser
from collections import OrderedDict
from libraries.utilities.provisioning_config_parser import hosts_for_tag

matplotlib.rcParams.update({'font.size': 6})


def keys_present(keys, dictionary):
    for key in keys:
        if key not in dictionary:
            # only plot timestamps with all info
            return False
    return True


def plot_gateload_expvars(figure, json_file_name):

    print("Plotting gateload expvars ...")

    with open(json_file_name, "r") as f:
        obj = json.loads(f.read(), object_pairs_hook=OrderedDict)

    datetimes = []
    p95s = []
    p99s = []
    docs_pushed = []
    docs_pulled = []
    docs_failed_to_push = []
    docs_failed_to_pull = []

    number_ns_per_sec = 1000000000.0

    for timestamp in obj:

        # only plot if p95 and p99 exist in expvars
        if "PushToSubscriberInteractive" in obj[timestamp]["expvars"]["gateload"]["ops"]:
            datetimes.append(datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f"))

            p95 = obj[timestamp]["expvars"]["gateload"]["ops"]["PushToSubscriberInteractive"]["p95"] / number_ns_per_sec
            p95s.append(p95)

            p99 = obj[timestamp]["expvars"]["gateload"]["ops"]["PushToSubscriberInteractive"]["p99"] / number_ns_per_sec
            p99s.append(p99)

            docs_pushed.append(obj[timestamp]["expvars"]["gateload"]["total_doc_pushed"])
            docs_pulled.append(obj[timestamp]["expvars"]["gateload"]["total_doc_pulled"])

            if "total_doc_failed_to_push" in obj[timestamp]["expvars"]["gateload"]:
                docs_failed = obj[timestamp]["expvars"]["gateload"]["total_doc_failed_to_push"]
                docs_failed_to_push.append(docs_failed)
                print("!!! ERROR: docs failed to push: {} !!!".format(docs_failed_to_push))

            if "total_doc_failed_to_pull" in obj[timestamp]["expvars"]["gateload"]:
                docs_failed = obj[timestamp]["expvars"]["gateload"]["total_doc_failed_to_pull"]
                docs_failed_to_pull.append(docs_failed)
                print("!!! ERROR: docs failed to pull: {} !!!".format(docs_failed_to_pull))

    # Plot p95 / p99
    ax1 = figure.add_subplot(211)
    ax1.set_title("PushToSubscriberInteractive (seconds): p95 (cyan) / p99 (magenta)")
    ax1.plot(datetimes, p95s, "cs", datetimes, p99s, "m^")
    # for i, j in zip(datetimes, p95):
    #     ax1.annotate(str(j), xy=(i, j))

    # Plot docs pushed / docs pulled
    ax2 = figure.add_subplot(212)
    ax2.set_title("total_doc_pushed (red) / total_doc_pulled (yellow)")
    ax2.plot(datetimes, docs_pushed, "rs", datetimes, docs_pulled, "y^")

    push_failed_label_pos = (min(datetimes), 0.75 * max(docs_pulled))
    pull_failed_label_pos = (min(datetimes), 0.25 * max(docs_pulled))

    # Plot doc push / pull failures
    if len(docs_failed_to_push) > 0:
        ax2.text(
            push_failed_label_pos[0],
            push_failed_label_pos[1],
            "ERROR - DOCS FAILED TO PUSH: {}".format(max(docs_failed_to_push)),
            color="red",
            fontsize=20
        )

    if len(docs_failed_to_pull) > 0:
        ax2.text(
            pull_failed_label_pos[0],
            pull_failed_label_pos[1],
            "ERROR - DOCS FAILED TO PULL: {}".format(max(docs_failed_to_pull)),
            color="red",
            fontsize=20
        )

    figure.autofmt_xdate()

    if len(docs_failed_to_push) > 0 or len(docs_failed_to_pull) > 0:
        return False

    return True


def plot_sync_gateway_expvars(cluster_config, figure, json_file_name):

    print("Plotting sync_gateway expvars ...")

    # Get writer hostnames for provisioning_config
    sg_writers = hosts_for_tag(cluster_config, "sg_accels")
    sg_writer_hostnames = [sg_writer["ansible_host"] for sg_writer in sg_writers]

    with open(json_file_name, "r") as f:
        obj = json.loads(f.read(), object_pairs_hook=OrderedDict)

    datetimes = []
    memstats_alloc = []
    memstats_sys = []

    writer_datetimes = []
    writer_memstats_alloc = []
    writer_memstats_sys = []

    for timestamp in obj:

        endpoint = obj[timestamp]["endpoint"]
        hostname = endpoint.split(":")[0]

        if hostname in sg_writer_hostnames:
            writer_datetimes.append(datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f"))
            writer_memstats_alloc.append(obj[timestamp]["expvars"]["memstats"]["Alloc"])
            writer_memstats_sys.append(obj[timestamp]["expvars"]["memstats"]["Sys"])
        else:
            datetimes.append(datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f"))
            memstats_alloc.append(obj[timestamp]["expvars"]["memstats"]["Alloc"])
            memstats_sys.append(obj[timestamp]["expvars"]["memstats"]["Sys"])

    # Plot Alloc / Sys
    ax1 = figure.add_subplot(111)
    ax1.set_title("(writers=blue, readers=green) memstats.Alloc (square) / memstats.Sys (triangle)")
    ax1.plot(datetimes, memstats_alloc, "gs", datetimes, memstats_sys, "g^")
    ax1.plot(writer_datetimes, writer_memstats_alloc, "bs", writer_datetimes, writer_memstats_sys, "b^")

    figure.autofmt_xdate()


def plot_machine_stats(cluster_config, figure, folder_path):

    print("Plotting machine stats ...")

    folders = [x[0] for x in os.walk(folder_path)]

    machine_stats = dict()
    # entry at one is the first subdirect
    for subfolder in folders[1:]:

        # Get name of sg
        path_components = os.path.split(subfolder)
        name = path_components[len(path_components) - 1]

        # Get CPU stats dict for sg
        with open("{}/cpu_stats.json".format(subfolder), "r") as f:
            obj = json.loads(f.read())
            machine_stats[name] = obj

    ax3 = figure.add_subplot(111)
    ax3.set_title("CPU percent (writers=blue, readers=green")

    # Get writer hostnames for provisioning_config
    sg_writers = hosts_for_tag(cluster_config, "sg_accels")
    sg_writer_hostnames = [sg_writer["inventory_hostname"] for sg_writer in sg_writers]

    for machine in machine_stats:
        entity = machine_stats[machine]

        datetimes = []
        cpu_percents = []

        # create a list of timestamps with the corresponding CPU percent
        for timestamp in entity.keys():
            datetimes.append(datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f"))
            cpu_percents.append(entity[timestamp]["cpu_percent"])

        # Plot blue if writer, green if reader
        if machine in sg_writer_hostnames:
            ax3.plot(datetimes, cpu_percents, "bo")
        else:
            ax3.plot(datetimes, cpu_percents, "go")

    figure.autofmt_xdate()


def analze_perf_results(cluster_config, test_id):

    print("Generating graphs for {}".format(test_id))

    # Generate plot of gateload expvars
    fig1 = plt.figure()
    fig1.text(0.5, 0.04, 'Gateload Expvars', ha='center', va='center')
    valid_results = plot_gateload_expvars(fig1, "testsuites/syncgateway/performance/results/{}/gateload_expvars.json".format(test_id))
    plt.savefig("testsuites/syncgateway/performance/results/{}/gateload_expvars.png".format(test_id), dpi=300)
    if not valid_results:
        print("FAILURE STATE. Some docs failed to push and/or pull. Exiting...")
        sys.exit(1)

    # Generate plot of sync_gateway expvars
    fig2 = plt.figure()
    fig2.text(0.5, 0.04, 'sync_gateway expvars', ha='center', va='center')
    plot_sync_gateway_expvars(cluster_config, fig2, "testsuites/syncgateway/performance/results/{}/sync_gateway_expvars.json".format(test_id))
    plt.savefig("testsuites/syncgateway/performance/results/{}/sync_gateway_expvars.png".format(test_id), dpi=300)

    # Generate plot of machine stats
    fig3 = plt.figure()
    fig3.text(0.5, 0.04, 'sync_gateway CPU', ha='center', va='center')
    plot_machine_stats(cluster_config, fig3, "testsuites/syncgateway/performance/results/{}/perf_logs/".format(test_id))
    plt.savefig("testsuites/syncgateway/performance/results/{}/sync_gateway_machine_stats.png".format(test_id), dpi=300)


if __name__ == "__main__":
    usage = """usage: analyze_perf_results.py
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
        print ("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        raise KeyError("CLUSTER_CONFIG not defined. Unable to provision cluster.")

    if opts.test_id is None:
        print("You must provide a test identifier to run the test")
        sys.exit(1)

    analze_perf_results(cluster_conf, opts.test_id)
