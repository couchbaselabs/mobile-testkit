import time

import pytest


from lib.admin import Admin
from lib.verify import verify_changes

from fixtures import cluster

def test_bucket_shadow_propagates_to_source_bucket(cluster):

    """
    Verify that a document added to sync gateway propagates to the source (shadow)
    bucket.
    """
    
    source_bucket_name = "source-bucket"
    config_path = "sync_gateway_bucketshadow_cc.json"
    
    mode = cluster.reset(config_path=config_path)
    
    config = cluster.sync_gateway_config
    
    if len(config.get_bucket_name_set()) != 2:
        raise Exception("Expected to find two buckets, only found {}".format(len(config.bucket_name_set())))
    
    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)

    admin = Admin(cluster.sync_gateways[0])

    alice = admin.register_user(
        target=cluster.sync_gateways[0],
        db="db",
        name="alice",
        password="password",
        channels=["ABC", "NBC", "CBS"],
    )

    # Add doc to sync gateway
    doc_id = alice.add_doc()
    
    # Get a connection to the bucket
    bucket = cluster.servers[0].get_bucket(source_bucket_name)

    # Get the doc from the source bucket, possibly retrying if needed
    # Otherwise an exception will be thrown and the test will fail
    doc = get_doc_from_source_bucket_retry(doc_id, bucket)
    print("Doc {} appeared in source bucket".format(doc))


def get_doc_from_source_bucket_retry(doc_id, bucket):
    """
    Get a document from the couchbase source bucket
    Will retry until it appears, or give up and raise an exception
    """
    # Wait til the docs appears in the source bucket
    doc  = None
    maxTries = 5
    i = 0
    while True:
        i += 1
        print("trying to get doc: {}".format(doc_id))
        doc = bucket.get(doc_id, quiet=True)
        print("doc.success: {}".format(doc.success))
        if doc.success:
            break
        else:
            if i > maxTries:
                # too many tries, give up
                raise Exception("Doc {} never made it to source bucket.  Aborting".format(doc_id))
            time.sleep(i)
            continue
    return doc 
