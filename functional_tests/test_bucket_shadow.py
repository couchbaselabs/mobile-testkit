import time

import pytest


from lib.admin import Admin
from lib.verify import verify_changes

from fixtures import cluster


def test_bucket_shadow_multiple_sync_gateways(cluster):

    # initially, setup both sync gateways as shadowers -- this needs to be
    # the initial config so that both buckets (source and data) will be created
    config_path_shadower = "sync_gateway_bucketshadow_cc.json"
    config_path_non_shadower = "sync_gateway_default_cc.json"
    source_bucket_name = "source-bucket"
    
    mode = cluster.reset(config_path=config_path_shadower)

    # pick a sync gateway and choose it as non-shadower.  reset with config.
    non_shadower_sg = cluster.sync_gateways[1]
    non_shadower_sg.restart(config_path_non_shadower)

    # the other sync gateway will be the shadower
    shadower_sg = cluster.sync_gateways[0]

    admin = Admin(non_shadower_sg)

    alice_shadower = admin.register_user(
        target=shadower_sg,
        db="db",
        name="alice",
        password="password",
        channels=["ABC", "NBC", "CBS"],
    )

    bob_non_shadower = admin.register_user(
        target=non_shadower_sg,
        db="db",
        name="bob",
        password="password",
        channels=["ABC", "NBC", "CBS"],
    )
    
    # Write several docs into shadower SG
    doc_id_alice = alice_shadower.add_doc()
    
    # Write several docs into non-shadower SG
    doc_id_bob = bob_non_shadower.add_doc()
    
    # Ditto as above, but bump revs rather than writing brand new docs
    bob_non_shadower.update_doc(doc_id_bob, num_revision=10)
    alice_shadower.update_doc(doc_id_alice, num_revision=10)

    # Get a connection to the bucket
    bucket = cluster.servers[0].get_bucket(source_bucket_name)

    # Get the doc from the source bucket, possibly retrying if needed
    # Otherwise an exception will be thrown and the test will fail
    get_doc_from_source_bucket_retry(doc_id_bob, bucket)
    get_doc_from_source_bucket_retry(doc_id_alice, bucket)
    
    # Stop the SG shadower
    shadower_sg.stop()
    
    # Write several docs + bump revs into non-shadower SG
    bob_non_shadower.update_doc(doc_id_bob, num_revision=10)
    doc2_id_bob = bob_non_shadower.add_doc()
    
    # Bring SG shadower back up
    shadower_sg.start(config_path_shadower)
    
    # Verify SG shadower comes up without panicking, given writes from non-shadower during downtime.
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)

    # If SG shadower does come up without panicking, bump a rev on a document that was modified during the downtime of the SG shadower
    bob_non_shadower.update_doc(doc_id_bob, num_revision=10)

    # Verify SG shadower comes up without panicking, given writes from non-shadower during downtime.
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)


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
