import logging
import os
import json

def log_r(request):
    logging.info("{0} {1} {2}".format(
            request.request.method,
            request.request.url,
            request.status_code
        )
    )
    logging.debug("{0} {1}\nHEADERS = {2}\nBODY = {3}".format(
            request.request.method,
            request.request.url,
            request.request.headers,
            request.request.body,
        )
    )
    logging.debug("{}".format(request.text))

def version_and_build(full_version):
    version_parts = full_version.split("-")
    assert (len(version_parts) == 2)
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
