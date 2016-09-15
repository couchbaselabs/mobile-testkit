import concurrent.futures

import subprocess
import json
import os

import testkit.settings
from testkit.cluster import Cluster
from testkit.data import Data
from testkit.admin import Admin

import logging
log = logging.getLogger(testkit.settings.LOGGER)

uncompressed_size = 6320500
part_encoded_size = 2244500
whole_response_compressed_size = 75500


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

    log.info("Request: {}".format(bulk_get_curl_command))

    with open("response", "w") as f:
        subprocess.call(bulk_get_curl_command, shell=True, stdout=f)

    # Get size of response and delete from disc
    response_size = os.path.getsize("response")
    os.remove("response")

    return response_size


def verify_response_size(user_agent, accept_encoding, x_accept_part_encoding, response_size):

    if user_agent is None or user_agent == "CouchbaseLite/1.1":

        if accept_encoding is None and x_accept_part_encoding is None:
            # Response size should not be compressed
            assert (uncompressed_size - 500) < response_size < (uncompressed_size + 500)
        elif accept_encoding == "gzip" and x_accept_part_encoding is None:
            # Response size should not be compressed
            assert (uncompressed_size - 500) < response_size < (uncompressed_size + 500)
        elif accept_encoding is None and x_accept_part_encoding == "gzip":
            # Response size should be part compressed
            assert (part_encoded_size - 500) < response_size < (part_encoded_size + 500)
        elif accept_encoding == "gzip" and x_accept_part_encoding == "gzip":
            # Response size should be part compressed
            assert (part_encoded_size - 500) < response_size < (part_encoded_size + 500)

    elif user_agent == "CouchbaseLite/1.2":

        if accept_encoding is None and x_accept_part_encoding is None:
            # Response size should not be compressed
            assert (uncompressed_size - 500) < response_size < (uncompressed_size + 500)
        elif accept_encoding == "gzip" and x_accept_part_encoding is None:
            # Response size should be fully compressed
            assert (whole_response_compressed_size - 500) < response_size < (whole_response_compressed_size + 500)
        elif accept_encoding is None and x_accept_part_encoding == "gzip":
            # Response size should be part compressed
            assert (part_encoded_size - 500) < response_size < (part_encoded_size + 500)
        elif accept_encoding == "gzip" and x_accept_part_encoding == "gzip":
            # Response size should be fully compressed
            assert (whole_response_compressed_size - 500) < response_size < (whole_response_compressed_size + 500)

    else:
        raise ValueError("Unsupported user agent")


def test_bulk_get_compression(conf, num_docs, accept_encoding=None, x_accept_part_encoding=None, user_agent=None):

    log.info("Using conf: {}".format(conf))
    log.info("Using num_docs: {}".format(num_docs))
    log.info("Using user_agent: {}".format(user_agent))
    log.info("Using accept_encoding: {}".format(accept_encoding))
    log.info("Using x_accept_part_encoding: {}".format(x_accept_part_encoding))

    cluster = Cluster()
    mode = cluster.reset(config_path=conf)
    admin = Admin(cluster.sync_gateways[0])

    user = admin.register_user(cluster.sync_gateways[0], "db", "seth", "password", channels=["seth"])

    doc_body = Data.load("mock_users_20k.json")

    with concurrent.futures.ThreadPoolExecutor(max_workers=testkit.settings.MAX_REQUEST_WORKERS) as executor:
        futures = [executor.submit(user.add_doc, doc_id="test-{}".format(i), content=doc_body) for i in range(num_docs)]
        for future in concurrent.futures.as_completed(futures):
            try:
                log.info(future.result())
            except Exception as e:
                log.error("Failed to push doc: {}".format(e))

    docs = [{"id": "test-{}".format(i)} for i in range(num_docs)]
    payload = {"docs": docs}

    # Issue curl request and get size of request
    response_size = issue_request(cluster.sync_gateways[0], user_agent, accept_encoding, x_accept_part_encoding, payload)
    log.info("Response size: {}".format(response_size))

    # Verfiy size matches expected size
    verify_response_size(user_agent, accept_encoding, x_accept_part_encoding, response_size)

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert len(errors) == 0





