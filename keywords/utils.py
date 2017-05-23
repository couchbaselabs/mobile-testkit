import logging
import json

from keywords.exceptions import FeatureSupportedError


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

    if "https" in url:
        host = url.replace("https://", "")
    else:
        host = url.replace("http://", "")

    host = host.split(":")[0]
    log_info("Extracted host ({}) from url ({})".format(host, url))

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


# Check if this version has net45
def has_dot_net4_dot_5(version):
    version_prefixes = [
        "1.2",
        "1.3",
        "1.4.0"  # For 1.4, the path is net45/LiteServ.exe, for 1.4.0, there is no net45
    ]

    for i in version_prefixes:
        if version.startswith(i):
            return False

    return True


def compare_versions(version_one, version_two):
    """ Checks two version and returns the following:

    Version should be of the following formats 1.4.2 or 1.4.1

    if version_one == version two, return 0
    if version_one < version_two, return -1,
    if version_one > version_two, return 1
    """

    # Strip build number if present, 1.4.1-345 -> 1.4.1
    version_one = version_one.split('-')[0]
    version_two = version_two.split('-')[0]

    # Strip '.' and convert to integers
    version_one_number_string = version_one.replace('.', '')
    version_two_number_string = version_two.replace('.', '')

    version_one_number_string_len = len(version_one_number_string)
    version_two_number_string_len = len(version_two_number_string)

    # Handle the case where 1.4 and 1.4.0 should be equal
    # by padding 0s on the right of the shorter number
    difference = abs(version_one_number_string_len - version_two_number_string_len)
    if difference != 0 and version_one_number_string_len < version_two_number_string_len:
        for _ in range(difference):
            version_one_number_string += "0"
    if difference != 0 and version_one_number_string_len > version_two_number_string_len:
        for _ in range(difference):
            version_two_number_string += "0"

    version_one_number = int(version_one_number_string)
    version_two_number = int(version_two_number_string)

    if version_one_number < version_two_number:
        return -1

    if version_one_number > version_two_number:
        return 1

    # All components are equal
    return 0


def check_xattr_support(server_version, sync_gateway_version):
    if compare_versions(server_version, '5.0.0') < 0:
        raise FeatureSupportedError('Make sure you are using Coucbhase Server 5.0+ for xattrs')
    if compare_versions(sync_gateway_version, '1.5') < 0:
        raise FeatureSupportedError('Make sure you are using Coucbhase Sync Gateway 1.5+ for xattrs')
