import time

import pytest


from lib.admin import Admin
from lib.verify import verify_changes
from collections import namedtuple

from fixtures import cluster

default_config_path_shadower = "sync_gateway_bucketshadow_cc.json"
default_config_path_shadower_low_revs = "sync_gateway_bucketshadow_low_revs_cc.json"
default_config_path_non_shadower = "sync_gateway_default_cc.json"
default_config_path_non_shadower_low_revs = "sync_gateway_default_low_revs_cc.json"
source_bucket_name = "source-bucket"
fake_doc_content = {"foo":"bar"}

ShadowCluster = namedtuple(
    'ShadowCluster',
    [
        'source_bucket',
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

    sc = ShadowCluster(
        bob_non_shadower=bob_non_shadower,
        alice_shadower=alice_shadower,
        admin=admin,
        mode=mode,
        shadower_sg=shadower_sg,
        non_shadower_sg=non_shadower_sg,
        source_bucket=source_bucket,
    )
    
    return sc

def test_bucket_shadow_low_revs_limit(cluster):
    """
    Set revs limit to 40
    Add doc and makes sure it syncs to source bucket
    Take shadower offline
    Update one doc more than 50 times
    Bring shadower online
    Look for panics
    Add more revisions
    Look for panics
    (TODO: Update doc in shadow bucket and look for panics?)
    """

    sc = init_shadow_cluster(cluster, default_config_path_shadower_low_revs, default_config_path_non_shadower_low_revs)    

    # Write doc into shadower SG
    doc_id = sc.alice_shadower.add_doc()
    print("Added doc_id: {}".format(doc_id))
    
    # Update the doc just so we have a rev_id
    updated_docs = sc.alice_shadower.update_doc(doc_id, content=fake_doc_content, num_revision=1)
    print("Update doc_id: {} with content: {}".format(doc_id, fake_doc_content))
    
    # Make sure it makes it to source bucket
    get_doc_with_content_from_source_bucket_retry(doc_id, fake_doc_content, sc.source_bucket)

    # Stop the SG shadower
    sc.shadower_sg.stop()

    # Update doc more than 50 times in non-shadower SG (since shadower is down)
    updated_docs = sc.bob_non_shadower.update_doc(doc_id, num_revision=100)
    updated_docs = sc.bob_non_shadower.update_doc(doc_id, content=fake_doc_content, num_revision=1)

    # Bring SG shadower back up
    sc.shadower_sg.start(default_config_path_shadower_low_revs)

    # Look for panics
    time.sleep(5) # Give tap feed a chance to initialize
    errors = cluster.verify_alive(sc.mode)

    # Verify that the latest revision sync'd to source bucket
    get_doc_with_content_from_source_bucket_retry(doc_id, fake_doc_content, sc.source_bucket)
    
    # Add more revisions
    updated_docs = sc.bob_non_shadower.update_doc(doc_id, num_revision=50)
    updated_docs = sc.bob_non_shadower.update_doc(doc_id, content=fake_doc_content, num_revision=1)
    
    # Verify that the latest revision sync'd to source bucket
    get_doc_with_content_from_source_bucket_retry(doc_id, fake_doc_content, sc.source_bucket)
    
    # Look for panics
    time.sleep(5) # Wait until the shadower can process
    errors = cluster.verify_alive(sc.mode)
    assert(len(errors) == 0)



    
def test_bucket_shadow_multiple_sync_gateways(cluster):


    # TODO: flavors of delete
    #       doc exists that has been pushed to source bucket
    #       while shadower offline
    #       bring shadower online, look for panics and failed delete operations (only option is to looking in logs .. manually)

    # TODO: take shadower offline
    #       write one new doc
    #       bring shadower online
    #       check whether new doc is pushed to source bucket
    #       assert that it does, fail test if not

    # TODO: start tap pusher from zero (hack)
    #       rerun above tests (in particular revs limit 40 test)

    #	listener.TapArgs = sgbucket.TapArguments{
    #		Backfill: sgbucket.TapNoBackfill,  // <--- set that to 0 instead of TapNoBackfill
    #		Notify:   notify,
    #	}

    sc = init_shadow_cluster(cluster, default_config_path_shadower, default_config_path_non_shadower)
    
    # Write several docs into shadower SG
    doc_id_alice = sc.alice_shadower.add_doc()
    
    # Write several docs into non-shadower SG
    doc_id_bob = sc.bob_non_shadower.add_doc()
    
    # Ditto as above, but bump revs rather than writing brand new docs
    sc.bob_non_shadower.update_doc(doc_id_bob, num_revision=10)
    sc.alice_shadower.update_doc(doc_id_alice, num_revision=10)

    # Get the doc from the source bucket, possibly retrying if needed
    # Otherwise an exception will be thrown and the test will fail
    get_doc_from_source_bucket_retry(doc_id_bob, sc.source_bucket)
    get_doc_from_source_bucket_retry(doc_id_alice, sc.source_bucket)
    
    # Stop the SG shadower
    sc.shadower_sg.stop()
    
    # Write several docs + bump revs into non-shadower SG
    bob_non_shadower.update_doc(doc_id_bob, num_revision=10)
    doc2_id_bob = sc.bob_non_shadower.add_doc()
    
    # Bring SG shadower back up
    sc.shadower_sg.start(default_config_path_shadower)

    time.sleep(5)  # Give tap feed a chance to initialize
    
    # Verify SG shadower comes up without panicking, given writes from non-shadower during downtime.
    errors = cluster.verify_alive(sc.mode)
    assert(len(errors) == 0)

    # If SG shadower does come up without panicking, bump a rev on a document that was modified during the downtime of the SG shadower
    bob_non_shadower.update_doc(doc_id_bob, num_revision=10)

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
            print("Got doc: {} with val: {}".format(doc, doc.value))
            if doc.value["content"] == content_dict:
                break
        else:
            if i > maxTries:
                # too many tries, give up
                raise Exception("Doc {} never made it to source bucket.  Aborting".format(doc_id))
            print "Sleeping for {} seconds".format(i)
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
