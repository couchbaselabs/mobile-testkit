import time
import datetime
import requests

from provisioning_config_parser import hosts_for_tag


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

        # in seconds
        test_time = 0
        collect_interval = 120

        while test_time < 1200:

            for endpoint in endpoints:
                try:
                    resp = requests.get("http://{}".format(endpoint))
                    print(resp.url)
                    f.write("\n############## VARS #############\n")
                    f.write("Date / Time: {}\n".format(datetime.datetime.now()))
                    f.write("Endpoint: {}\n".format(endpoint))

                    expvars = resp.json()

                    p95 = expvars["gateload"]["ops"]["PushToSubscriberInteractive"]["p95"]
                    p99 = expvars["gateload"]["ops"]["PushToSubscriberInteractive"]["p99"]
                    total_doc_pushed = expvars["gateload"]["total_doc_pushed"]
                    total_doc_pulled = expvars["gateload"]["total_doc_pulled"]
                    user_active = expvars["gateload"]["user_active"]
                    user_awake = expvars["gateload"]["user_awake"]

                    f.write("P95: {}\n".format(p95))
                    f.write("P99: {}\n".format(p99))
                    f.write("total_doc_pushed: {}\n".format(total_doc_pushed))
                    f.write("total_doc_pulled: {}\n".format(total_doc_pulled))
                    f.write("user_active: {}\n".format(user_active))
                    f.write("user_awake: {}\n".format(user_awake))

                except Exception as e:
                    print("Failed to connect: {}".format(e))
                    f.write("!! Failed to connect to endpoint: {}\n".format(endpoint))

            print("Elapsed: {}".format(test_time))
            f.write("\n\n\n".format(endpoint))
            time.sleep(collect_interval)
            test_time += collect_interval
