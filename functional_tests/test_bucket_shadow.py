import time

import pytest


from lib.admin import Admin
from lib.verify import verify_changes

from fixtures import cluster

## 1. Do cluster reset with config that specifies shadow buckets
## 2. Presumably add some docs via SG Rest API?
## 3. (check order) Shut down sync gateway
## 4. Delete document from "source bucket" directly in couchbase server
## 5. Restart sync gw
## 6. Do some verification

def test_bucket_shadow(cluster):

    config_path = "sync_gateway_bucketshadow_cc.json"
    
    mode = cluster.reset(config_path=config_path)

    config = cluster.sync_gateway_config
    
    if len(config.get_bucket_name_set()) != 2:
        raise Exception("Expected to find two buckets, only found {}".format(len(config.bucket_name_set())))
    
    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)
    
    # Get a connection to the bucket
    bucket = cluster.servers[0].get_bucket("source-bucket")
    
    # Add doc directly to source bucket
    doc = {}
    doc_id = "{}".format(time.time())
    doc["foo"] = "bar"
    bucket.add(doc_id, doc)

    # Delete doc from source bucket
    bucket.remove(doc_id)

    # Restart Sync gateway
    cluster.sync_gateways[0].restart(config_path)

    # Verify all Sync Gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)

    

