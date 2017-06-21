from __future__ import print_function

import time

import pytest

from couchbase.bucket import Bucket

from keywords import attachment, document
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.utils import host_for_url, log_info
from libraries.testkit.cluster import Cluster


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.xattrs
@pytest.mark.changes
@pytest.mark.session
@pytest.mark.parametrize('sg_conf_name, deletion_type', [
    ('sync_gateway_default_functional_tests', 'tombstone'),
    ('sync_gateway_default_functional_tests', 'purge')
])
def test_document_resurrection(params_from_base_test_setup, sg_conf_name, deletion_type):
    """
    Scenario:

    Doc meta mode / tombstone
    1. Create docs (set A) via Sync Gateway
    1. Delete docs (set A) via Sync Gateway
    1. Verify docs (set A) are deleted via Sync Gateway
    1. Create docs (set A) via Sync Gateway
    1. Verify revs (set A) are generation 3 via Sync Gateway

    Doc meta mode / purge
    1. Create docs (set A) via Sync Gateway
    1. Purge docs (set A) via Sync Gateway
    1. Verify docs (set A) are deleted via Sync Gateway
    1. Create docs (set A) via Sync Gateway
    1. Verify revs (set A) are generation 1 via Sync Gateway

    XATTRs / tombstone
    1. Create docs (set A) via Sync Gateway
    1. Create docs (set B) via SDK
    1. Delete docs (set A) via Sync Gateway
    1. Verify docs (set A) are deleted via Sync Gateway
    1. Verify docs (set A) are deleted via SDK
    1. Delete docs (set B) via SDK
    1. Verify docs (set B) are deleted via Sync Gateway
    1. Verify docs (set B) are deleted via SDK
    1. Create docs (set A) via Sync Gateway
    1. Create docs (set B) via SDK
    1. Verify revs (set A, B) are generation 3 via Sync Gateway

     XATTRs / purge
    1. Create docs (set A) via Sync Gateway
    1. Create docs (set B) via SDK
    1. Purge docs (set A) via Sync Gateway
    1. Verify docs (set A) are deleted via Sync Gateway
    1. Verify docs (set A) are deleted via SDK
    1. Delete docs (set B) via SDK
    1. Verify docs (set B) are deleted via Sync Gateway
    1. Verify docs (set B) are deleted via SDK
    1. Create docs (set A) via Sync Gateway
    1. Create docs (set B) via SDK
    1. Verify revs (set A, B) are generation 1 via Sync Gateway

    """
    cluster_conf = params_from_base_test_setup['cluster_config']
    cluster_topology = params_from_base_test_setup['cluster_topology']
    mode = params_from_base_test_setup['mode']
    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']

    cbs_url = cluster_topology['couchbase_servers'][0]
    sg_admin_url = cluster_topology['sync_gateways'][0]['admin']
    sg_url = cluster_topology['sync_gateways'][0]['public']

    bucket_name = 'data-bucket'
    sg_db = 'db'
    cbs_host = host_for_url(cbs_url)

    num_docs_per_client = 10

    # This test should only run when using xattr meta storage
    if not xattrs_enabled:
        pytest.skip('XATTR tests require --xattrs flag')

    # Reset cluster
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    # Initialize clients
    sg_client = MobileRestClient()
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_host, bucket_name), password='password')

    # Create Sync Gateway user
    sg_user_channels = ['NASA', 'NATGEO']
    sg_client.create_user(url=sg_admin_url, db=sg_db, name='seth', password='pass', channels=sg_user_channels)
    sg_user_auth = sg_client.create_session(url=sg_admin_url, db=sg_db, name='seth', password='pass')

    # Create docs
    sg_doc_bodies = document.create_docs(
        doc_id_prefix='sg_doc',
        number=num_docs_per_client,
        content={'foo': 'bar'},
        channels=sg_user_channels,
        attachments_generator=attachment.generate_2_png_10_10
    )
    sg_doc_ids = [doc['_id'] for doc in sg_doc_bodies]

    sdk_doc_bodies = document.create_docs(
        doc_id_prefix='sdk_doc',
        number=num_docs_per_client,
        content={'foo': 'bar'},
        channels=sg_user_channels,
    )
    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    sdk_doc_ids = [doc['_id'] for doc in sdk_doc_bodies]

    all_doc_ids = sg_doc_ids + sdk_doc_ids
    assert len(all_doc_ids) == num_docs_per_client * 2

    # Add docs from SG
    sg_bulk_docs_resp = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_doc_bodies, auth=sg_user_auth)
    assert len(sg_bulk_docs_resp) == num_docs_per_client

    # Add docs from sdk
    log_info('Creating SDK docs')
    sdk_client.upsert_multi(sdk_docs)

    # TODO: Remove once https://github.com/couchbase/sync_gateway/issues/2627 is fixed
    time.sleep(2)

    log_info('Deleting SDK docs')
    sdk_client.remove_multi(sdk_doc_ids)

    # Get all docs via Sync Gateway
    docs, errors = sg_client.get_bulk_docs(
        url=sg_url,
        db=sg_db,
        doc_ids=all_doc_ids,
        auth=sg_user_auth,
        validate=False
    )
    assert len(docs) == num_docs_per_client
    assert len(errors) == num_docs_per_client

    # TODO: Verify docs

    log_info('Recreating SDK docs')
    sdk_client.upsert_multi(sdk_docs)

    # Get all docs via Sync Gateway
    docs, errors = sg_client.get_bulk_docs(
        url=sg_url,
        db=sg_db,
        doc_ids=all_doc_ids,
        auth=sg_user_auth,
        validate=False
    )
    assert len(docs) == num_docs_per_client * 2
    assert len(errors) == 0

    # TODO verify docs

    # SG delete all docs
    for doc_id in all_doc_ids:
        doc = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id, auth=sg_user_auth)
        deleted = sg_client.delete_doc(url=sg_url, db=sg_db, doc_id=doc_id, rev=doc['_rev'], auth=sg_user_auth)
        log_info(deleted)

    # TODO: verify that SDK can't see tombstones

    # Recreate all docs
    for doc_id in sg_doc_ids:
        sg_bulk_docs_resp = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_doc_bodies, auth=sg_user_auth)
        assert len(sg_bulk_docs_resp) == num_docs_per_client

    # TODO: Test purge
