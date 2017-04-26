import time
import json

import pytest

from libraries.testkit.admin import Admin
from libraries.testkit.cluster import Cluster
from keywords.SyncGateway import sync_gateway_config_path_for_mode

from keywords.utils import log_info

from collections import namedtuple


source_bucket_name = "source-bucket"
data_bucket_name = "data-bucket"
fake_doc_content = {"foo": "bar"}

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
    mode = cluster.reset(sg_config_path=config_path_shadower)

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


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.bucketshadow
@pytest.mark.channel
@pytest.mark.basicauth
def test_bucket_shadow_low_revs_limit_repeated_deletes(params_from_base_test_setup):
    """
    Validate that Sync Gateway doesn't panic (and instead creates a conflict branch
    and prints a warning) after doing the following steps:

    - Set revs_limit to 5
    - Create a doc via SG
    - Issue a delete operation for that doc via SG
    - Repeat step 3 5x. (each additional delete will create a new revision in SG, but the delete on the source bucket will fail with the 'not found' error, which also means that upstream_rev won't get incremented
    - Recreate the doc in the source bucket
    See https://github.com/couchbaselabs/sync-gateway-testcluster/issues/291#issuecomment-191521993
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    if mode == "di":
        pytest.skip("https://github.com/couchbase/sync_gateway/issues/2193")

    default_config_path_shadower_low_revs = sync_gateway_config_path_for_mode("sync_gateway_bucketshadow_low_revs", mode)
    default_config_path_non_shadower_low_revs = sync_gateway_config_path_for_mode("sync_gateway_default_low_revs", mode)

    log_info("Running 'test_bucket_shadow_low_revs_limit_repeated_deletes'")
    log_info("Using cluster_config: {}".format(cluster_config))

    cluster = Cluster(config=cluster_config)
    sc = init_shadow_cluster(cluster,
                             default_config_path_shadower_low_revs,
                             default_config_path_non_shadower_low_revs)

    # Wait until shadower db is online, since deleting the bucket as part of provisioning might take it offline for a bit
    log_info("wait_until_db_online")
    sc.alice_shadower.wait_until_db_online()
    log_info("/wait_until_db_online")

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
    sc.source_bucket.upsert(doc_id, json.loads('{"foo":"bar"}'))

    # Check if SG's are up
    errors = cluster.verify_alive(sc.mode)
    assert len(errors) == 0

    # Restart Shadow SG
    sc.shadower_sg.stop()
    sc.shadower_sg.start(default_config_path_shadower_low_revs)


@pytest.mark.topospecific
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.bucketshadow
@pytest.mark.channel
@pytest.mark.basicauth
def test_bucket_shadow_low_revs_limit(params_from_base_test_setup):
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

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    if mode == "di":
        pytest.skip("https://github.com/couchbase/sync_gateway/issues/2193")

    log_info("Running 'test_bucket_shadow_low_revs_limit'")
    log_info("Using cluster_config: {}".format(cluster_config))

    default_config_path_shadower_low_revs = sync_gateway_config_path_for_mode("sync_gateway_bucketshadow_low_revs", mode)
    default_config_path_non_shadower_low_revs = sync_gateway_config_path_for_mode("sync_gateway_default_low_revs", mode)

    cluster = Cluster(config=cluster_config)
    sc = init_shadow_cluster(cluster, default_config_path_shadower_low_revs, default_config_path_non_shadower_low_revs)

    # Wait until shadower db is online, since deleting the bucket as part of provisioning might take it offline for a bit
    log_info("wait_until_db_online")
    sc.alice_shadower.wait_until_db_online()
    log_info("/wait_until_db_online")

    # Write doc into shadower SG
    doc_id = sc.alice_shadower.add_doc()
    log_info("Wrote doc {} into {}".format(doc_id, sc.alice_shadower))

    # Update the doc just so we have a rev_id
    resp = sc.alice_shadower.update_doc(doc_id, content=fake_doc_content, num_revision=1)
    log_info("Wrote new rev {} into {}".format(resp, sc.alice_shadower))

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
    time.sleep(5)  # Give tap feed a chance to initialize
    errors = cluster.verify_alive(sc.mode)
    assert len(errors) == 0

    # Verify that the latest revision sync'd to source bucket
    get_doc_with_content_from_source_bucket_retry(doc_id, fake_doc_content, sc.source_bucket)

    # Add more revisions
    sc.bob_non_shadower.update_doc(doc_id, num_revision=50)
    sc.bob_non_shadower.update_doc(doc_id, content=fake_doc_content, num_revision=1)

    # Verify that the latest revision sync'd to source bucket
    get_doc_with_content_from_source_bucket_retry(doc_id, fake_doc_content, sc.source_bucket)

    # Look for panics
    time.sleep(5)  # Wait until the shadower can process


@pytest.mark.topospecific
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.bucketshadow
@pytest.mark.channel
@pytest.mark.basicauth
def test_bucket_shadow_multiple_sync_gateways(params_from_base_test_setup):

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    if mode == "di":
        pytest.skip("https://github.com/couchbase/sync_gateway/issues/2193")

    log_info("Running 'test_bucket_shadow_multiple_sync_gateways'")
    log_info("Using cluster_config: {}".format(cluster_config))

    default_config_path_shadower = sync_gateway_config_path_for_mode("sync_gateway_bucketshadow", mode)
    default_config_path_non_shadower = sync_gateway_config_path_for_mode("sync_gateway_default", mode)

    cluster = Cluster(config=cluster_config)
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
    sc.bob_non_shadower.add_doc()

    # Delete one of the docs
    sc.bob_non_shadower.delete_doc(doc_id_will_delete)

    # Bring SG shadower back up
    sc.shadower_sg.start(default_config_path_shadower)
    time.sleep(5)  # Give tap feed a chance to initialize

    # Verify SG shadower comes up without panicking, given writes from non-shadower during downtime.
    errors = cluster.verify_alive(sc.mode)
    assert len(errors) == 0

    # If SG shadower does come up without panicking, bump a rev on a document that was modified during the downtime of the SG shadower
    sc.bob_non_shadower.update_doc(doc_id_bob, num_revision=10)

    # Make sure the doc that was added while shadower was down makes it to source bucket
    # FAILING: Currently known to be failing, so temporarily disabled
    # get_doc_from_source_bucket_retry(doc_id_shadower_down, sc.source_bucket)

    # Manual check
    # Grep logs for:
    # WARNING: Error pushing rev of "f6eb40bf-d02a-4b4d-a3ab-779cce2fe9d5" to external bucket: MCResponse status=KEY_ENOENT, opcode=DELETE, opaque=0, msg: Not found -- db.(*Shadower).PushRevision() at shadower.go:164

    # Verify SG shadower comes up without panicking, given writes from non-shadower during downtime.
    time.sleep(5)  # Give tap feed a chance to initialize


def get_doc_with_content_from_source_bucket_retry(doc_id, content_dict, bucket):
    """
    Get a document from the couchbase source bucket with particular content
    Will retry until it appears, or give up and raise an exception
    """
    doc = None
    max_tries = 5
    i = 0
    while True:
        i += 1
        doc = bucket.get(doc_id, quiet=True)
        if doc.success:
            if "content" in doc.value and doc.value["content"] == content_dict:
                break
        else:
            if i > max_tries:
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
    doc = None
    max_tries = 5
    i = 0
    while True:
        i += 1
        doc = bucket.get(doc_id, quiet=True)
        if doc.success:
            break
        else:
            if i > max_tries:
                # too many tries, give up
                raise Exception("Doc {} never made it to source bucket.  Aborting".format(doc_id))
            time.sleep(i)
            continue
    return doc
