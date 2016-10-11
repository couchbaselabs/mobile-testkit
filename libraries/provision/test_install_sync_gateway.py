import unittest
import os
from libraries.provision.install_sync_gateway import get_buckets_from_sync_gateway_config


# TODO: convert to pytest (but pytest can use unittest format as well)
class TestInstallSyncGateway(unittest.TestCase):

    def test_get_buckets_from_sync_gateway_config_template_vars(self):

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
        self.assertEquals(len(buckets), numBucketsExpected, msg="Expected {} buckets".format(numBucketsExpected))

        # clean up temp file
        os.remove(tmpConfigFileName)

    def test_get_buckets_from_sync_gateway_config_no_buckets(self):

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
        self.assertEquals(len(buckets), numBucketsExpected, msg="Expected {} buckets".format(numBucketsExpected))

        # clean up temp file
        os.remove(tmpConfigFileName)
