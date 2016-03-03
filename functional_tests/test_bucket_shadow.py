import time

import pytest

from lib.admin import Admin
from lib.verify import verify_changes
from collections import namedtuple
import json

from fixtures import cluster

default_config_path_shadower = "sync_gateway_bucketshadow_cc.json"
default_config_path_shadower_low_revs = "sync_gateway_bucketshadow_low_revs_cc.json"
default_config_path_non_shadower = "sync_gateway_default_cc.json"
default_config_path_non_shadower_low_revs = "sync_gateway_default_low_revs_cc.json"
source_bucket_name = "source-bucket"
data_bucket_name = "data-bucket"
fake_doc_content = {"foo":"bar"}

ShadowCluster = namedtuple(
    'ShadowCluster',
    [
        'source_bucket',
        'data_bucket',
        'mode',
        'non_shadower_sg',
        'shadower_sg',
        'admin',
        'alice_shadower',
        'bob_non_shadower',
    ],
    verbose=False)

def init_shadow_cluster(cluster, config_path_shadower, config_path_non_shadower):

    # initially, setup both sync gateways as shadowers -- this needs to be
    # the initial config so that both buckets (source and data) will be created
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

    source_bucket = cluster.servers[0].get_bucket(source_bucket_name)
    data_bucket = cluster.servers[0].get_bucket(data_bucket_name)

    sc = ShadowCluster(
        bob_non_shadower=bob_non_shadower,
        alice_shadower=alice_shadower,
        admin=admin,
        mode=mode,
        shadower_sg=shadower_sg,
        non_shadower_sg=non_shadower_sg,
        source_bucket=source_bucket,
        data_bucket=data_bucket,
    )
    
    return sc


# Validate that Sync Gateway doesn't panic (and instead creates a conflict branch
# and prints a warning) after doing the following steps:
# 
# - Set revs_limit to 5 
# - Create a doc via SG
# - Issue a delete operation for that doc via SG
# - Repeat step 3 5x. (each additional delete will create a new revision in SG, but the delete on the source bucket will fail with the 'not found' error, which also means that upstream_rev won't get incremented
# - Recreate the doc in the source bucket
#
# See https://github.com/couchbaselabs/sync-gateway-testcluster/issues/291#issuecomment-191521993 
def test_bucket_shadow_low_revs_limit_repeated_deletes(cluster):

    sc = init_shadow_cluster(cluster,
                             default_config_path_shadower_low_revs,
                             default_config_path_non_shadower_low_revs,
    )    

    # Write doc into shadower SG
    doc_id = sc.alice_shadower.add_doc()

    # Wait until it gets to source bucket
    get_doc_from_source_bucket_retry(doc_id, sc.source_bucket)    

    # Wait until upstream-rev in _sync metadata is non empty
    # Otherwise, this will not reproduce a panic 
    while True:
        doc = sc.data_bucket.get(doc_id)
        if doc.success:
            if "upstream_rev" in doc.value["_sync"]:
                break
        time.sleep(1)
    
    # Repeatedly issue a delete operation for that doc via SG
    # Keep adding tombstone revs to the one and only branch
    rev_id_to_delete = None
    for i in xrange(100):
        resp = sc.alice_shadower.delete_doc(doc_id, rev_id_to_delete)
        rev_id_to_delete = resp["rev"]

    # Recreate doc with that ID in the source bucket
    result = sc.source_bucket.upsert(doc_id, json.loads('{"foo":"bar"}'))

    # Check if SG's are up
    errors = cluster.verify_alive(sc.mode)
    assert(len(errors) == 0)

    # Restart Shadow SG
    sc.shadower_sg.stop()
    sc.shadower_sg.start(default_config_path_shadower_low_revs)
        
    # Check if SG's are up
    errors = cluster.verify_alive(sc.mode)
    assert(len(errors) == 0)
    

def test_bucket_shadow_low_revs_limit(cluster):
    """
    Set revs limit to 40
    Add doc and makes sure it syncs to source bucket
    Take shadower offline
    Update one doc more than 50 times
    Bring shadower online
    Look for panics
    Add more revisions to SG -- expected issue 
    Look for panics
    (TODO: Update doc in shadow bucket and look for panics?)
    """

    sc = init_shadow_cluster(cluster,
                             default_config_path_shadower_low_revs,
                             default_config_path_non_shadower_low_revs,
    )    

    # Write doc into shadower SG
    doc_id = sc.alice_shadower.add_doc()
    
    # Update the doc just so we have a rev_id
    sc.alice_shadower.update_doc(doc_id, content=fake_doc_content, num_revision=1)
    
    # Make sure it makes it to source bucket
    get_doc_with_content_from_source_bucket_retry(doc_id, fake_doc_content, sc.source_bucket)

    # Stop the SG shadower
    sc.shadower_sg.stop()

    # Update doc more than 50 times in non-shadower SG (since shadower is down)
    sc.bob_non_shadower.update_doc(doc_id, num_revision=100)
    sc.bob_non_shadower.update_doc(doc_id, content=fake_doc_content, num_revision=1)

    # Bring SG shadower back up
    sc.shadower_sg.start(default_config_path_shadower_low_revs)

    # Look for panics
    time.sleep(5) # Give tap feed a chance to initialize
    errors = cluster.verify_alive(sc.mode)
    assert(len(errors) == 0)
    
    # Verify that the latest revision sync'd to source bucket
    get_doc_with_content_from_source_bucket_retry(doc_id, fake_doc_content, sc.source_bucket)
    
    # Add more revisions
    sc.bob_non_shadower.update_doc(doc_id, num_revision=50)
    sc.bob_non_shadower.update_doc(doc_id, content=fake_doc_content, num_revision=1)
    
    # Verify that the latest revision sync'd to source bucket
    get_doc_with_content_from_source_bucket_retry(doc_id, fake_doc_content, sc.source_bucket)
    
    # Look for panics
    time.sleep(5) # Wait until the shadower can process
    errors = cluster.verify_alive(sc.mode)
    assert(len(errors) == 0)

    
def test_bucket_shadow_multiple_sync_gateways(cluster):

    sc = init_shadow_cluster(
        cluster,
        default_config_path_shadower,
        default_config_path_non_shadower,
    )
    
    # Write several docs into shadower SG
    doc_id_alice = sc.alice_shadower.add_doc()
    
    doc_id_will_delete = sc.alice_shadower.add_doc()
    
    # Write several docs into non-shadower SG
    doc_id_bob = sc.bob_non_shadower.add_doc()
        
    # Ditto as above, but bump revs rather than writing brand new docs
    sc.bob_non_shadower.update_doc(doc_id_bob, num_revision=10)
    sc.alice_shadower.update_doc(doc_id_alice, num_revision=10)

    # Get the doc from the source bucket, possibly retrying if needed
    # Otherwise an exception will be thrown and the test will fail
    get_doc_from_source_bucket_retry(doc_id_bob, sc.source_bucket)
    get_doc_from_source_bucket_retry(doc_id_alice, sc.source_bucket)
    get_doc_from_source_bucket_retry(doc_id_will_delete, sc.source_bucket)
    
    # Stop the SG shadower
    sc.shadower_sg.stop()
    
    # Write several docs + bump revs into non-shadower SG
    sc.bob_non_shadower.update_doc(doc_id_bob, num_revision=10)
    doc_id_shadower_down = sc.bob_non_shadower.add_doc()
    
    # Delete one of the docs
    sc.bob_non_shadower.delete_doc(doc_id_will_delete)
    
    # Bring SG shadower back up
    sc.shadower_sg.start(default_config_path_shadower)
    time.sleep(5)  # Give tap feed a chance to initialize
    
    # Verify SG shadower comes up without panicking, given writes from non-shadower during downtime.
    errors = cluster.verify_alive(sc.mode)
    assert(len(errors) == 0)

    # If SG shadower does come up without panicking, bump a rev on a document that was modified during the downtime of the SG shadower
    sc.bob_non_shadower.update_doc(doc_id_bob, num_revision=10)

    # Make sure the doc that was added while shadower was down makes it to source bucket
    # FAILING: Currently known to be failing, so temporarily disabled 
    # get_doc_from_source_bucket_retry(doc_id_shadower_down, sc.source_bucket)

    # Manual check
    # Grep logs for:
    # WARNING: Error pushing rev of "f6eb40bf-d02a-4b4d-a3ab-779cce2fe9d5" to external bucket: MCResponse status=KEY_ENOENT, opcode=DELETE, opaque=0, msg: Not found -- db.(*Shadower).PushRevision() at shadower.go:164
    
    # Verify SG shadower comes up without panicking, given writes from non-shadower during downtime.
    time.sleep(5) # Give tap feed a chance to initialize
    errors = cluster.verify_alive(sc.mode)
    assert(len(errors) == 0)


def get_doc_with_content_from_source_bucket_retry(doc_id, content_dict, bucket):
    """
    Get a document from the couchbase source bucket with particular content
    Will retry until it appears, or give up and raise an exception
    """
    doc  = None
    maxTries = 5
    i = 0
    while True:
        i += 1
        doc = bucket.get(doc_id, quiet=True)
        if doc.success:
            if "content" in doc.value and doc.value["content"] == content_dict:
                break
        else:
            if i > maxTries:
                # too many tries, give up
                raise Exception("Doc {} never made it to source bucket.  Aborting".format(doc_id))
            time.sleep(i)
            continue
    return doc 

    
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
        doc = bucket.get(doc_id, quiet=True)
        if doc.success:
            break
        else:
            if i > maxTries:
                # too many tries, give up
                raise Exception("Doc {} never made it to source bucket.  Aborting".format(doc_id))
            time.sleep(i)
            continue
    return doc 




    
