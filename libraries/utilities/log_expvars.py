import time
import datetime
import requests
import json
import os
import sys
from keywords.utils import log_info
from libraries.testkit import settings

from collections import OrderedDict

from requests.exceptions import RequestException

from provisioning_config_parser import hosts_for_tag


def dump_results(test_folder, gateload_results, sync_gateway_results):
    filename = "testsuites/syncgateway/performance/results/{}/gateload_expvars.json".format(test_folder)
    log_info("Writing gateload_expvars to: {}".format(filename))
    with open(filename, "w") as f:
        f.write(json.dumps(gateload_results))

    filename = "testsuites/syncgateway/performance/results/{}/sync_gateway_expvars.json".format(test_folder)
    log_info("Writing sync_gateway_expvars to: {}".format(filename))
    with open(filename, "w") as f:
        f.write(json.dumps(sync_gateway_results))


def write_expvars(results_obj, endpoint):

        resp = requests.get("http://{}".format(endpoint), timeout=settings.HTTP_REQ_TIMEOUT)
        resp.raise_for_status()
        expvars = resp.json()

        now = "{}".format(datetime.datetime.utcnow())
        results_obj[now] = {
            "endpoint": endpoint,
            "expvars": expvars
        }


def log_expvars(cluster_config, folder_name, sleep_time=30):
    """
    usage: log_expvars.py"
    """

    finished_successfully = True

    try:

        # Get gateload ips from ansible inventory
        lgs_host_vars = hosts_for_tag(cluster_config, "load_generators")
        lgs = [lg["ansible_host"] for lg in lgs_host_vars]
        lgs_expvar_endpoints = [lg + ":9876/debug/vars" for lg in lgs]
        log_info("Monitoring gateloads until they finish: {}".format("\n".join(lgs_expvar_endpoints)))

        # Get sync_gateway ips from ansible inventory
        sgs_host_vars = hosts_for_tag(cluster_config, "sync_gateways")
        sgs = [sgv["ansible_host"] for sgv in sgs_host_vars]
        sgs_expvar_endpoints = [sg + ":4985/_expvar" for sg in sgs]
        log_info("Monitoring sync_gateways: {}".format("\n".join(sgs_expvar_endpoints)))

        # Verify that sync gateway expvar endpoints are reachable
        wait_for_endpoints_alive_or_raise(sgs_expvar_endpoints)

        # Wait until the gateload expvar endpoints are up, or raise an exception and abort
        wait_for_endpoints_alive_or_raise(lgs_expvar_endpoints)

        start_time = time.time()
        gateload_results = OrderedDict()
        sync_gateway_results = OrderedDict()

        gateload_is_running = True
        sg_is_running = True
        while gateload_is_running and sg_is_running:

            # Caputure expvars for gateloads
            for endpoint in lgs_expvar_endpoints:
                try:
                    log_info("Collecting gateload expavars {}".format(endpoint))
                    write_expvars(gateload_results, endpoint)
                    dump_results(folder_name, gateload_results, sync_gateway_results)
                except RequestException as re:
                    # connection to gateload expvars has been closed
                    log_info(re)
                    log_info("Error: {}.  Gateload {} no longer reachable. Writing expvars to {}".format(re, endpoint, folder_name))
                    dump_results(folder_name, gateload_results, sync_gateway_results)
                    gateload_is_running = False

            # Capture expvars for sync_gateways
            for endpoint in sgs_expvar_endpoints:
                try:
                    log_info("Collecting sg expavars {}".format(endpoint))
                    write_expvars(sync_gateway_results, endpoint)
                    dump_results(folder_name, gateload_results, sync_gateway_results)
                except RequestException as re:
                    # Should not happen unless sg crashes
                    finished_successfully = False
                    log_info(re)
                    log_info("ERROR {}: sync_gateway not reachable. Dumping results to {}".format(re, folder_name))
                    dump_results(folder_name, gateload_results, sync_gateway_results)
                    sg_is_running = False

            log_info("Elapsed: {} minutes".format((time.time() - start_time) / 60.0))
            time.sleep(sleep_time)

    except RuntimeError as e:
        log_info("Exception trying to log expvars: {}".format(e))
        finished_successfully = False

    return finished_successfully


def wait_for_endpoints_alive_or_raise(endpoints, num_attempts=5):

    """
    Wait for the given endpoints to be up or throw an exception
    """
    for i in xrange(num_attempts):
        endpoints_are_up = True
        for endpoint in endpoints:
            endpoint_url = endpoint
            if not endpoint_url.startswith("http"):
                endpoint_url = "http://{}".format(endpoint_url)

            try:
                log_info("Checking if endpoint is up: {}".format(endpoint_url))
                resp = requests.get(endpoint_url, timeout=settings.HTTP_REQ_TIMEOUT)
                resp.raise_for_status()
                log_info("Endpoint is up")
            except Exception as e:
                endpoints_are_up = False
                log_info("Endpoint not up. Got exception: {}".format(e))
                pass

        if endpoints_are_up:
            return

        time.sleep(i * 2)

    raise RuntimeError("Give up waiting for endpoints after {} attempts".format(num_attempts))

if __name__ == "__main__":

    try:
        main_cluster_config = os.environ["CLUSTER_CONFIG"]
    except KeyError:
        print ("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        sys.exit(1)

    log_expvars(main_cluster_config, ".", sleep_time=5)
