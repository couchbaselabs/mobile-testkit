import pytest
import time
import concurrent.futures

import subprocess
import json
import os

import lib.settings
from lib.data import Data
from lib.admin import Admin

import logging
log = logging.getLogger(lib.settings.LOGGER)


@pytest.mark.sanity
@pytest.mark.parametrize(
    "conf,num_docs",
    [
        ("sync_gateway_default_cc.json", 300),
        ("sync_gateway_default.json", 300)
    ],
    ids=["CC-1", "DI-2"]
)
def test_bulk_get_compression(cluster, conf, num_docs):

    log.info("Using conf: {}".format(conf))
    log.info("Using num_docs: {}".format(num_docs))

    cluster.reset(conf)
    admin = Admin(cluster.sync_gateways[2])

    user = admin.register_user(cluster.sync_gateways[0], "db", "seth", "password", channels=["seth"])

    doc_body = Data.load("mock_users_20k.json")

    with concurrent.futures.ThreadPoolExecutor(max_workers=lib.settings.MAX_REQUEST_WORKERS) as executor:
        futures = [executor.submit(user.add_doc, doc_id="test-{}".format(i), content=doc_body) for i in range(num_docs)]
        for future in concurrent.futures.as_completed(futures):
            try:
                log.info(future.result())
            except Exception as e:
                log.error("Failed to push doc: {}".format(e))

    docs = [{"id": "test-{}".format(i)} for i in range(num_docs)]
    payload = {"docs": docs}

    # Curl with no compression
    headers = '-H "Authorization: Basic c2V0aDpwYXNzd29yZA==" -H "Content-Type: application/json"'
    bulk_get_curl_command = 'curl -X "POST" {0}/db/_bulk_get {1} -d $\'{2}\''.format(
        cluster.sync_gateways[0].url,
        headers,
        json.dumps(payload)
    )

    with open("no_compression_response", "w") as f:
        subprocess.call(bulk_get_curl_command, shell=True, stdout=f)

    # Curl with "Accept-Encoding: gzip"
    headers = '-H "Accept-Encoding: gzip" -H "Authorization: Basic c2V0aDpwYXNzd29yZA==" -H "Content-Type: application/json"'
    bulk_get_curl_command = 'curl -X "POST" {0}/db/_bulk_get {1} -d $\'{2}\''.format(
        cluster.sync_gateways[0].url,
        headers,
        json.dumps(payload)
    )

    with open("Accept-Encoding-gzip_response", "w") as f:
        subprocess.call(bulk_get_curl_command, shell=True, stdout=f)

    # Curl with "X-Accept-Part-Encoding: gzip"
    headers = '-H "X-Accept-Part-Encoding: gzip" -H "Authorization: Basic c2V0aDpwYXNzd29yZA==" -H "Content-Type: application/json"'
    bulk_get_curl_command = 'curl -X "POST" {0}/db/_bulk_get {1} -d $\'{2}\''.format(
        cluster.sync_gateways[0].url,
        headers,
        json.dumps(payload)
    )

    with open("X-Accept-Encoding-gzip_response", "w") as f:
        subprocess.call(bulk_get_curl_command, shell=True, stdout=f)

    no_compression_response_size = os.path.getsize("no_compression_response")
    accept_encoding_response_size = os.path.getsize("Accept-Encoding-gzip_response")
    x_accept_part_encoding_response_size = os.path.getsize("X-Accept-Encoding-gzip_response")

    # delete reponses
    os.remove("no_compression_response")
    os.remove("Accept-Encoding-gzip_response")
    os.remove("X-Accept-Encoding-gzip_response")

    log.info("no_compression_response size {}".format(no_compression_response_size))
    log.info("'Accept-Encoding: gzip' response size {}".format(accept_encoding_response_size))
    log.info("'X-Accept-Part-Encoding: gzip' response size {}".format(x_accept_part_encoding_response_size))

    # Verify response sizes
    assert(6320000 < no_compression_response_size < 6321000)
    assert(2244000 < x_accept_part_encoding_response_size < 2245000)
    assert(75000 < accept_encoding_response_size < 76000)




