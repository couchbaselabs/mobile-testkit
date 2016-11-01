import os
import pytest

from libraries.provision.install_sync_gateway import get_buckets_from_sync_gateway_config

from keywords.SyncGateway import validate_sync_gateway_mode


def test_verify_mode_correct():
    validate_sync_gateway_mode("cc")
    validate_sync_gateway_mode("di")


def test_verify_mode_none_or_invalid():

    expected_error_message = "Sync Gateway mode must be 'cc' (channel cache) or 'di' (distributed index)"

    with pytest.raises(ValueError) as ve:
        validate_sync_gateway_mode(None)
    ve_message = str(ve.value)
    assert ve_message == expected_error_message

    with pytest.raises(ValueError) as ve:
        validate_sync_gateway_mode("ccc")
    ve_message = str(ve.value)
    assert ve_message == expected_error_message


def test_get_buckets_from_sync_gateway_config_template_vars():

    configJson = """
        {
    "interface":":4984",
    "adminInterface": "0.0.0.0:4985",
    "maxIncomingConnections": 0,
    "maxCouchbaseConnections": 16,
    "maxFileDescriptors": 90000,
    "slowServerCallWarningThreshold": 500,
    "compressResponses": true,
    "log": ["CRUD+", "Cache+", "HTTP+", "Changes+"],
    "cluster_config": {
        "server":"http://{{ couchbase_server_primary_node }}:8091",
        "data_dir":".",
        "bucket":"data-bucket"
    },
    "databases":{
        "db":{
            "feed_type":"DCPSHARD",
            "feed_params":{
                "num_shards":64
            },
            "server":"http://{{ couchbase_server_primary_node }}:8091",
            "bucket":"data-bucket",
            "users":{
                "GUEST":{
                    "disabled":true,
                    "admin_channels":[
                        "*"
                    ]
                }
            },
            "channel_index":{
                "server":"http://{{ couchbase_server_primary_node }}:8091",
                "bucket":"index-bucket",
                "writer":{{ is_index_writer }}
            }
        }
    }
}
"""

    tmpConfigFileName = "/tmp/test_get_buckets_from_sync_gateway_config_template_vars.json"
    tmpConfigFile = open(tmpConfigFileName, "w")
    tmpConfigFile.write(configJson)
    tmpConfigFile.close()

    buckets = get_buckets_from_sync_gateway_config(tmpConfigFileName)

    numBucketsExpected = 2
    assert len(buckets) == numBucketsExpected

    # clean up temp file
    os.remove(tmpConfigFileName)


def test_get_buckets_from_sync_gateway_config_no_buckets():

    configJson = """
        {
          "log":[
            "*"
          ],
          "databases":{
            "db":{
              "server":"walrus:",
              "users":{
                "GUEST":{
                  "disabled":true,
                  "admin_channels":[
                    "*"
                  ]
                },
              "foo": {
                  "disabled":false,
                  "admin_channels": [
                  "*"
                  ],
                  "password": "bar"
              }
              },
              "allow_empty_password":true
            }
          }
        }
    """

    tmpConfigFileName = "/tmp/test_get_buckets_from_sync_gateway_config_no_buckets.json"
    tmpConfigFile = open(tmpConfigFileName, "w")
    tmpConfigFile.write(configJson)
    tmpConfigFile.close()

    buckets = get_buckets_from_sync_gateway_config(tmpConfigFileName)

    numBucketsExpected = 0
    assert len(buckets) == numBucketsExpected

    # clean up temp file
    os.remove(tmpConfigFileName)
