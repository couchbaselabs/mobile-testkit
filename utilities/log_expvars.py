import time
import datetime
import requests
import json

from collections import OrderedDict

from requests.exceptions import ConnectionError

from provisioning_config_parser import hosts_for_tag


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
    lgs = [lg["ansible_ssh_host"] for lg in lgs_host_vars]

    print("Monitoring gateloads: {}".format(lgs))
    lgs_expvar_endpoints = [lg + ":9876/debug/vars" for lg in lgs]

    # Get sync_gateway ips from ansible inventory
    sgs_host_vars = hosts_for_tag("sync_gateways")
    sgs = [sgv["ansible_ssh_host"] for sgv in sgs_host_vars]

    print("Monitoring sync_gateways: {}".format(sgs))
    sgs_expvar_endpoints = [sg + ":4985/_expvar" for sg in sgs]

    start_time = time.time()

    gateload_results = OrderedDict()
    syncgateway_results = OrderedDict()

    gateload_is_running = True
    while gateload_is_running:

        # Caputure expvars for gateloads
        for endpoint in lgs_expvar_endpoints:
            try:
                write_expvars(gateload_results, endpoint)
            except ConnectionError as he:
                # connection to gateload expvars has been closed
                print(he)
                gateload_is_running = False

        # Caputure expvars for sync_gateways
        for endpoint in sgs_expvar_endpoints:
            write_expvars(syncgateway_results, endpoint)

        print("Elapsed: {}".format(time.time() - start_time))
        time.sleep(30)

    with open("performance_results/{}/gateload_expvars.json".format(folder_name), "w") as f:
        f.write(json.dumps(gateload_results))

    with open("performance_results/{}/sync_gateway_expvars.json".format(folder_name), "w") as f:
        f.write(json.dumps(syncgateway_results))
