import logging
import os
import json
import pdb
import sys


def log_info(message, is_verify=False):
    # pytest will capture stdout / stderr
    # by using 'print' the html reporting and running the test with -s will pick up this output in the console
    # If verify is true, the message will have the format "  > This is some message" for cleaner output

    if is_verify:
        message = "  > {}".format(message)

    print(message)
    logging.info(message)


def log_r(request, info=True):
    request_summary = "{0} {1} {2}".format(
        request.request.method,
        request.request.url,
        request.status_code
    )
    if info:
        log_info(request_summary)
    logging.debug("{0} {1}\nHEADERS = {2}\nBODY = {3}".format(
            request.request.method,
            request.request.url,
            request.request.headers,
            request.request.body,
        )
    )
    logging.debug("{}".format(request.text))


def version_is_binary(version):
    if len(version.split(".")) > 1:
        # ex 1.2.1 or 1.2.1-4
        return True
    else:
        return False


def version_and_build(full_version):
    version_parts = full_version.split("-")
    assert len(version_parts) == 2
    return version_parts[0], version_parts[1]


# Targeted playbooks need to use the host_name (i.e. sg1)
def hostname_for_url(url):
    cluster_config = "{}.json".format(os.environ["CLUSTER_CONFIG"])
    with open(cluster_config) as f:
        logging.info("Using cluster config: {}".format(cluster_config))
        cluster = json.loads(f.read())

    logging.debug(cluster)

    # strip possible ports
    url = url.replace("http://", "")
    url = url.replace(":4984", "")
    url = url.replace(":4985", "")
    url = url.replace(":8091", "")

    endpoints = cluster["sg_accels"]
    endpoints.extend(cluster["sync_gateways"])
    endpoints.extend(cluster["couchbase_servers"])

    logging.debug(endpoints)

    for endpoint in endpoints:
        if endpoint["ip"] == url:
            logging.info("Name found for url: {}. Returning: {}".format(url, endpoint["name"]))
            return endpoint["name"]

    raise ValueError("Could not find name for url: {} in cluster_config: {}".format(url, cluster_config))


def dump_file_contents_to_logs(filename):
    try:
        log_info("Contents of {}: {}".format(filename, open(filename).read()))
    except Exception as e:
        log_info("Error reading {}: {}".format(filename, e))
