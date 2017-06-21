from __future__ import print_function

import time

import pytest
from requests.exceptions import HTTPError
from couchbase.exceptions import NotFoundError
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
    1. Delete SDK docs (set B) via Sync Gateway
    1. Delete SG docs (set A) via SDK
    1. Verify docs (set B) are deleted via Sync Gateway
    1. Verify docs (set B) are deleted via SDK
    1. Verify docs (set A) are deleted via Sync Gateway
    1. Verify docs (set A) are deleted via SDK
    1. Create docs (set A) via Sync Gateway
    1. Create docs (set B) via SDK
    1. Verify revs (set A, B) are generation 3 via Sync Gateway

     XATTRs / purge
    1. Create docs (set A) via Sync Gateway
    1. Create docs (set B) via SDK
    1. Purge SDK docs (set B) via Sync Gateway
    1. Delete SG docs (set A) via SDK
    1. Verify docs (set B) are deleted via Sync Gateway
    1. Verify docs (set B) are deleted via SDK
    1. Verify docs (set A) are deleted via Sync Gateway
    1. Verify docs (set A) are deleted via SDK
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

    # Create / Add docs from SG
    sg_doc_bodies = document.create_docs(
        doc_id_prefix='sg_doc',
        number=num_docs_per_client,
        content={'foo': 'bar'},
        channels=sg_user_channels,
        attachments_generator=attachment.generate_2_png_10_10
    )
    sg_doc_ids = [doc['_id'] for doc in sg_doc_bodies]

    sg_bulk_docs_resp = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_doc_bodies, auth=sg_user_auth)
    assert len(sg_bulk_docs_resp) == num_docs_per_client

    all_doc_ids = sg_doc_ids
    assert len(all_doc_ids) == num_docs_per_client

    if xattrs_enabled:
        #  Create / Add docs from sdk
        log_info('Adding docs via SDK')
        sdk_doc_bodies = document.create_docs(
            doc_id_prefix='sdk_doc',
            number=num_docs_per_client,
            content={'foo': 'bar'},
            channels=sg_user_channels,
        )
        sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
        sdk_doc_ids = [doc['_id'] for doc in sdk_doc_bodies]

        log_info('Creating SDK docs')
        sdk_client.upsert_multi(sdk_docs)

        all_doc_ids = sg_doc_ids + sdk_doc_ids
        assert len(all_doc_ids) == num_docs_per_client * 2

    if deletion_type == 'tombstone':
        # Set the target docs.
        # Doc meta mode: Delete Sync Gateway docs via Sync Gateway
        # XATTR mode: Delete SDK docs via Sync Gateway
        sg_doc_ids_to_delete = sg_doc_ids
        if xattrs_enabled:
            sg_doc_ids_to_delete = sdk_doc_ids

        # SG delete target docs
        for doc_id in sg_doc_ids_to_delete:
            doc = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id, auth=sg_user_auth)
            deleted = sg_client.delete_doc(url=sg_url, db=sg_db, doc_id=doc_id, rev=doc['_rev'], auth=sg_user_auth)
            log_info(deleted)

        if xattrs_enabled:
            log_info('Deleting SG docs via SDK')
            sdk_client.remove_multi(sg_doc_ids)

    elif deletion_type == 'purge':
        # SG Purge all docs
        all_docs, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=all_doc_ids, auth=sg_user_auth)
        if xattrs_enabled:
            assert len(all_docs) == num_docs_per_client * 2
            assert len(errors) == 0
        else:
            assert len(all_docs) == num_docs_per_client
            assert len(errors) == 0
        log_info('Purging docs via Sync Gateway')
        sg_client.purge_docs(url=sg_admin_url, db=sg_db, docs=all_docs)

    else:
        raise ValueError('Invalid test parameters')

    # Verify deletes via Sync Gateway
    deleted_docs_to_verify = sg_doc_ids
    if xattrs_enabled:
        deleted_docs_to_verify = sg_doc_ids + sdk_doc_ids
        assert len(deleted_docs_to_verify) == num_docs_per_client * 2
    if xattrs_enabled and deletion_type == 'tombstone':
        # Verify SDK + SG docs are deleted from Sync Gateway
        verify_sg_deletes(sg_client, sg_url, sg_db, deleted_docs_to_verify, sg_user_auth)
        # Verify SDK + SG docs are deleted from SDK
        verify_sdk_deletes(sdk_client, deleted_docs_to_verify)
    elif xattrs_enabled and deletion_type == 'purge':
        # Verify SDK + SG docs are purged from Sync Gateway
        verify_sg_purges(sg_client, sg_url, sg_db, deleted_docs_to_verify, sg_user_auth)
        # Verify SDK + SG docs are deleted from SDK
        verify_sdk_deletes(sdk_client, deleted_docs_to_verify)
    elif not xattrs_enabled and deletion_type == 'tombstone':
        # Doc meta: Verify SG docs are all deleted via SG
        # XATTRs: Verify SDK + SG docs are all deleted via SG
        verify_sg_deletes(sg_client, sg_url, sg_db, deleted_docs_to_verify, sg_user_auth)
    elif not xattrs_enabled and deletion_type == 'purge':
        # Doc meta: Verify SG docs are all deleted via SG
        # XATTRs: Verify SDK + SG docs are all deleted via SG
        verify_sg_purges(sg_client, sg_url, sg_db, deleted_docs_to_verify, sg_user_auth)
    else:
        raise ValueError('Invalid test parameters')

    # Recreate deleted docs from Sync Gateway
    sg_bulk_docs_resp = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_doc_bodies, auth=sg_user_auth)
    assert len(sg_bulk_docs_resp) == num_docs_per_client

    if xattrs_enabled:
        log_info('Recreating SDK docs')
        # Recreate deleted docs from SDK
        sdk_client.upsert_multi(sdk_docs)

    # Get docs via Sync Gateway
    doc_ids_to_get = sg_doc_ids
    if xattrs_enabled:
        doc_ids_to_get = sg_doc_ids + sdk_doc_ids
    docs, errors = sg_client.get_bulk_docs(
        url=sg_url,
        db=sg_db,
        doc_ids=doc_ids_to_get,
        auth=sg_user_auth,
        validate=False
    )
    if xattrs_enabled:
        assert len(docs) == num_docs_per_client * 2
        assert len(errors) == 0
    else:
        assert len(docs) == num_docs_per_client
        assert len(errors) == 0

    if xattrs_enabled:
        # Get SDK docs and makes sure all docs were recreated
        all_docs_from_sdk = sdk_client.get_multi(doc_ids_to_get)
        assert len(all_docs_from_sdk) == num_docs_per_client * 2
        log_info('Found: {} recreated docs via SDK'.format(len(all_docs_from_sdk)))

        # Make sure we are able to get recreated docs via SDK
        doc_ids_to_get_scratch = list(doc_ids_to_get)
        assert len(doc_ids_to_get_scratch) == num_docs_per_client * 2
        for doc_id in all_docs_from_sdk:
            doc_ids_to_get_scratch.remove(doc_id)
        assert len(doc_ids_to_get_scratch) == 0

    # Make sure we are able to get recreated docs via SDK
    doc_ids_to_get_scratch = list(doc_ids_to_get)
    assert len(doc_ids_to_get_scratch) == num_docs_per_client * 2
    for doc in docs:
        # Check that the doc has a rev generation of 3 (Create, Delete (Tombstone), Recreate)
        if deletion_type == 'purge':
            assert doc['_rev'].startswith('1-')
        else:
            assert doc['_rev'].startswith('3-')
        doc_ids_to_get_scratch.remove(doc['_id'])

    # Make sure all docs were found
    assert len(doc_ids_to_get_scratch) == 0


def verify_sg_deletes(sg_client, sg_url, sg_db, expected_deleted_ids, sg_auth):
    for doc_id in expected_deleted_ids:
        he = None
        with pytest.raises(HTTPError) as he:
            sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id, auth=sg_auth)
        assert he is not None
        log_info(he.value.message)
        # TODO Verify this with adam
        assert he.value.message.startswith('403 Client Error: Forbidden for url:')


def verify_sg_purges(sg_client, sg_url, sg_db, expected_deleted_ids, sg_auth):
    for doc_id in expected_deleted_ids:
        he = None
        with pytest.raises(HTTPError) as he:
            sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id, auth=sg_auth)
        assert he is not None
        log_info(he.value.message)
        # TODO Verify this with adam
        assert he.value.message.startswith('404 Client Error: Not Found for url:')


def verify_sdk_deletes(sdk_client, expected_deleted_ids):
    for doc_id in expected_deleted_ids:
        nfe = None
        with pytest.raises(NotFoundError) as nfe:
            sdk_client.get(doc_id)
        assert nfe is not None
        log_info(nfe.value.message)
        assert 'The key does not exist on the server' in str(nfe)
