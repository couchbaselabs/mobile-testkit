import logging
import json
import nmap

# TODO: Use python logging hooks instead of wrappers - https://github.com/couchbaselabs/mobile-testkit/issues/686
def log_info(message, is_verify=False):
    # pytest will capture stdout / stderr
    # by using 'print' the html reporting and running the test with -s will pick up this output in the console
    # If verify is true, the message will have the format "  > This is some message" for cleaner output

    if is_verify:
        message = "  > {}".format(message)

    print(message)
    logging.info(message)


def log_section():
    output = "----------------"
    print(output)
    logging.info(output)


def log_debug(message):
    """Wrapper around logging.debug if we want to add hooks in the future."""
    logging.debug(message)


def log_error(message):
    """Wrapper around logging.error if we want to add hooks in the future."""
    print(message)
    logging.error(message)


def log_warn(message):
    """Wrapper around logging.warn if we want to add hooks in the future."""
    print(message)
    logging.warn(message)


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
        request.request.body))

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


def host_for_url(url):
    """ Takes a url in the form of http://192.168.33.10:4985
    and returns an host in the form 192.168.33.10
    """

    host = url.replace("http://", "")
    host = host.split(":")[0]
    log_info("Extracted host () from url ()".format(host, url))

    return host


# Targeted playbooks need to use the host_name (i.e. sg1)
def hostname_for_url(cluster_config, url):
    cluster_config = "{}.json".format(cluster_config)
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

def detect_remote_windows_os(ip_address):
    nm = nmap.PortScanner()
    # nm.scan(ip_address, arguments='-O') can do OS fingerprinting
    # but needs root privileges, so we'll do a ping scan instead
    # and look for "Microsoft Windows" in the port's output
    # Sample port output - 445: {'product': 'Microsoft Windows 7 - 10 microsoft-ds',
    # 'state': 'open', 'version': '', 'name': 'microsoft-ds', 'conf': '10',
    # 'extrainfo': 'workgroup: WORKGROUP', 'reason': 'syn-ack',
    # 'cpe': 'cpe:/o:microsoft:windows'}
    output = nm.scan(ip_address)

    for i in output['scan'][ip_address]['tcp']:
        if "Microsoft Windows" in output['scan']['10.17.1.168']['tcp'][i]['product']:
            return True
