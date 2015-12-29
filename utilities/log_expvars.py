import time
import datetime
import requests

from requests.exceptions import HTTPError

from provisioning_config_parser import hosts_for_tag


def write_expvars(file, endpoint):

        resp = requests.get("http://{}".format(endpoint))
        resp.raise_for_status()
        expvars = resp.json()

        try:
            file.write("\n############## VARS #############\n")
            file.write("Date / Time: {}\n".format(datetime.datetime.now()))
            file.write("Endpoint: {}\n".format(endpoint))

            p95 = expvars["gateload"]["ops"]["PushToSubscriberInteractive"]["p95"]
            p99 = expvars["gateload"]["ops"]["PushToSubscriberInteractive"]["p99"]
            total_doc_pushed = expvars["gateload"]["total_doc_pushed"]
            total_doc_pulled = expvars["gateload"]["total_doc_pulled"]
            user_active = expvars["gateload"]["user_active"]
            user_awake = expvars["gateload"]["user_awake"]

            file.write("P95: {}\n".format(p95))
            file.write("P99: {}\n".format(p99))
            file.write("total_doc_pushed: {}\n".format(total_doc_pushed))
            file.write("total_doc_pulled: {}\n".format(total_doc_pulled))
            file.write("user_active: {}\n".format(user_active))
            file.write("user_awake: {}\n".format(user_awake))

        except Exception as e:
            # P95 and P99 may have not been calculated as of yet
            print("Failed to connect: {}".format(e))
            file.write("!! Failed to connect to endpoint: {}\n".format(endpoint))


def log_expvars():
    usage = """
    usage: log_expvars.py"
    """

    # Get gateload ips from ansible inventory
    lgs_host_vars = hosts_for_tag("load_generators")
    lgs = [lg["ansible_ssh_host"] for lg in lgs_host_vars]

    print("Monitoring gateloads: {}".format(lgs))
    lgs_with_port = [lg + ":9876/debug/vars" for lg in lgs]

    # Get sync_gateway ips from ansible inventory
    sgs_host_vars = hosts_for_tag("sync_gateways")
    sgs = [sgv["ansible_ssh_host"] for sgv in sgs_host_vars]

    print("Monitoring sync_gateways: {}".format(sgs))
    sgs_with_port = [sg + ":4985/_expvar" for sg in sgs]

    endpoints = list()
    endpoints.extend(lgs_with_port)

    target_test_filename = "perf_test.log"

    with open(target_test_filename, "w") as f:

        start_time = time.time()
        f.write("Test beginning: {}".format(datetime.datetime.now()))

        gateload_is_running = True
        while gateload_is_running:
            for endpoint in endpoints:
                try:
                    write_expvars(f, endpoint)
                except HTTPError as he:
                    # connection to gateload expvars has been closed
                    print(he)
                    gateload_is_running = False

            print("Elapsed: {}".format(time.time() - start_time))
            time.sleep(60)
            f.write("\n\n\n")
