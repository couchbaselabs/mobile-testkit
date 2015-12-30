import time
import datetime
import requests
import json

from requests.exceptions import ConnectionError

from provisioning_config_parser import hosts_for_tag


def write_gateload_expvars(results_obj, endpoint):

        resp = requests.get("http://{}".format(endpoint))
        resp.raise_for_status()
        expvars = resp.json()

        now = "{}".format(datetime.datetime.utcnow())
        results_obj[now] = dict()

        try:
            results_obj[now]["endpoint"] = endpoint
            results_obj[now]["p95"] = expvars["gateload"]["ops"]["PushToSubscriberInteractive"]["p95"]
            results_obj[now]["p99"] = expvars["gateload"]["ops"]["PushToSubscriberInteractive"]["p99"]
            results_obj[now]["total_doc_pushed"] = expvars["gateload"]["total_doc_pushed"]
            results_obj[now]["total_doc_pulled"] = expvars["gateload"]["total_doc_pulled"]
            results_obj[now]["user_active"] = expvars["gateload"]["user_active"]
            results_obj[now]["user_awake"] = expvars["gateload"]["user_awake"]

        except Exception as e:
            # P95 and P99 may have not been calculated as of yet
            print("Failed to connect: {}".format(e))
            results_obj[now]["error"] = "!! Failed to connect to endpoint: {}\n".format(endpoint)


def write_sync_gateway_expvars(results_obj, endpoint):

        resp = requests.get("http://{}".format(endpoint))
        resp.raise_for_status()
        expvars = resp.json()

        now = "{}".format(datetime.datetime.utcnow())
        results_obj[now] = {
            "endpoint": endpoint,
            "memstats": {
                "Alloc": expvars["memstats"]["Alloc"],
                "Sys": expvars["memstats"]["Sys"],
                "HeapAlloc": expvars["memstats"]["HeapAlloc"],
                "HeapSys": expvars["memstats"]["HeapSys"]
            }
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


    date_time = time.strftime("%Y-%m-%d-%H-%M-%S")
    target_test_filename = "performance_results/{}/expvars.json".format(folder_name)

    with open(target_test_filename, "w") as f:

        start_time = time.time()

        results = dict()

        gateload_is_running = True
        while gateload_is_running:

            # Caputure expvars for gateloads
            for endpoint in lgs_expvar_endpoints:
                try:
                    write_gateload_expvars(results, endpoint)
                except ConnectionError as he:
                    # connection to gateload expvars has been closed
                    print(he)
                    gateload_is_running = False

            # Caputure expvars for sync_gateways
            for endpoint in sgs_expvar_endpoints:
                write_sync_gateway_expvars(results, endpoint)

            print("Elapsed: {}".format(time.time() - start_time))
            time.sleep(30)

        f.write(json.dumps(results, indent=4))
