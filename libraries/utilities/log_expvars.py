import time
import datetime
import requests
import json

from collections import OrderedDict

from requests.exceptions import ConnectionError

from provisioning_config_parser import hosts_for_tag


def dump_results(test_folder, gateload_results, sync_gateway_results):
    filename = "testsuites/syncgateway/performance/results/{}/gateload_expvars.json".format(test_folder)
    print("Writing gateload_expvars to: {}".format(filename))
    with open(filename, "w") as f:
        f.write(json.dumps(gateload_results))

    filename = "testsuites/syncgateway/performance/results/{}/sync_gateway_expvars.json".format(test_folder)
    print("Writing sync_gateway_expvars to: {}".format(filename))
    with open(filename, "w") as f:
        f.write(json.dumps(sync_gateway_results))


def write_expvars(results_obj, endpoint):

        resp = requests.get("http://{}".format(endpoint))
        resp.raise_for_status()
        expvars = resp.json()

        now = "{}".format(datetime.datetime.utcnow())
        results_obj[now] = {
            "endpoint": endpoint,
            "expvars": expvars
        }


def log_expvars(folder_name):
    usage = """
    usage: log_expvars.py"
    """

    # Get gateload ips from ansible inventory
    lgs_host_vars = hosts_for_tag("load_generators")
    lgs = [lg["ansible_host"] for lg in lgs_host_vars]
    lgs_expvar_endpoints = [lg + ":9876/debug/vars" for lg in lgs]
    print("Monitoring gateloads until they finish: {}".format("\n".join(lgs_expvar_endpoints)))

    # Get sync_gateway ips from ansible inventory
    sgs_host_vars = hosts_for_tag("sync_gateways")
    sgs = [sgv["ansible_host"] for sgv in sgs_host_vars]
    sgs_expvar_endpoints = [sg + ":4985/_expvar" for sg in sgs]
    print("Monitoring sync_gateways: {}".format("\n".join(sgs_expvar_endpoints)))

    # Give gateload a chance to startup, also useful for debugging issues
    print("Waiting 15s for gateload to startup")
    time.sleep(15)
    print("Done waiting for gateload to startup")

    # Verify that sync gateway expvar endpoints are reachable
    for sgs_expvar_endpoint in sgs_expvar_endpoints:
        resp = requests.get(sgs_expvar_endpoint)
        resp.raise_for_status()
        print("{}: OK".format(sgs_expvar_endpoint))

    start_time = time.time()
    gateload_results = OrderedDict()
    sync_gateway_results = OrderedDict()

    gateload_is_running = True
    while gateload_is_running:

        # Caputure expvars for gateloads
        for endpoint in lgs_expvar_endpoints:
            try:
                write_expvars(gateload_results, endpoint)
            except ConnectionError as he:
                # connection to gateload expvars has been closed
                print("Gateload no longer reachable. Writing expvars to {}".format(folder_name))
                dump_results(folder_name, gateload_results, sync_gateway_results)
                gateload_is_running = False

        # Capture expvars for sync_gateways
        for endpoint in sgs_expvar_endpoints:
            try:
                write_expvars(sync_gateway_results, endpoint)
            except ConnectionError as he:
                # Should not happen unless sg crashes
                print(he)
                print("ERROR: sync_gateway not reachable. Dumping results to {}".format(folder_name))
                dump_results(folder_name, gateload_results, sync_gateway_results)

        print("Elapsed: {} minutes".format((time.time() - start_time) / 60.0))
        time.sleep(30)
