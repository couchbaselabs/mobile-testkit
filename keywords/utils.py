import logging
import json
import os
import random
import string
import re

from keywords.exceptions import FeatureSupportedError
from keywords.constants import DATA_DIR
from utilities.cluster_config_utils import get_cbs_servers, get_sg_version


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

    try:
        logging.debug("{}".format(request.text.encode("utf-8")))
    except Exception, err:
        log_debug("Error occurred: {}".format(err))


def version_is_binary(version):
    if len(version.split(".")) > 1:
        # ex 1.2.1 or 1.2.1-4
        return True
    else:
        return False


def version_and_build(full_version):
    version_parts = full_version.split("-")
    if len(version_parts) == 2:
        return version_parts[0], version_parts[1]
    else:
        return version_parts[0], None


def host_for_url(url):
    """ Takes a url in the form of http://192.168.33.10:4985
    and returns an host in the form 192.168.33.10
    """

    if "https" in url:
        host = url.replace("https://", "")
    else:
        host = url.replace("http://", "")

    host = host.rsplit(":", 1)[0]
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
    url = url.replace("https://", "")
    url = url.replace(":4984", "")
    url = url.replace(":4985", "")
    url = url.replace(":8091", "")
    url = url.replace("[", "")
    url = url.replace("]", "")

    endpoints = cluster["sg_accels"]
    endpoints.extend(cluster["sync_gateways"])
    endpoints.extend(cluster["couchbase_servers"])
    endpoints.extend(cluster["load_balancers"])

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


def add_cbs_to_sg_config_server_field(cluster_config):
    """ This method get all CBS servers ips from cluster config and
       it as server in sync gateway config file . Each ip is seperated
       by comma
       Format of server file in sync-gateway config if there are 3 couchbase servers
       server: "http://xxx.xxx.xx.xx,xx1.xx1.x1.x1,xx2,xx2,x2,x2:8091 """
    couchbase_server_primary_node = ""
    sg_version = get_sg_version(cluster_config)
    cbs_servers = get_cbs_servers(cluster_config)
    if compare_versions(sg_version, '1.5') < 0:
        couchbase_server_primary_node = cbs_servers[0]
    else:
        for i in range(len(cbs_servers)):
            couchbase_server_primary_node = couchbase_server_primary_node + cbs_servers[i]
            if (i + 1) < len(cbs_servers):
                couchbase_server_primary_node = couchbase_server_primary_node + ","

    return couchbase_server_primary_node


def random_string(length, printable=False, digit=False):
    if digit:
        return ''.join(random.choice(string.digits) for _ in range(length))
    if printable:
        return ''.join(random.choice(string.printable) for _ in range(length))
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))


def clear_resources_pngs():
    log_info("Clearing png files in {}".format(DATA_DIR))
    for the_file in os.listdir(DATA_DIR):
        file_path = os.path.join(DATA_DIR, the_file)

        try:
            if os.path.isfile(file_path) and file_path.endswith(".png"):
                os.unlink(file_path)
        except Exception as e:
            print(e)


def get_event_changes(event_changes):
    """
    @summary:
    A method to filter out the events.
    @return:
    a dict containing doc_id as key and error status and replication as value,
    for a particular Replication event
    """
    event_dict = {}
    pattern = ".*?doc_id: ([a-zA-Z0-9_]+), error_code: (.*?), error_domain: ([a-zA-Z0-9_]+)," \
              " push: ([a-zA-Z0-9_]+), flags: (.*?)'.*?"
    events = re.findall(pattern, string=str(event_changes))
    for event in events:
        doc_id = event[0].strip()
        error_code = event[1].strip()
        error_domain = event[2].strip()
        is_push = True if ("true" in event[3] or "True" in event[3]) else False
        flags = event[4] if event[4] != '[]' else None
        if error_code == '0' or error_code == 'nil':
            error_code = None
        if error_domain == '0' or error_domain == 'nil':
            error_domain = None
        event_dict[doc_id] = {"push": is_push,
                              "error_code": error_code,
                              "error_domain": error_domain,
                              "flags": flags}
    return event_dict


def add_new_fields_to_doc(doc_body):
    doc_body["new_field_1"] = random.choice([True, False])
    doc_body["new_field_2"] = random_string(length=60)
    doc_body["new_field_3"] = random_string(length=90)
    return doc_body


def compare_docs(cbl_db, db, docs_dict):
    doc_ids = db.getDocIds(cbl_db)
    cbl_db_docs = db.getDocuments(cbl_db, doc_ids)
    for doc in docs_dict:
        try:
            del doc["doc"]["_rev"]
        except KeyError:
            log_info("no _rev exists in the dict")
        key = doc["doc"]["_id"]
        del doc["doc"]["_id"]
        try:
            del cbl_db_docs[key]["_id"]
        except KeyError:
            log_info("Ignoring id verification")
        assert deep_dict_compare(doc["doc"], cbl_db_docs[key]), "mismatch in the dictionary"


def compare_generic_types(object1, object2, isPredictiveResult=False):
    """
    @summary:
    A method to compare generic type of objects with an option of making approximate comparison.
    If isPredictiveResult flag is enabled, some large numbers are considered equal if the difference is tolerable.
    @return:
    true if equals, false otherwise
    """
    if object1 is None and object2 is None:
        return True
    if isinstance(object1, str) and isinstance(object2, str):
        return object1 == object2
    elif isinstance(object1, unicode) and isinstance(object2, unicode):
        return object1 == object2
    elif isinstance(object1, bool) and isinstance(object2, bool):
        return object1 == object2
    elif isinstance(object1, int) and isinstance(object2, int):
        return object1 == object2
    elif isinstance(object1, long) and isinstance(object2, long):
        return object1 == object2
    elif isinstance(object1, float) and isinstance(object2, float):
        return object1 == object2
    elif isinstance(object1, float) and isinstance(object2, int):
        if isPredictiveResult:
            return abs(object1 - object2) < 100
        else:
            return object1 == float(object2)
    elif isinstance(object1, int) and isinstance(object2, float):
        return object1 == int(float(object2))
    elif isinstance(object1, long) and isinstance(object2, int):
        return object1 == long(object2)
    elif isinstance(object1, int) and isinstance(object2, long):
        return object1 == int(object2)
    elif isinstance(object1, float) and isinstance(object2, long):
        if isPredictiveResult:
            return abs(object1 - object2) < 100
        else:
            return object1 == float(object2)
    elif isinstance(object1, long) and isinstance(object2, float):
        return object1 == long(float(object2))
    elif isinstance(object1, str) and isinstance(object2, unicode):
        return object1 == str(object2)
    elif isinstance(object1, unicode) and isinstance(object2, str):
        return str(object1) == object2
    return False


def deep_list_compare(object1, object2, isPredictiveResult=False):
    """
    @summary:
    A method to compare two lists with an option of forwarding
    an approximate comparison flag to compare_generic_types function
    @return:
    true if equals, false otherwise
    """
    retval = True
    count = len(object1)
    object1 = sorted(object1)
    object2 = sorted(object2)
    for x in range(count):
        if isinstance(object1[x], dict) and isinstance(object2[x], dict):
            retval = deep_dict_compare(object1[x], object2[x], isPredictiveResult)
            if retval is False:
                log_info("Unable to match element in dict {} and {}".format(object1, object2))
                return False
        elif isinstance(object1[x], list) and isinstance(object2[x], list):
            retval = deep_list_compare(object1[x], object2[x], isPredictiveResult)
            if retval is False:
                log_info("Unable to match element in list {} and {}".format(object1[x], object2[x]))
                return False
        else:
            retval = compare_generic_types(object1[x], object2[x], isPredictiveResult)
            if retval is False:
                log_info("Unable to match objects in generic {} and {}".format(object1[x], object2[x]))
                return False

    return retval


def deep_dict_compare(object1, object2, isPredictiveResult=False):
    """
    @summary:
    A method to compare two dictionaries with an option of forwarding
    an approximate comparison flag to compare_generic_types function.
    @return:
    true if equals, false otherwise
    """
    retval = True
    if len(object1) != len(object2):
        log_info("lengths of sgw object and cbl object are different {} --- {}".format(len(object1), len(object2)))
        log_info("keys of object 1 and object2 {}\n---{}".format(object1.keys(), object2.keys()))
        return False

    for k in object1.iterkeys():
        obj1 = object1[k]
        obj2 = object2[k]
        if isinstance(obj1, list) and isinstance(obj2, list):
            retval = deep_list_compare(obj1, obj2, isPredictiveResult)
            if retval is False:
                log_info("mismatch between sgw: {} and cbl lists :{}".format(obj1, obj2))
                return False

        elif isinstance(obj1, dict) and isinstance(obj2, dict):
            retval = deep_dict_compare(obj1, obj2, isPredictiveResult)
            if retval is False:
                log_info("mismatch between sgw: {} and cbl dict :{}".format(obj1, obj2))
                return False
        else:
            retval = compare_generic_types(obj1, obj2, isPredictiveResult)
            if retval is False:
                log_info("mismatch {} and {}".format(obj1, obj2))
                return False

    return retval


def meet_supported_version(version_list, target_version):
    for ver in version_list:
        if ver < target_version:
            return False

    return True
