import concurrent.futures
import pytest
import subprocess
import json
import os

import libraries.testkit.settings
from libraries.testkit.cluster import Cluster
from libraries.testkit.data import Data
from libraries.testkit.admin import Admin

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.utils import log_info
from keywords.Logging import Logging


uncompressed_size = 6320500
uncompressed_lower_limit = uncompressed_size - (uncompressed_size / 10)
uncompressed_upper_limit = uncompressed_size + (uncompressed_size / 10)

part_encoded_size = 2244500
part_encoded_lower_limit = part_encoded_size - (part_encoded_size / 10)
part_encoded_upper_limit = part_encoded_size + (part_encoded_size / 10)

whole_response_compressed_size = 75500
whole_response_compressed_lower_limit = whole_response_compressed_size - (whole_response_compressed_size / 10)
whole_response_compressed_upper_limit = whole_response_compressed_size + (whole_response_compressed_size / 10)


# This is called before each test and will yield the cluster_config to each test in the file
# After each test_* function, execution will continue from the yield a pull logs on failure
@pytest.fixture(scope="function")
def setup_1sg_1cbs_test(request):

    test_name = request.node.name
    log_info("Setting up test '{}'".format(test_name))

    yield {"cluster_config": os.environ["CLUSTER_CONFIG"]}

    log_info("Tearing down test '{}'".format(test_name))

    # if the test failed pull logs
    if request.node.rep_call.failed:
        logging_helper = Logging()
        logging_helper.fetch_and_analyze_logs(cluster_config=os.environ["CLUSTER_CONFIG"], test_name=test_name)


def issue_request(target, user_agent, accept_encoding, x_accept_part_encoding, payload):

    # Set proper headers
    if user_agent is None:
        if accept_encoding is None and x_accept_part_encoding is None:
            headers = '-H "Authorization: Basic c2V0aDpwYXNzd29yZA==" -H "Content-Type: application/json"'
        elif accept_encoding == "gzip" and x_accept_part_encoding is None:
            headers = '-H "Accept-Encoding: gzip" -H "Authorization: Basic c2V0aDpwYXNzd29yZA==" -H "Content-Type: application/json"'
        elif accept_encoding is None and x_accept_part_encoding == "gzip":
            headers = '-H "X-Accept-Part-Encoding: gzip" -H "Authorization: Basic c2V0aDpwYXNzd29yZA==" -H "Content-Type: application/json"'
        elif accept_encoding == "gzip" and x_accept_part_encoding == "gzip":
            headers = '-H "Accept-Encoding: gzip" -H "X-Accept-Part-Encoding: gzip" -H "Authorization: Basic c2V0aDpwYXNzd29yZA==" -H "Content-Type: application/json"'
    else:
        if accept_encoding is None and x_accept_part_encoding is None:
            headers = '-A {} -H "Authorization: Basic c2V0aDpwYXNzd29yZA==" -H "Content-Type: application/json"'.format(user_agent)
        elif accept_encoding == "gzip" and x_accept_part_encoding is None:
            headers = '-A {} -H "Accept-Encoding: gzip" -H "Authorization: Basic c2V0aDpwYXNzd29yZA==" -H "Content-Type: application/json"'.format(user_agent)
        elif accept_encoding is None and x_accept_part_encoding == "gzip":
            headers = '-A {} -H "X-Accept-Part-Encoding: gzip" -H "Authorization: Basic c2V0aDpwYXNzd29yZA==" -H "Content-Type: application/json"'.format(user_agent)
        elif accept_encoding == "gzip" and x_accept_part_encoding == "gzip":
            headers = '-A {} -H "Accept-Encoding: gzip" -H "X-Accept-Part-Encoding: gzip" -H "Authorization: Basic c2V0aDpwYXNzd29yZA==" -H "Content-Type: application/json"'.format(user_agent)

    # Issue curl and write response to disc
    bulk_get_curl_command = 'curl -X "POST" {0}/db/_bulk_get {1} -d $\'{2}\''.format(
        target.url,
        headers,
        json.dumps(payload)
    )

    log_info("Request: {}".format(bulk_get_curl_command))

    with open("response", "w") as f:
        subprocess.call(bulk_get_curl_command, shell=True, stdout=f)

    # Get size of response and delete from disc
    response_size = os.path.getsize("response")
    os.remove("response")

    return response_size


def verify_response_size(user_agent, accept_encoding, x_accept_part_encoding, response_size):

    log_info("user_agent: {}, accept_encoding: {}, x_accept_part_encoding: {}, response_size: {}".format(user_agent,
                                                                                                         accept_encoding,
                                                                                                         x_accept_part_encoding,
                                                                                                         response_size))

    if user_agent is None or user_agent == "CouchbaseLite/1.1":

        if accept_encoding is None and x_accept_part_encoding is None:

            # Response size should not be compressed
            log_info("{} < {} < {}".format(uncompressed_lower_limit, response_size, uncompressed_upper_limit))
            assert uncompressed_lower_limit < response_size < uncompressed_upper_limit

        elif accept_encoding == "gzip" and x_accept_part_encoding is None:

            # Response size should not be compressed
            log_info("{} < {} < {}".format(uncompressed_lower_limit, response_size, uncompressed_upper_limit))
            assert uncompressed_lower_limit < response_size < uncompressed_upper_limit

        elif accept_encoding is None and x_accept_part_encoding == "gzip":

            # Response size should be part compressed
            log_info("{} < {} < {}".format(part_encoded_lower_limit, response_size, part_encoded_upper_limit))
            assert part_encoded_lower_limit < response_size < part_encoded_upper_limit

        elif accept_encoding == "gzip" and x_accept_part_encoding == "gzip":

            # Response size should be part compressed
            log_info("{} < {} < {}".format(part_encoded_lower_limit, response_size, part_encoded_upper_limit))
            assert part_encoded_lower_limit < response_size < part_encoded_upper_limit

    elif user_agent == "CouchbaseLite/1.2":

        if accept_encoding is None and x_accept_part_encoding is None:

            # Response size should not be compressed
            log_info("{} < {} < {}".format(uncompressed_lower_limit, response_size, uncompressed_upper_limit))
            assert uncompressed_lower_limit < response_size < uncompressed_upper_limit

        elif accept_encoding == "gzip" and x_accept_part_encoding is None:

            # Response size should be fully compressed
            log_info("{} < {} < {}".format(whole_response_compressed_lower_limit, response_size, whole_response_compressed_upper_limit))
            assert whole_response_compressed_lower_limit < response_size < whole_response_compressed_upper_limit

        elif accept_encoding is None and x_accept_part_encoding == "gzip":

            # Response size should be part compressed
            log_info("{} < {} < {}".format(part_encoded_lower_limit, response_size, part_encoded_upper_limit))
            assert part_encoded_lower_limit < response_size < part_encoded_upper_limit

        elif accept_encoding == "gzip" and x_accept_part_encoding == "gzip":

            # Response size should be fully compressed
            log_info("{} < {} < {}".format(whole_response_compressed_lower_limit, response_size, whole_response_compressed_upper_limit))
            assert whole_response_compressed_lower_limit < response_size < whole_response_compressed_upper_limit

    else:
        raise ValueError("Unsupported user agent")


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.parametrize("sg_conf_name, num_docs, accept_encoding, x_accept_part_encoding, user_agent", [
    ("sync_gateway_gzip", 300, None, None, None),
    ("sync_gateway_gzip", 300, None, None, "CouchbaseLite/1.1"),
    ("sync_gateway_gzip", 300, "gzip", None, None),
    ("sync_gateway_gzip", 300, "gzip", None, "CouchbaseLite/1.1"),
    ("sync_gateway_gzip", 300, None, "gzip", None),
    ("sync_gateway_gzip", 300, None, "gzip", "CouchbaseLite/1.1"),
    ("sync_gateway_gzip", 300, "gzip", "gzip", None),
    ("sync_gateway_gzip", 300, "gzip", "gzip", "CouchbaseLite/1.1"),
    ("sync_gateway_gzip", 300, None, None, "CouchbaseLite/1.2"),
    ("sync_gateway_gzip", 300, "gzip", None, "CouchbaseLite/1.2"),
    ("sync_gateway_gzip", 300, None, "gzip", "CouchbaseLite/1.2"),
    ("sync_gateway_gzip", 300, "gzip", "gzip", "CouchbaseLite/1.2")
])
def test_bulk_get_compression(params_from_base_test_setup, sg_conf_name, num_docs, accept_encoding, x_accept_part_encoding, user_agent):

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'test_bulk_get_compression'")
    log_info("Using cluster_config: {}".format(cluster_config))
    log_info("Using sg_conf: {}".format(sg_conf))
    log_info("Using num_docs: {}".format(num_docs))
    log_info("Using user_agent: {}".format(user_agent))
    log_info("Using accept_encoding: {}".format(accept_encoding))
    log_info("Using x_accept_part_encoding: {}".format(x_accept_part_encoding))

    cluster = Cluster(config=cluster_config)
    mode = cluster.reset(sg_config_path=sg_conf)
    admin = Admin(cluster.sync_gateways[0])

    user = admin.register_user(cluster.sync_gateways[0], "db", "seth", "password", channels=["seth"])

    doc_body = Data.load("mock_users_20k.json")

    with concurrent.futures.ThreadPoolExecutor(max_workers=libraries.testkit.settings.MAX_REQUEST_WORKERS) as executor:
        futures = [executor.submit(user.add_doc, doc_id="test-{}".format(i), content=doc_body) for i in range(num_docs)]
        for future in concurrent.futures.as_completed(futures):
            try:
                log_info(future.result())
            except Exception as e:
                log_info("Failed to push doc: {}".format(e))

    docs = [{"id": "test-{}".format(i)} for i in range(num_docs)]
    payload = {"docs": docs}

    # Issue curl request and get size of request
    response_size = issue_request(cluster.sync_gateways[0], user_agent, accept_encoding, x_accept_part_encoding, payload)
    log_info("Response size: {}".format(response_size))

    # Verfiy size matches expected size
    verify_response_size(user_agent, accept_encoding, x_accept_part_encoding, response_size)
