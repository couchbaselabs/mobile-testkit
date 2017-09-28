from __future__ import print_function

import random
import time
import json

import pytest
from concurrent.futures import ThreadPoolExecutor

from couchbase.bucket import Bucket
from couchbase.exceptions import KeyExistsError, NotFoundError
from requests.exceptions import HTTPError
from keywords.exceptions import ChangesError

from keywords import attachment, document
from keywords.constants import DATA_DIR, SDK_TIMEOUT
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.SyncGateway import SyncGateway
from keywords.userinfo import UserInfo
from keywords.utils import host_for_url, log_info
from libraries.testkit.cluster import Cluster
from keywords.ChangesTracker import ChangesTracker

# Since sdk is quicker to update docs we need to have it sleep longer
# between ops to avoid ops heavily weighted to SDK. These gives us more balanced
# concurrency for each client.
SG_OP_SLEEP = 0.001
SDK_OP_SLEEP = 0.05


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.xattrs
@pytest.mark.session
@pytest.mark.parametrize('sg_conf_name', [
    'xattrs/old_doc'
])
def test_olddoc_nil(params_from_base_test_setup, sg_conf_name):
    """ Regression test for - https://github.com/couchbase/sync_gateway/issues/2565

    Using the custom sync function:
        function(doc, oldDoc) {
            if (oldDoc != null) {
                throw({forbidden: "Old doc should be null!"})
            } else {
                console.log("oldDoc is null");
                console.log(doc.channels);
                channel(doc.channels);
            }
        }

    1. Create user with channel 'ABC' (user1)
    2. Create user with channel 'CBS' (user2)
    3. Write doc with channel 'ABC'
    4. Verify that user1 can see the doc and user2 cannot
    5. SDK updates the doc channel to 'CBS'
    6. This should result in a new rev but with oldDoc == nil (due to SDK mutation)
    7. Assert that user2 can see the doc and user1 cannot
    """

    bucket_name = 'data-bucket'
    sg_db = 'db'
    num_docs = 1000

    cluster_conf = params_from_base_test_setup['cluster_config']
    cluster_topology = params_from_base_test_setup['cluster_topology']
    mode = params_from_base_test_setup['mode']
    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']

    # This test should only run when using xattr meta storage
    if not xattrs_enabled:
        pytest.skip('XATTR tests require --xattrs flag')

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_admin_url = cluster_topology['sync_gateways'][0]['admin']
    sg_url = cluster_topology['sync_gateways'][0]['public']
    cbs_url = cluster_topology['couchbase_servers'][0]

    log_info('sg_conf: {}'.format(sg_conf))
    log_info('sg_admin_url: {}'.format(sg_admin_url))
    log_info('sg_url: {}'.format(sg_url))
    log_info('cbs_url: {}'.format(cbs_url))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    # Create clients
    sg_client = MobileRestClient()
    cbs_ip = host_for_url(cbs_url)
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password', timeout=SDK_TIMEOUT)

    # Create user / session
    user_one_info = UserInfo(name='user1', password='pass', channels=['ABC'], roles=[])
    user_two_info = UserInfo(name='user2', password='pass', channels=['CBS'], roles=[])

    for user in [user_one_info, user_two_info]:
        sg_client.create_user(
            url=sg_admin_url,
            db=sg_db,
            name=user.name,
            password=user.password,
            channels=user.channels
        )

    user_one_auth = sg_client.create_session(
        url=sg_admin_url,
        db=sg_db,
        name=user_one_info.name,
        password=user_one_info.password
    )

    user_two_auth = sg_client.create_session(
        url=sg_admin_url,
        db=sg_db,
        name=user_two_info.name,
        password=user_two_info.password
    )

    abc_docs = document.create_docs(doc_id_prefix="abc_docs", number=num_docs, channels=user_one_info.channels)
    abc_doc_ids = [doc['_id'] for doc in abc_docs]

    user_one_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=abc_docs, auth=user_one_auth)
    assert len(user_one_docs) == num_docs

    # Issue bulk_get from user_one and assert that user_one, can see all of the docs
    user_one_bulk_get_docs, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=abc_doc_ids, auth=user_one_auth)
    assert len(user_one_bulk_get_docs) == num_docs
    assert len(errors) == 0

    # Issue bulk_get from user_two and assert that user_two cannot see any of the docs
    user_two_bulk_get_docs, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=abc_doc_ids, auth=user_two_auth, validate=False)
    assert len(user_two_bulk_get_docs) == 0
    assert len(errors) == num_docs

    # Update the channels of each doc to 'NBC'
    for abc_doc_id in abc_doc_ids:
        doc = sdk_client.get(abc_doc_id)
        doc_body = doc.value
        doc_body['channels'] = user_two_info.channels
        sdk_client.upsert(abc_doc_id, doc_body)

    # Issue bulk_get from user_one and assert that user_one can't see any docs
    user_one_bulk_get_docs, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=abc_doc_ids, auth=user_one_auth, validate=False)
    assert len(user_one_bulk_get_docs) == 0
    assert len(errors) == num_docs

    # Issue bulk_get from user_two and assert that user_two can see all docs
    user_two_bulk_get_docs, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=abc_doc_ids, auth=user_two_auth)
    assert len(user_two_bulk_get_docs) == num_docs
    assert len(errors) == 0


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.xattrs
@pytest.mark.session
@pytest.mark.parametrize('sg_conf_name', [
    'xattrs/no_import'
])
def test_on_demand_import_of_external_updates(params_from_base_test_setup, sg_conf_name):
    """
    Scenario: On demand processing of external updates

    - Start sg with XATTRs, but not import
    - Create doc via SG, store rev (#1)
    - Update doc via SDK
    - Update doc via SG, using (#1), should fail with conflict
    """

    bucket_name = 'data-bucket'
    sg_db = 'db'

    cluster_conf = params_from_base_test_setup['cluster_config']
    cluster_topology = params_from_base_test_setup['cluster_topology']
    mode = params_from_base_test_setup['mode']
    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']

    # This test should only run when using xattr meta storage
    if not xattrs_enabled:
        pytest.skip('XATTR tests require --xattrs flag')

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_admin_url = cluster_topology['sync_gateways'][0]['admin']
    sg_url = cluster_topology['sync_gateways'][0]['public']
    cbs_url = cluster_topology['couchbase_servers'][0]

    log_info('sg_conf: {}'.format(sg_conf))
    log_info('sg_admin_url: {}'.format(sg_admin_url))
    log_info('sg_url: {}'.format(sg_url))
    log_info('cbs_url: {}'.format(cbs_url))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    # Create clients
    sg_client = MobileRestClient()
    cbs_ip = host_for_url(cbs_url)
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password', timeout=SDK_TIMEOUT)

    # Create user / session
    seth_user_info = UserInfo(name='seth', password='pass', channels=['NASA'], roles=[])
    sg_client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=seth_user_info.name,
        password=seth_user_info.password,
        channels=seth_user_info.channels
    )

    seth_auth = sg_client.create_session(
        url=sg_admin_url,
        db=sg_db,
        name=seth_user_info.name,
        password=seth_user_info.password
    )

    doc_id = 'test_doc'

    doc_body = document.create_doc(doc_id, channels=seth_user_info.channels)
    doc = sg_client.add_doc(url=sg_url, db=sg_db, doc=doc_body, auth=seth_auth)
    doc_rev_one = doc['rev']

    log_info('Created doc: {} via Sync Gateway'.format(doc))

    # Update the document via SDK
    doc_to_update = sdk_client.get(doc_id)
    doc_body = doc_to_update.value
    doc_body['updated_via_sdk'] = True
    updated_doc = sdk_client.upsert(doc_id, doc_body)
    log_info('Updated doc: {} via SDK'.format(updated_doc))

    # Try to create a revision of generation 1 from Sync Gateway.
    # If on demand importing is working as designed, it should go to the
    # bucket and see that there has been an external update and import it.
    # Sync Gateway should then get a 409 conflict when trying to update the doc
    with pytest.raises(HTTPError) as he:
        sg_client.put_doc(url=sg_url, db=sg_db, doc_id=doc_id, rev=doc_rev_one, doc_body=doc_body, auth=seth_auth)
    log_info(he.value)
    assert he.value.message.startswith('409')


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.xattrs
@pytest.mark.session
@pytest.mark.parametrize('sg_conf_name', [
    'sync_gateway_default_functional_tests',
])
def test_offline_processing_of_external_updates(params_from_base_test_setup, sg_conf_name):
    """
    Scenario:
    1. Start SG, write some docs
    2. Stop SG
    3. Update the same docs via SDK (to ensure the same vbucket is getting updated)
    4. Write some new docs for SDK (just for additional testing)
    5. Restart SG, validate that all writes from 3 and 4 have been imported (w/ correct revisions)
    """

    num_docs_per_client = 1000
    bucket_name = 'data-bucket'
    sg_db = 'db'

    cluster_conf = params_from_base_test_setup['cluster_config']
    cluster_topology = params_from_base_test_setup['cluster_topology']
    mode = params_from_base_test_setup['mode']
    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']

    # This test should only run when using xattr meta storage
    if not xattrs_enabled:
        pytest.skip('XATTR tests require --xattrs flag')

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_admin_url = cluster_topology['sync_gateways'][0]['admin']
    sg_url = cluster_topology['sync_gateways'][0]['public']
    cbs_url = cluster_topology['couchbase_servers'][0]

    log_info('sg_conf: {}'.format(sg_conf))
    log_info('sg_admin_url: {}'.format(sg_admin_url))
    log_info('sg_url: {}'.format(sg_url))
    log_info('cbs_url: {}'.format(cbs_url))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    # Create clients
    sg_client = MobileRestClient()
    cbs_ip = host_for_url(cbs_url)
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password', timeout=SDK_TIMEOUT)

    # Create user / session
    seth_user_info = UserInfo(name='seth', password='pass', channels=['SG', 'SDK'], roles=[])
    sg_client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=seth_user_info.name,
        password=seth_user_info.password,
        channels=seth_user_info.channels
    )

    seth_auth = sg_client.create_session(
        url=sg_admin_url,
        db=sg_db,
        name=seth_user_info.name,
        password=seth_user_info.password
    )

    # Add docs
    sg_docs = document.create_docs('sg', number=num_docs_per_client, channels=['SG'])
    sg_doc_ids = [doc['_id'] for doc in sg_docs]
    bulk_docs_resp = sg_client.add_bulk_docs(
        url=sg_url,
        db=sg_db,
        docs=sg_docs,
        auth=seth_auth
    )
    assert len(bulk_docs_resp) == num_docs_per_client

    # Stop Sync Gateway
    sg_controller = SyncGateway()
    sg_controller.stop_sync_gateways(cluster_conf, url=sg_url)

    # Update docs that sync gateway wrote via SDK
    sg_docs_via_sdk_get = sdk_client.get_multi(sg_doc_ids)
    assert len(sg_docs_via_sdk_get.keys()) == num_docs_per_client
    for doc_id, val in sg_docs_via_sdk_get.items():
        log_info("Updating: '{}' via SDK".format(doc_id))
        doc_body = val.value
        doc_body["updated_by_sdk"] = True
        sdk_client.upsert(doc_id, doc_body)

    # Add additional docs via SDK
    log_info('Adding {} docs via SDK ...'.format(num_docs_per_client))
    sdk_doc_bodies = document.create_docs('sdk', number=num_docs_per_client, channels=['SDK'])
    sdk_doc_ids = [doc['_id'] for doc in sdk_doc_bodies]
    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    sdk_docs_resp = sdk_client.upsert_multi(sdk_docs)
    assert len(sdk_docs_resp) == num_docs_per_client

    # Start Sync Gateway
    sg_controller.start_sync_gateways(cluster_conf, url=sg_url, config=sg_conf)

    # Verify all docs are gettable via Sync Gateway
    all_doc_ids = sg_doc_ids + sdk_doc_ids
    assert len(all_doc_ids) == num_docs_per_client * 2
    bulk_resp, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=all_doc_ids, auth=seth_auth)
    assert len(errors) == 0

    # Create a scratch pad and check off docs
    all_doc_ids_scratch_pad = list(all_doc_ids)
    for doc in bulk_resp:
        log_info(doc)
        if doc['_id'].startswith('sg_'):
            # Rev prefix should be '2-' due to the write by Sync Gateway and the update by SDK
            assert doc['_rev'].startswith('2-')
            assert doc['updated_by_sdk']
        else:
            # SDK created doc. Should only have 1 rev from import
            assert doc['_rev'].startswith('1-')
        all_doc_ids_scratch_pad.remove(doc['_id'])
    assert len(all_doc_ids_scratch_pad) == 0

    # Verify all of the docs show up in the changes feed
    docs_to_verify_in_changes = [{'id': doc['_id'], 'rev': doc['_rev']} for doc in bulk_resp]
    sg_client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=docs_to_verify_in_changes, auth=seth_auth)


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.xattrs
@pytest.mark.session
@pytest.mark.parametrize('sg_conf_name', [
    'sync_gateway_default_functional_tests',
])
def test_large_initial_import(params_from_base_test_setup, sg_conf_name):
    """ Regression test for https://github.com/couchbase/sync_gateway/issues/2537
    Scenario:
    - Stop Sync Gateway
    - Bulk create 30000 docs via SDK
    - Start Sync Gateway to begin import
    - Verify all docs are imported
    """

    num_docs = 30000
    bucket_name = 'data-bucket'
    sg_db = 'db'

    cluster_conf = params_from_base_test_setup['cluster_config']
    cluster_topology = params_from_base_test_setup['cluster_topology']
    mode = params_from_base_test_setup['mode']
    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']

    # This test should only run when using xattr meta storage
    if not xattrs_enabled:
        pytest.skip('XATTR tests require --xattrs flag')

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_admin_url = cluster_topology['sync_gateways'][0]['admin']
    sg_url = cluster_topology['sync_gateways'][0]['public']
    cbs_url = cluster_topology['couchbase_servers'][0]

    log_info('sg_conf: {}'.format(sg_conf))
    log_info('sg_admin_url: {}'.format(sg_admin_url))
    log_info('sg_url: {}'.format(sg_url))
    log_info('cbs_url: {}'.format(cbs_url))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    # Stop Sync Gateway
    sg_controller = SyncGateway()
    sg_controller.stop_sync_gateways(cluster_conf, url=sg_url)

    # Connect to server via SDK
    cbs_ip = host_for_url(cbs_url)
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password', timeout=SDK_TIMEOUT)

    # Generate array for each doc doc to give it a larger size
    def prop_gen():
        return {'sample_array': ["test_item_{}".format(i) for i in range(20)]}

    # Create 'num_docs' docs from SDK
    sdk_doc_bodies = document.create_docs('sdk', num_docs, channels=['created_via_sdk'], prop_generator=prop_gen)
    sdk_doc_ids = [doc['_id'] for doc in sdk_doc_bodies]
    assert len(sdk_doc_ids) == num_docs
    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    sdk_client.upsert_multi(sdk_docs)

    # Start Sync Gateway to begin import
    sg_controller.start_sync_gateways(cluster_conf, url=sg_url, config=sg_conf)

    # Let some documents process
    log_info('Sleeping 30s to let some docs auto import')
    time.sleep(30)

    # Any document that have not been imported with be imported on demand.
    # Verify that all the douments have been imported
    sg_client = MobileRestClient()
    seth_auth = sg_client.create_user(url=sg_admin_url, db=sg_db, name='seth', password='pass', channels=['created_via_sdk'])

    sdk_doc_ids_scratch_pad = list(sdk_doc_ids)
    bulk_resp, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=sdk_doc_ids, auth=seth_auth)
    assert len(errors) == 0

    for doc in bulk_resp:
        log_info('Doc: {}'.format(doc))
        assert doc['_rev'].startswith('1-')
        sdk_doc_ids_scratch_pad.remove(doc['_id'])

    assert len(sdk_doc_ids_scratch_pad) == 0

    # Verify all of the docs show up in the changes feed
    docs_to_verify_in_changes = [{'id': doc['_id'], 'rev': doc['_rev']} for doc in bulk_resp]
    sg_client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=docs_to_verify_in_changes, auth=seth_auth)


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.xattrs
@pytest.mark.changes
@pytest.mark.session
@pytest.mark.parametrize('sg_conf_name, use_multiple_channels', [
    ('sync_gateway_default_functional_tests', False),
    ('sync_gateway_default_functional_tests', True)
])
def test_purge(params_from_base_test_setup, sg_conf_name, use_multiple_channels):
    """
    Scenario:
    - Bulk create 1000 docs via Sync Gateway
    - Bulk create 1000 docs via SDK
    - Get all of the docs via Sync Gateway
    - Get all of the docs via SDK
    - Sync Gateway delete 1/2 the docs, This will exercise purge on deleted and non-deleted docs
    - Sync Gateway purge all docs
    - Verify SDK can't see the docs
    - Verify SG can't see the docs
    - Verify XATTRS are gone using SDK client with full bucket permissions via subdoc?
    """

    cluster_conf = params_from_base_test_setup['cluster_config']
    cluster_topology = params_from_base_test_setup['cluster_topology']
    mode = params_from_base_test_setup['mode']
    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']

    # This test should only run when using xattr meta storage
    if not xattrs_enabled:
        pytest.skip('XATTR tests require --xattrs flag')

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_admin_url = cluster_topology['sync_gateways'][0]['admin']
    sg_url = cluster_topology['sync_gateways'][0]['public']

    bucket_name = 'data-bucket'
    cbs_url = cluster_topology['couchbase_servers'][0]
    sg_db = 'db'
    number_docs_per_client = 10
    number_revs_per_doc = 1

    if use_multiple_channels:
        log_info('Using multiple channels')
        channels = ['shared_channel_{}'.format(i) for i in range(1000)]
    else:
        log_info('Using a single channel')
        channels = ['NASA']

    log_info('sg_conf: {}'.format(sg_conf))
    log_info('sg_admin_url: {}'.format(sg_admin_url))
    log_info('sg_url: {}'.format(sg_url))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    sg_client = MobileRestClient()
    seth_user_info = UserInfo(name='seth', password='pass', channels=channels, roles=[])
    sg_client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=seth_user_info.name,
        password=seth_user_info.password,
        channels=seth_user_info.channels
    )

    seth_auth = sg_client.create_session(
        url=sg_admin_url,
        db=sg_db,
        name=seth_user_info.name,
        password=seth_user_info.password
    )

    # Create 'number_docs_per_client' docs from Sync Gateway
    seth_docs = document.create_docs('sg', number=number_docs_per_client, channels=seth_user_info.channels)
    bulk_docs_resp = sg_client.add_bulk_docs(
        url=sg_url,
        db=sg_db,
        docs=seth_docs,
        auth=seth_auth
    )
    assert len(bulk_docs_resp) == number_docs_per_client

    # Connect to server via SDK
    cbs_ip = host_for_url(cbs_url)
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password', timeout=SDK_TIMEOUT)

    # Create 'number_docs_per_client' docs from SDK
    sdk_doc_bodies = document.create_docs('sdk', number_docs_per_client, channels=seth_user_info.channels)
    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    sdk_doc_ids = [doc for doc in sdk_docs]
    sdk_client.upsert_multi(sdk_docs)

    sg_doc_ids = ['sg_{}'.format(i) for i in range(number_docs_per_client)]
    sdk_doc_ids = ['sdk_{}'.format(i) for i in range(number_docs_per_client)]
    all_doc_ids = sg_doc_ids + sdk_doc_ids

    # Get all of the docs via Sync Gateway
    sg_docs, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=all_doc_ids, auth=seth_auth)
    assert len(sg_docs) == number_docs_per_client * 2
    assert len(errors) == 0

    # Check that all of the doc ids are present in the SG response
    doc_id_scatch_pad = list(all_doc_ids)
    assert len(doc_id_scatch_pad) == number_docs_per_client * 2
    for sg_doc in sg_docs:
        log_info('Found doc through SG: {}'.format(sg_doc['_id']))
        doc_id_scatch_pad.remove(sg_doc['_id'])
    assert len(doc_id_scatch_pad) == 0

    # Get all of the docs via SDK
    sdk_docs = sdk_client.get_multi(all_doc_ids)
    assert len(sdk_docs) == number_docs_per_client * 2

    # Verify XATTRS present via SDK and SG and that they are the same
    for doc_id in all_doc_ids:
        verify_sg_xattrs(
            mode,
            sg_client,
            sg_url=sg_admin_url,
            sg_db=sg_db,
            doc_id=doc_id,
            expected_number_of_revs=number_revs_per_doc,
            expected_number_of_channels=len(channels)
        )

    # Check that all of the doc ids are present in the SDK response
    doc_id_scatch_pad = list(all_doc_ids)
    assert len(doc_id_scatch_pad) == number_docs_per_client * 2
    for sdk_doc in sdk_docs:
        log_info('Found doc through SDK: {}'.format(sdk_doc))
        doc_id_scatch_pad.remove(sdk_doc)
    assert len(doc_id_scatch_pad) == 0

    # Use Sync Gateway to delete half of the documents choosen randomly
    deletion_count = 0
    doc_id_choice_pool = list(all_doc_ids)
    deleted_doc_ids = []
    while deletion_count < number_docs_per_client:

        # Get a random doc_id from available doc ids
        random_doc_id = random.choice(doc_id_choice_pool)

        # Get the current revision of the doc and delete it
        doc = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=random_doc_id, auth=seth_auth)
        sg_client.delete_doc(url=sg_url, db=sg_db, doc_id=random_doc_id, rev=doc['_rev'], auth=seth_auth)

        # Remove deleted doc from pool of choices
        doc_id_choice_pool.remove(random_doc_id)
        deleted_doc_ids.append(random_doc_id)
        deletion_count += 1

    # Verify xattrs still exist on deleted docs
    # Expected revs will be + 1 due to the deletion revision
    for doc_id in deleted_doc_ids:
        verify_sg_xattrs(
            mode,
            sg_client,
            sg_url=sg_admin_url,
            sg_db=sg_db,
            doc_id=doc_id,
            expected_number_of_revs=number_revs_per_doc + 1,
            expected_number_of_channels=len(channels),
            deleted_docs=True
        )

    assert len(doc_id_choice_pool) == number_docs_per_client
    assert len(deleted_doc_ids) == number_docs_per_client

    # Sync Gateway purge all docs
    sg_client.purge_docs(url=sg_admin_url, db=sg_db, docs=sg_docs)

    # Verify SG can't see the docs. Bulk get should only return errors
    sg_docs_visible_after_purge, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=all_doc_ids, auth=seth_auth, validate=False)
    assert len(sg_docs_visible_after_purge) == 0
    assert len(errors) == number_docs_per_client * 2

    # Verify that all docs have been deleted
    sg_deleted_doc_scratch_pad = list(all_doc_ids)
    for error in errors:
        assert error['status'] == 404
        assert error['reason'] == 'missing'
        assert error['error'] == 'not_found'
        assert error['id'] in sg_deleted_doc_scratch_pad
        sg_deleted_doc_scratch_pad.remove(error['id'])
    assert len(sg_deleted_doc_scratch_pad) == 0

    # Verify SDK can't see the docs
    sdk_deleted_doc_scratch_pad = list(all_doc_ids)
    for doc_id in all_doc_ids:
        nfe = None
        with pytest.raises(NotFoundError) as nfe:
            sdk_client.get(doc_id)
        log_info(nfe.value)
        if nfe is not None:
            sdk_deleted_doc_scratch_pad.remove(nfe.value.key)
    assert len(sdk_deleted_doc_scratch_pad) == 0

    # Verify XATTRS are gone using SDK client with full bucket permissions via subdoc?
    for doc_id in all_doc_ids:
        verify_no_sg_xattrs(
            sg_client=sg_client,
            sg_url=sg_url,
            sg_db=sg_db,
            doc_id=doc_id
        )


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.xattrs
@pytest.mark.changes
@pytest.mark.session
@pytest.mark.parametrize('sg_conf_name', [
    'sync_gateway_default_functional_tests'
])
def test_sdk_does_not_see_sync_meta(params_from_base_test_setup, sg_conf_name):
    """
    Scenario:
    - Bulk create 1000 docs via sync gateway
    - Perform GET of docs from SDK
    - Assert that SDK does not see any sync meta data
    """

    cluster_conf = params_from_base_test_setup['cluster_config']
    cluster_topology = params_from_base_test_setup['cluster_topology']
    mode = params_from_base_test_setup['mode']
    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']

    # This test should only run when using xattr meta storage
    if not xattrs_enabled:
        pytest.skip('XATTR tests require --xattrs flag')

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_admin_url = cluster_topology['sync_gateways'][0]['admin']
    sg_url = cluster_topology['sync_gateways'][0]['public']

    bucket_name = 'data-bucket'
    cbs_url = cluster_topology['couchbase_servers'][0]
    sg_db = 'db'
    number_of_sg_docs = 1000
    channels = ['NASA']

    log_info('sg_conf: {}'.format(sg_conf))
    log_info('sg_admin_url: {}'.format(sg_admin_url))
    log_info('sg_url: {}'.format(sg_url))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    # Create sg user
    sg_client = MobileRestClient()
    sg_client.create_user(url=sg_admin_url, db=sg_db, name='seth', password='pass', channels=['shared'])
    seth_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name='seth', password='pass')

    # Connect to server via SDK
    cbs_ip = host_for_url(cbs_url)
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password', timeout=SDK_TIMEOUT)

    # Add 'number_of_sg_docs' to Sync Gateway
    sg_doc_bodies = document.create_docs(
        doc_id_prefix='sg_docs',
        number=number_of_sg_docs,
        attachments_generator=attachment.generate_2_png_100_100,
        channels=channels
    )
    sg_bulk_resp = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_doc_bodies, auth=seth_session)
    assert len(sg_bulk_resp) == number_of_sg_docs

    doc_ids = ['sg_docs_{}'.format(i) for i in range(number_of_sg_docs)]

    # Get all of the docs via the SDK
    docs_from_sg = sdk_client.get_multi(doc_ids)
    assert len(docs_from_sg) == number_of_sg_docs

    attachment_name_ids = []
    for doc_key, doc_val in docs_from_sg.items():
        # Scratch doc off in list of all doc ids
        doc_ids.remove(doc_key)

        # Get the document body
        doc_body = doc_val.value

        # Build tuple of the filename and server doc id of the attachments
        for att_key, att_val in doc_body['_attachments'].items():
            attachment_name_ids.append((att_key, '_sync:att:{}'.format(att_val['digest'])))

        # Make sure 'sync' property is not present in the document
        assert '_sync' not in doc_body

    assert len(doc_ids) == 0

    # Verify attachments stored locally have the same data as those written to the server
    for att_file_name, att_doc_id in attachment_name_ids:

        att_doc = sdk_client.get(att_doc_id, no_format=True)
        att_bytes = att_doc.value

        local_file_path = '{}/{}'.format(DATA_DIR, att_file_name)
        log_info('Checking that the generated attachment is the same that is store on server: {}'.format(
            local_file_path
        ))
        with open(local_file_path, 'rb') as local_file:
            local_bytes = local_file.read()
            assert att_bytes == local_bytes


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.xattrs
@pytest.mark.changes
@pytest.mark.session
@pytest.mark.parametrize('sg_conf_name', [
    'sync_gateway_default_functional_tests'
])
def test_sg_sdk_interop_unique_docs(params_from_base_test_setup, sg_conf_name):

    """
    Scenario:
    - Bulk create 'number_docs' docs from SDK with id prefix 'sdk' and channels ['sdk']
    - Bulk create 'number_docs' docs from SG with id prefix 'sg' and channels ['sg']
    - SDK: Verify docs (sg + sdk) are present
    - SG: Verify docs (sg + sdk) are there via _all_docs
    - SG: Verify docs (sg + sdk) are there via _changes
    - Bulk update each doc 'number_updates' from SDK for 'sdk' docs
    - SDK should verify it does not see _sync
    - Bulk update each doc 'number_updates' from SG for 'sg' docs
    - SDK: Verify doc updates (sg + sdk) are present using the doc['content']['updates'] property
    - SG: Verify doc updates (sg + sdk) are there via _all_docs using the doc['content']['updates'] property and rev prefix
    - SG: Verify doc updates (sg + sdk) are there via _changes using the doc['content']['updates'] property and rev prefix
    - SDK should verify it does not see _sync
    - Bulk delete 'sdk' docs from SDK
    - Bulk delete 'sg' docs from SG
    - Verify SDK sees all docs (sg + sdk) as deleted
    - Verify SG sees all docs (sg + sdk) as deleted
    """

    cluster_conf = params_from_base_test_setup['cluster_config']
    cluster_topology = params_from_base_test_setup['cluster_topology']
    mode = params_from_base_test_setup['mode']
    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']

    # This test should only run when using xattr meta storage
    if not xattrs_enabled:
        pytest.skip('XATTR tests require --xattrs flag')

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_admin_url = cluster_topology['sync_gateways'][0]['admin']
    sg_url = cluster_topology['sync_gateways'][0]['public']

    bucket_name = 'data-bucket'
    cbs_url = cluster_topology['couchbase_servers'][0]
    sg_db = 'db'
    number_docs_per_client = 10
    number_updates = 10

    log_info('sg_conf: {}'.format(sg_conf))
    log_info('sg_admin_url: {}'.format(sg_admin_url))
    log_info('sg_url: {}'.format(sg_url))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    # Connect to server via SDK
    log_info('Connecting to bucket ...')
    cbs_ip = host_for_url(cbs_url)
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password', timeout=SDK_TIMEOUT)

    # Create docs and add them via sdk
    log_info('Adding docs via sdk ...')
    sdk_doc_bodies = document.create_docs('sdk', number_docs_per_client, content={'foo': 'bar', 'updates': 1}, channels=['sdk'])
    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    sdk_doc_ids = [doc for doc in sdk_docs]
    sdk_client.upsert_multi(sdk_docs)

    # Create sg user
    log_info('Creating user / session on Sync Gateway ...')
    sg_client = MobileRestClient()
    sg_client.create_user(url=sg_admin_url, db=sg_db, name='seth', password='pass', channels=['sg', 'sdk'])
    seth_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name='seth', password='pass')

    # Create / add docs to sync gateway
    log_info('Adding docs Sync Gateway ...')
    sg_docs = document.create_docs('sg', number_docs_per_client, content={'foo': 'bar', 'updates': 1}, channels=['sg'])
    log_info('Adding bulk_docs')
    sg_docs_resp = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs, auth=seth_session)
    sg_doc_ids = [doc['_id'] for doc in sg_docs]
    assert len(sg_docs_resp) == number_docs_per_client

    all_doc_ids = sdk_doc_ids + sg_doc_ids

    # Verify docs all docs are present via SG _bulk_get
    log_info('Verify Sync Gateway sees all docs via _bulk_get ...')
    all_docs_via_sg, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=all_doc_ids, auth=seth_session)
    assert len(all_docs_via_sg) == number_docs_per_client * 2
    assert len(errors) == 0
    verify_doc_ids_in_sg_bulk_response(all_docs_via_sg, number_docs_per_client * 2, all_doc_ids)

    # Verify docs all docs are present via SG _all_docs
    log_info('Verify Sync Gateway sees all docs via _all_docs ...')
    all_docs_resp = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=seth_session)
    verify_doc_ids_in_sg_all_docs_response(all_docs_resp, number_docs_per_client * 2, all_doc_ids)

    # Verify docs all docs are present via SDK get_multi
    log_info('Verify SDK sees all docs via get_multi ...')
    all_docs_via_sdk = sdk_client.get_multi(all_doc_ids)
    verify_doc_ids_in_sdk_get_multi(all_docs_via_sdk, number_docs_per_client * 2, all_doc_ids)

    # SG: Verify docs (sg + sdk) are there via _changes
    # Format docs for changes verification
    log_info('Verify Sync Gateway sees all docs on _changes ...')
    all_docs_via_sg_formatted = [{"id": doc["_id"], "rev": doc["_rev"]} for doc in all_docs_via_sg]
    assert len(all_docs_via_sg_formatted) == number_docs_per_client * 2
    sg_client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=all_docs_via_sg_formatted, auth=seth_session)

    log_info("Sync Gateway updates 'sg_*' docs and SDK updates 'sdk_*' docs ...")
    for i in range(number_updates):

        # Get docs and extract doc_id (key) and doc_body (value.value)
        sdk_docs_resp = sdk_client.get_multi(sdk_doc_ids)
        docs = {k: v.value for k, v in sdk_docs_resp.items()}

        # update the updates property for every doc
        for _, v in docs.items():
            v['content']['updates'] += 1

        # Push the updated batch to Couchbase Server
        sdk_client.upsert_multi(docs)

        # Get docs from Sync Gateway
        sg_docs_to_update, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=sg_doc_ids, auth=seth_session)
        assert len(sg_docs_to_update) == number_docs_per_client
        assert len(errors) == 0

        # Update the docs
        for sg_doc in sg_docs_to_update:
            sg_doc['content']['updates'] += 1

        # Bulk add the updates to Sync Gateway
        sg_docs_resp = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs_to_update, auth=seth_session)

    # Verify updates from SG via _bulk_get
    log_info('Verify Sync Gateway sees all docs via _bulk_get ...')
    docs_from_sg_bulk_get, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=all_doc_ids, auth=seth_session)
    assert len(docs_from_sg_bulk_get) == number_docs_per_client * 2
    assert len(errors) == 0
    for doc in docs_from_sg_bulk_get:
        # If it is an SG doc the revision prefix should match the number of updates.
        # This may not be the case due to batched importing of SDK updates
        if doc['_id'].startswith('sg_'):
            assert doc['_rev'].startswith('{}-'.format(number_updates + 1))
        assert doc['content']['updates'] == number_updates + 1

    # Verify updates from SG via _all_docs
    log_info('Verify Sync Gateway sees updates via _all_docs ...')
    docs_from_sg_all_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=seth_session, include_docs=True)
    assert len(docs_from_sg_all_docs['rows']) == number_docs_per_client * 2
    for doc in docs_from_sg_all_docs['rows']:
        # If it is an SG doc the revision prefix should match the number of updates.
        # This may not be the case due to batched importing of SDK updates
        if doc['id'].startswith('sg_'):
            assert doc['value']['rev'].startswith('{}-'.format(number_updates + 1))
            assert doc['doc']['_rev'].startswith('{}-'.format(number_updates + 1))

        assert doc['id'] == doc['doc']['_id']
        assert doc['doc']['content']['updates'] == number_updates + 1

    # Verify updates from SG via _changes
    log_info('Verify Sync Gateway sees updates on _changes ...')
    all_docs_via_sg_formatted = [{"id": doc["_id"], "rev": doc["_rev"]} for doc in docs_from_sg_bulk_get]
    sg_client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=all_docs_via_sg_formatted, auth=seth_session)

    # Verify updates from SDK via get_multi
    log_info('Verify SDK sees updates via get_multi ...')
    all_docs_from_sdk = sdk_client.get_multi(all_doc_ids)
    assert len(all_docs_from_sdk) == number_docs_per_client * 2
    for doc_id, value in all_docs_from_sdk.items():
        assert '_sync' not in value.value
        assert value.value['content']['updates'] == number_updates + 1

    # Delete the sync gateway docs
    log_info("Deleting 'sg_*' docs from Sync Gateway  ...")
    sg_docs_to_delete, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=sg_doc_ids, auth=seth_session)
    assert len(sg_docs_to_delete) == number_docs_per_client
    assert len(errors) == 0

    sg_docs_delete_resp = sg_client.delete_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs_to_delete, auth=seth_session)
    assert len(sg_docs_delete_resp) == number_docs_per_client

    # Delete the sdk docs
    log_info("Deleting 'sdk_*' docs from SDK  ...")
    sdk_client.remove_multi(sdk_doc_ids)

    # Verify all docs are deleted on the sync_gateway side
    all_doc_ids = sdk_doc_ids + sg_doc_ids
    assert len(all_doc_ids) == 2 * number_docs_per_client

    # Check deletes via GET /db/doc_id and bulk_get
    verify_sg_deletes(client=sg_client, url=sg_url, db=sg_db, docs_to_verify_deleted=all_doc_ids, auth=seth_session)

    # Verify all docs are deleted on sdk, deleted docs should rase and exception
    sdk_doc_delete_scratch_pad = list(all_doc_ids)
    for doc_id in all_doc_ids:
        nfe = None
        with pytest.raises(NotFoundError) as nfe:
            sdk_client.get(doc_id)
        log_info(nfe.value)
        if nfe is not None:
            sdk_doc_delete_scratch_pad.remove(nfe.value.key)

    # Assert that all of the docs are flagged as deleted
    assert len(sdk_doc_delete_scratch_pad) == 0


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.xattrs
@pytest.mark.changes
@pytest.mark.session
@pytest.mark.parametrize(
    'sg_conf_name, number_docs_per_client, number_updates_per_doc_per_client',
    [
        ('sync_gateway_default_functional_tests', 10, 10),
        ('sync_gateway_default_functional_tests', 100, 10),
        ('sync_gateway_default_functional_tests', 10, 100),
        ('sync_gateway_default_functional_tests', 1, 1000)
    ]
)
def test_sg_sdk_interop_shared_docs(params_from_base_test_setup,
                                    sg_conf_name,
                                    number_docs_per_client,
                                    number_updates_per_doc_per_client):
    """
    Scenario:
    - Bulk create 'number_docs' docs from SDK with prefix 'doc_set_one' and channels ['shared']
      with 'sg_one_updates' and 'sdk_one_updates' counter properties
    - Bulk create 'number_docs' docs from SG with prefix 'doc_set_two' and channels ['shared']
      with 'sg_one_updates' and 'sdk_one_updates' counter properties
    - SDK: Verify docs (sg + sdk) are present
    - SG: Verify docs (sg + sdk) are there via _all_docs
    - SG: Verify docs (sg + sdk) are there via _changes
    - Start concurrent updates:
        - Start update from sg / sdk to a shared set of docs. Sync Gateway and SDK will try to update
          random docs from the shared set and update the corresponding counter property as well as the
          'updates' properties
    - SDK: Verify doc updates (sg + sdk) are present using the counter properties
    - SG: Verify doc updates (sg + sdk) are there via _changes using the counter properties and rev prefix
    - Start concurrent deletes:
        loop until len(all_doc_ids_to_delete) == 0
            - List of all_doc_ids_to_delete
            - Pick random doc and try to delete from sdk
            - If successful, remove from list
            - Pick random doc and try to delete from sg
            - If successful, remove from list
    - Verify SDK sees all docs (sg + sdk) as deleted
    - Verify SG sees all docs (sg + sdk) as deleted
    """

    cluster_conf = params_from_base_test_setup['cluster_config']
    cluster_topology = params_from_base_test_setup['cluster_topology']
    mode = params_from_base_test_setup['mode']
    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']

    # This test should only run when using xattr meta storage
    if not xattrs_enabled:
        pytest.skip('XATTR tests require --xattrs flag')

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_admin_url = cluster_topology['sync_gateways'][0]['admin']
    sg_url = cluster_topology['sync_gateways'][0]['public']

    bucket_name = 'data-bucket'
    cbs_url = cluster_topology['couchbase_servers'][0]
    sg_db = 'db'

    log_info('Num docs per client: {}'.format(number_docs_per_client))
    log_info('Num updates per doc per client: {}'.format(number_updates_per_doc_per_client))

    log_info('sg_conf: {}'.format(sg_conf))
    log_info('sg_admin_url: {}'.format(sg_admin_url))
    log_info('sg_url: {}'.format(sg_url))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    sg_tracking_prop = 'sg_one_updates'
    sdk_tracking_prop = 'sdk_one_updates'

    # Create sg user
    sg_client = MobileRestClient()
    sg_client.create_user(url=sg_admin_url, db=sg_db, name='seth', password='pass', channels=['shared'])
    seth_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name='seth', password='pass')

    # Connect to server via SDK
    cbs_ip = host_for_url(cbs_url)
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password', timeout=SDK_TIMEOUT)

    # Inject custom properties into doc template
    def update_props():
        return {
            'updates': 0,
            sg_tracking_prop: 0,
            sdk_tracking_prop: 0
        }

    # Create / add docs to sync gateway
    sg_docs = document.create_docs(
        'doc_set_one',
        number_docs_per_client,
        channels=['shared'],
        prop_generator=update_props
    )
    sg_docs_resp = sg_client.add_bulk_docs(
        url=sg_url,
        db=sg_db,
        docs=sg_docs,
        auth=seth_session
    )
    doc_set_one_ids = [doc['_id'] for doc in sg_docs]
    assert len(sg_docs_resp) == number_docs_per_client

    # Create / add docs via sdk
    sdk_doc_bodies = document.create_docs(
        'doc_set_two',
        number_docs_per_client,
        channels=['shared'],
        prop_generator=update_props
    )

    # Add docs via SDK
    log_info('Adding {} docs via SDK ...'.format(number_docs_per_client))
    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    doc_set_two_ids = [sdk_doc['_id'] for sdk_doc in sdk_doc_bodies]
    sdk_docs_resp = sdk_client.upsert_multi(sdk_docs)
    assert len(sdk_docs_resp) == number_docs_per_client

    # Build list of all doc_ids
    all_docs_ids = doc_set_one_ids + doc_set_two_ids
    assert len(all_docs_ids) == number_docs_per_client * 2

    # Verify docs (sg + sdk) via SG bulk_get
    docs_from_sg_bulk_get, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=all_docs_ids, auth=seth_session)
    assert len(docs_from_sg_bulk_get) == number_docs_per_client * 2
    assert len(errors) == 0
    verify_doc_ids_in_sg_bulk_response(docs_from_sg_bulk_get, number_docs_per_client * 2, all_docs_ids)

    # Verify docs (sg + sdk) are there via _all_docs
    all_docs_resp = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=seth_session)
    assert len(all_docs_resp["rows"]) == number_docs_per_client * 2
    verify_doc_ids_in_sg_all_docs_response(all_docs_resp, number_docs_per_client * 2, all_docs_ids)

    # SG: Verify docs (sg + sdk) are there via _changes
    all_docs_via_sg_formatted = [{"id": doc["_id"], "rev": doc["_rev"]} for doc in docs_from_sg_bulk_get]
    sg_client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=all_docs_via_sg_formatted, auth=seth_session)

    # SDK: Verify docs (sg + sdk) are present
    all_docs_via_sdk = sdk_client.get_multi(all_docs_ids)
    verify_doc_ids_in_sdk_get_multi(all_docs_via_sdk, number_docs_per_client * 2, all_docs_ids)

    # Build a dictionary of all the doc ids with default number of updates (1 for created)
    all_doc_ids = doc_set_one_ids + doc_set_two_ids
    assert len(all_doc_ids) == number_docs_per_client * 2

    # Update the same documents concurrently from a sync gateway client and and sdk client
    with ThreadPoolExecutor(max_workers=5) as tpe:
        update_from_sg_task = tpe.submit(
            update_sg_docs,
            client=sg_client,
            url=sg_url,
            db=sg_db,
            docs_to_update=all_doc_ids,
            prop_to_update=sg_tracking_prop,
            number_updates=number_updates_per_doc_per_client,
            auth=seth_session
        )

        update_from_sdk_task = tpe.submit(
            update_sdk_docs,
            client=sdk_client,
            docs_to_update=all_doc_ids,
            prop_to_update=sdk_tracking_prop,
            number_updates=number_updates_per_doc_per_client
        )

        # Make sure to block on the result to catch any exceptions that may have been thrown
        # during execution of the future
        update_from_sg_task.result()
        update_from_sdk_task.result()

    # Issue a bulk_get to make sure all docs have auto imported
    docs_from_sg_bulk_get, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=all_doc_ids, auth=seth_session)
    assert len(docs_from_sg_bulk_get) == number_docs_per_client * 2
    assert len(errors) == 0

    # Issue _changes
    docs_from_sg_bulk_get_formatted = [{"id": doc["_id"], "rev": doc["_rev"]} for doc in docs_from_sg_bulk_get]
    assert len(docs_from_sg_bulk_get_formatted) == number_docs_per_client * 2
    sg_client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=docs_from_sg_bulk_get_formatted, auth=seth_session)

    # Get all of the docs and verify that all updates we applied
    log_info('Verifying that all docs have the expected number of updates.')
    for doc_id in all_doc_ids:

        # Get doc from SDK
        doc_result = sdk_client.get(doc_id)
        doc_body = doc_result.value

        log_info('doc: {} -> {}:{}, {}:{}'.format(
            doc_id,
            sg_tracking_prop, doc_body[sg_tracking_prop],
            sdk_tracking_prop, doc_body[sdk_tracking_prop],
        ))

        assert doc_body['updates'] == number_updates_per_doc_per_client * 2
        assert doc_body[sg_tracking_prop] == number_updates_per_doc_per_client
        assert doc_body[sdk_tracking_prop] == number_updates_per_doc_per_client

        # Get doc from Sync Gateway
        doc = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id, auth=seth_session)

        assert doc['updates'] == number_updates_per_doc_per_client * 2
        assert doc[sg_tracking_prop] == number_updates_per_doc_per_client
        assert doc[sdk_tracking_prop] == number_updates_per_doc_per_client

        # We cant be sure deterministically due to batched import from SDK updates
        # so make sure it has been update past initial write
        assert int(doc['_rev'].split('-')[0]) > 1
        assert len(doc['_revisions']['ids']) > 1

    # Try concurrent deletes from either side
    with ThreadPoolExecutor(max_workers=5) as tpe:

        sdk_delete_task = tpe.submit(
            delete_sdk_docs,
            client=sdk_client,
            docs_to_delete=all_doc_ids
        )

        sg_delete_task = tpe.submit(
            delete_sg_docs,
            client=sg_client,
            url=sg_url,
            db=sg_db,
            docs_to_delete=all_doc_ids,
            auth=seth_session
        )

        # Make sure to block on the result to catch any exceptions that may have been thrown
        # during execution of the future
        sdk_delete_task.result()
        sg_delete_task.result()

    assert len(all_doc_ids) == number_docs_per_client * 2

    # Verify all docs deleted from SG context
    verify_sg_deletes(client=sg_client, url=sg_url, db=sg_db, docs_to_verify_deleted=all_doc_ids, auth=seth_session)

    # Verify all docs deleted from SDK context
    verify_sdk_deletes(sdk_client, all_doc_ids)


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.xattrs
@pytest.mark.changes
@pytest.mark.session
@pytest.mark.parametrize(
    'sg_conf_name, number_docs_per_client, number_updates_per_doc_per_client',
    [
        ('sync_gateway_default_functional_tests', 10, 10),
        ('sync_gateway_default_functional_tests', 100, 10),
        ('sync_gateway_default_functional_tests', 10, 100),
        ('sync_gateway_default_functional_tests', 1, 1000)
    ]
)
def test_sg_feed_changed_with_xattrs_importEnabled(params_from_base_test_setup,
                                                   sg_conf_name,
                                                   number_docs_per_client,
                                                   number_updates_per_doc_per_client):
    """
    Scenario:
    - Start sync-gateway with Xattrs and import enabled
    - start listening to changes
    - Create docs via SDK
    - Verify docs via ChangesTracker with rev generation 1-
    - update docs via SDK
    - Verify docs via ChangesTracker with rev generation 2-
    - update SDK docs via SG
    - Verify docs via ChangesTracker with expected revision
    - Create docs via SG
    - Verify docs via ChangesTracker with expected revision
    - update docs via SG
    - Verify docs via ChangesTracker with expected revision
    - update SG docs via SDK
    - Verify docs via ChangesTracker with rev generation 3-
   """
    cluster_conf = params_from_base_test_setup['cluster_config']
    cluster_topology = params_from_base_test_setup['cluster_topology']
    mode = params_from_base_test_setup['mode']
    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']

    # This test should only run when using xattr meta storage
    if not xattrs_enabled:
        pytest.skip('XATTR tests require --xattrs flag')

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_admin_url = cluster_topology['sync_gateways'][0]['admin']
    sg_url = cluster_topology['sync_gateways'][0]['public']

    bucket_name = 'data-bucket'
    cbs_url = cluster_topology['couchbase_servers'][0]
    sg_db = 'db'
    changesTracktimeout = 60

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    sg_client = MobileRestClient()
    sg_client.create_user(url=sg_admin_url, db=sg_db, name='autosdkuser', password='pass', channels=['shared'])
    autosdkuser_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name='autosdkuser', password='pass')

    sg_client.create_user(url=sg_admin_url, db=sg_db, name='autosguser', password='pass', channels=['sg-shared'])
    autosguser_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name='autosguser', password='pass')

    log_info('Num docs per client: {}'.format(number_docs_per_client))
    log_info('Num updates per doc per client: {}'.format(number_updates_per_doc_per_client))

    log_info('sg_conf: {}'.format(sg_conf))
    log_info('sg_admin_url: {}'.format(sg_admin_url))
    log_info('sg_url: {}'.format(sg_url))

    sg_tracking_prop = 'sg_one_updates'
    sdk_tracking_prop = 'sdk_one_updates'

    # Start listening to changes feed
    changestrack = ChangesTracker(sg_url, sg_db, auth=autosdkuser_session)
    changestrack_sg = ChangesTracker(sg_url, sg_db, auth=autosguser_session)
    cbs_ip = host_for_url(cbs_url)

    # Connect to server via SDK
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password', timeout=SDK_TIMEOUT)

    # Inject custom properties into doc template
    def update_props():
        return {
            'updates': 0,
            sg_tracking_prop: 0,
            sdk_tracking_prop: 0
        }

    # Create / add docs via sdk
    sdk_doc_bodies = document.create_docs(
        'doc_sdk_ids',
        number_docs_per_client,
        channels=['shared'],
        prop_generator=update_props
    )

    with ThreadPoolExecutor(max_workers=5) as crsdk_tpe:

        # Add docs via SDK
        log_info('Started adding {} docs via SDK ...'.format(number_docs_per_client))
        sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
        doc_set_ids1 = [sdk_doc['_id'] for sdk_doc in sdk_doc_bodies]
        sdk_docs_resp = sdk_client.upsert_multi(sdk_docs)
        assert len(sdk_docs_resp) == number_docs_per_client
        assert len(doc_set_ids1) == number_docs_per_client
        log_info("Docs creation via SDK done")
        all_docs_via_sg_formatted = [
            {"id": doc, "rev": "1-"} for doc in doc_set_ids1]

        ct_task = crsdk_tpe.submit(changestrack.start(timeout=10000))
        log_info("ct_task value {}".format(ct_task))
        wait_for_changes = crsdk_tpe.submit(
            changestrack.wait_until, all_docs_via_sg_formatted, rev_prefix_gen=True)

        if wait_for_changes.result():
            log_info("Found all docs ...")
        else:
            raise NotFoundError(
                "Could not find all changes in feed for adding docs via SDK before timeout!!")

    with ThreadPoolExecutor(max_workers=5) as upsdk_tpe:
        log_info("Updating docs via SDK...")

        # Update docs via SDK
        sdk_docs = sdk_client.get_multi(doc_set_ids1)
        assert len(sdk_docs.keys()) == number_docs_per_client
        for doc_id, val in sdk_docs.items():
            doc_body = val.value
            doc_body["updated_by_sdk"] = True
            sdk_client.upsert(doc_id, doc_body)
        # Retry to get changes until expected changes appeared
        start = time.time()
        while True:
            if time.time() - start > changesTracktimeout:
                break
            try:
                ct_task = upsdk_tpe.submit(changestrack.start(timeout=15000))
                break
            except ChangesError:
                continue
        all_docs_via_sg_formatted = [
            {"id": doc, "rev": "2-"} for doc in doc_set_ids1]

        wait_for_changes = upsdk_tpe.submit(
            changestrack.wait_until, all_docs_via_sg_formatted, rev_prefix_gen=True)

        if wait_for_changes.result():
            log_info("Found all docs after SDK update ...")
        else:
            raise NotFoundError(
                "Could not find all changes in feed for SDK updated SDK docs before timeout!!")

    # update docs by sync-gateway
    with ThreadPoolExecutor(max_workers=5) as upsdksg_tpe:
        log_info("Starting updating SDK docs by sync-gateway...")
        user_docs, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=sdk_docs, auth=autosdkuser_session)
        assert len(errors) == 0

        # Update the 'updates' property
        for doc in user_docs:
            doc['updated_by_sg'] = True

        # Add the bulk docs via sync-gateway
        sg_docs_update_resp = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=user_docs, auth=autosdkuser_session)
        # Retry to get changes until expected changes appeared
        start = time.time()
        while True:
            if time.time() - start > changesTracktimeout:
                break
            try:
                ct_task = upsdksg_tpe.submit(changestrack.start(timeout=15000))
                break
            except ChangesError:
                continue
        wait_for_changes = upsdksg_tpe.submit(
            changestrack.wait_until, sg_docs_update_resp)

        if wait_for_changes.result():
            log_info("Stopping ...")
            log_info("Found all docs for update docs via sg ...")
            upsdksg_tpe.submit(changestrack.stop)
        else:
            upsdksg_tpe.submit(changestrack.stop)
            raise NotFoundError(
                "Could not find all changes in feed for SG updated SDK docs via sg before timeout!!")

    with ThreadPoolExecutor(max_workers=5) as crsg_tpe:
        log_info("Starting adding docs via sync-gateway...")

        # Create / add docs to sync gateway
        sg_docs = document.create_docs(
            'doc_sg_id',
            number_docs_per_client,
            channels=['sg-shared'],
            prop_generator=update_props
        )
        sg_docs_resp = sg_client.add_bulk_docs(
            url=sg_url,
            db=sg_db,
            docs=sg_docs,
            auth=autosguser_session
        )
        assert len(sg_docs_resp) == number_docs_per_client
        sg_docs = [doc['id'] for doc in sg_docs_resp]
        assert len(sg_docs) == number_docs_per_client
        # Retry to get changes until expected changes appeared
        start = time.time()
        while True:
            if time.time() - start > changesTracktimeout:
                break
            try:
                ct_task = crsg_tpe.submit(changestrack_sg.start(timeout=15000))
                break
            except ChangesError:
                continue
        wait_for_changes = crsg_tpe.submit(
            changestrack_sg.wait_until, sg_docs_resp)

        if wait_for_changes.result():
            log_info("Found all docs ...")
        else:
            raise NotFoundError(
                "Could not find all changes in feed for sg created docs before timeout!!")

    # update docs by sync-gateway
    with ThreadPoolExecutor(max_workers=5) as upsg_tpe:
        log_info("Starting updating sg docs by sync-gateway...")
        user_docs, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=sg_docs, auth=autosguser_session)
        assert len(errors) == 0

        # Update the 'updates' property
        for doc in user_docs:
            doc['updated_by_sg'] = "edits_1"

        # Add the docs via bulk_docs
        sg_docs_update_resp = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=user_docs, auth=autosguser_session)
        # Retry to get changes until expected changes appeared
        start = time.time()
        while True:
            if time.time() - start > changesTracktimeout:
                break
            try:
                ct_task = upsg_tpe.submit(changestrack_sg.start(timeout=15000))
                break
            except ChangesError:
                continue
        wait_for_changes = upsg_tpe.submit(
            changestrack_sg.wait_until, sg_docs_update_resp)

        if wait_for_changes.result():
            log_info("Found all sg docs for update docs via sg ...")
        else:
            raise NotFoundError(
                "Could not find all changes in feed for update sg docs via sg before timeout!!")

    # Update sg docs via SDK
    with ThreadPoolExecutor(max_workers=5) as upsgsdk_tpe:
        log_info("Updating sg docs via SDK...")

        sdk_docs = sdk_client.get_multi(sg_docs)
        assert len(sdk_docs.keys()) == number_docs_per_client
        for doc_id, val in sdk_docs.items():
            doc_body = val.value
            doc_body["updated_by_sdk"] = True
            sdk_client.upsert(doc_id, doc_body)
        # Retry to get changes until expected changes appeared
        start = time.time()
        while True:
            if time.time() - start > changesTracktimeout:
                break
            try:
                ct_task = upsgsdk_tpe.submit(changestrack_sg.start(timeout=15000))
                break
            except ChangesError:
                continue
        all_docs_via_sg_formatted = [
            {"id": doc, "rev": "3-"} for doc in sg_docs]

        wait_for_changes = upsgsdk_tpe.submit(changestrack_sg.wait_until, all_docs_via_sg_formatted, rev_prefix_gen=True)

        if wait_for_changes.result():
            log_info("Stopping sg changes track...")
            log_info("Found all sg docs after SDK update ...")
            upsgsdk_tpe.submit(changestrack_sg.stop)
        else:
            upsgsdk_tpe.submit(changestrack_sg.stop)
            raise NotFoundError(
                "Could not find all changes in feed for SDK updated sg docs before timeout!!")


def update_sg_docs(client, url, db, docs_to_update, prop_to_update, number_updates, auth=None):
    """
    1. Check if document has already been updated 'number_updates'
    1. Get random doc id from 'docs_to_update'
    2. Update the doc
    3. Check to see if it has been updated 'number_updates'
    4. If it has been updated the correct number of times, delete it from the the list
    """

    log_info("Client: {}".format(id(client)))

    # Store copy of list to avoid mutating 'docs_to_update'
    local_docs_to_update = list(docs_to_update)

    # 'docs_to_update' is a list of doc ids that the client should update a number of times
    # Once the doc has been updated the correct number of times, it will be removed from the list.
    # Loop until all docs have been removed
    while len(local_docs_to_update) > 0:
        random_doc_id = random.choice(local_docs_to_update)
        doc = client.get_doc(url=url, db=db, doc_id=random_doc_id, auth=auth)

        # Create property updater to modify custom property
        def property_updater(doc_body):
            doc_body[prop_to_update] += 1
            return doc_body

        # Remove doc from the list if the doc has been updated enough times
        if doc[prop_to_update] == number_updates:
            local_docs_to_update.remove(doc["_id"])
        else:
            # Update the doc
            try:
                log_info('Updating: {} from SG'.format(random_doc_id))
                client.update_doc(url=url, db=db, doc_id=random_doc_id, property_updater=property_updater, auth=auth)
            except HTTPError as e:
                # This is possible if hitting a conflict. Check that it is. If it is not, we want to raise
                if not is_conflict(e):
                    raise
                else:
                    log_info('Hit a conflict! Will retry later ...')

        # SDK and sync gateway do not operate at the same speed.
        # This will help normalize the rate
        time.sleep(SG_OP_SLEEP)


def is_conflict(httperror):
    if httperror.response.status_code == 409 \
            and httperror.message.startswith('409 Client Error: Conflict for url:'):
        return True
    else:
        return False


def update_sdk_docs(client, docs_to_update, prop_to_update, number_updates):
    """ This will update a set of docs (docs_to_update)
    by updating a property (prop_to_update) using CAS safe writes.
    It will continue to update the set of docs until all docs have
    been updated a number of times (number_updates).
    """

    log_info("Client: {}".format(id(client)))

    # Store copy of list to avoid mutating 'docs_to_update'
    local_docs_to_update = list(docs_to_update)

    while len(local_docs_to_update) > 0:
        random_doc_id = random.choice(local_docs_to_update)
        log_info(random_doc_id)

        doc = client.get(random_doc_id)
        doc_body = doc.value

        # Make sure not meta is seen
        assert '_sync' not in doc_body

        if doc_body[prop_to_update] == number_updates:
            local_docs_to_update.remove(random_doc_id)
        else:
            try:
                # Do a CAS safe write. It is possible that the document is updated
                # by Sync Gateway between the client.get and the client.upsert.
                # If this happens, catch the CAS error and retry
                doc_body[prop_to_update] += 1
                doc_body['updates'] += 1
                log_info('Updating: {} from SDK'.format(random_doc_id))
                cur_cas = doc.cas
                client.upsert(random_doc_id, doc_body, cas=cur_cas)
            except KeyExistsError:
                log_info('CAS mismatch from SDK. Will retry ...')

        # SDK and sync gateway do not operate at the same speed.
        # This will help normalize the rate
        time.sleep(SDK_OP_SLEEP)


def delete_sg_docs(client, url, db, docs_to_delete, auth):
    """ This will attempt to delete a document via Sync Gateway. This method is meant to be
    run concurrently with delete_sdk_docs so the deletions have to handle external deletions
    as well.
    """

    deleted_count = 0

    # Create a copy of all doc ids
    docs_to_remove = list(docs_to_delete)
    while len(docs_to_remove) > 0:
        random_doc_id = random.choice(docs_to_remove)
        log_info('Attempting to delete from SG: {}'.format(random_doc_id))
        try:
            doc_to_delete = client.get_doc(url=url, db=db, doc_id=random_doc_id, auth=auth)
            deleted_doc = client.delete_doc(url=url, db=db, doc_id=random_doc_id, rev=doc_to_delete['_rev'], auth=auth)
            docs_to_remove.remove(deleted_doc['id'])
            deleted_count += 1
        except HTTPError as he:
            if he.response.status_code == 403 and str(he).startswith('403 Client Error: Forbidden for url:'):
                # Doc may have been deleted by the SDK and GET fails for SG
                log_info('Could not find doc, must have been deleted by SDK. Retrying ...')
                docs_to_remove.remove(random_doc_id)
            elif he.response.status_code == 409 and str(he).startswith('409 Client Error: Conflict for url:'):
                # This can happen in the following scenario:
                # During concurrent deletes from SG and SDK,
                #  1. SG GETs doc 'a' with rev '2'
                #  2. SDK deletes doc 'a' with rev '2' before
                #  3. SG tries to DELETE doc 'a' with rev '2' and GET a conflict
                log_info('Could not find doc, must have been deleted by SDK. Retrying ...')
                docs_to_remove.remove(random_doc_id)
            else:
                raise he

        # SDK and sync gateway do not operate at the same speed.
        # This will help normalize the rate
        time.sleep(SG_OP_SLEEP)

    # If the scenario is the one doc per client, it is possible that the SDK may delete both docs
    # before Sync Gateway has a chance to delete one. Only assert when we have enought docs to
    # ensure both sides get a chances to delete
    if len(docs_to_delete) > 2:
        assert deleted_count > 0


def delete_sdk_docs(client, docs_to_delete):
    """ This will attempt to delete a document via Couchbase Server Python SDK. This method is meant to be
    run concurrently with delete_sg_docs so the deletions have to handle external deletions by Sync Gateway.
    """

    deleted_count = 0

    # Create a copy of all doc ids
    docs_to_remove = list(docs_to_delete)
    while len(docs_to_remove) > 0:
        random_doc_id = random.choice(docs_to_remove)
        log_info('Attempting to delete from SDK: {}'.format(random_doc_id))
        try:
            doc = client.remove(random_doc_id)
            print(doc.key)
            docs_to_remove.remove(doc.key)
            deleted_count += 1
        except NotFoundError:
            # Doc may have been deleted by sync gateway
            log_info('Could not find doc, must have been deleted by SG. Retrying ...')
            docs_to_remove.remove(random_doc_id)

        # SDK and sync gateway do not operate at the same speed.
        # This will help normalize the rate
        time.sleep(SDK_OP_SLEEP)

    # If the scenario is the one doc per client, it is possible that the SDK may delete both docs
    # before Sync Gateway has a chance to delete one. Only assert when we have enought docs to
    # ensure both sides get a chances to delete
    if len(docs_to_delete) > 2:
        assert deleted_count > 0


def verify_sg_deletes(client, url, db, docs_to_verify_deleted, auth):
    """ Verify that documents have been deleted via Sync Gateway GET's.
    - Verify the expected result is returned via GET doc
    - Verify the expected result is returned via GET _bulk_get
    """

    docs_to_verify_scratchpad = list(docs_to_verify_deleted)

    # Verify deletes via individual GETs
    for doc_id in docs_to_verify_deleted:
        he = None
        with pytest.raises(HTTPError) as he:
            client.get_doc(url=url, db=db, doc_id=doc_id, auth=auth)

        assert he is not None
        log_info(he.value.message)

        assert he.value.message.startswith('404 Client Error: Not Found for url:') or \
            he.value.message.startswith('403 Client Error: Forbidden for url:')

        # Parse out the doc id
        # sg_0?conflicts=true&revs=true
        parts = he.value.message.split('/')[-1]
        doc_id_from_parts = parts.split('?')[0]

        # Remove the doc id from the list
        docs_to_verify_scratchpad.remove(doc_id_from_parts)

    assert len(docs_to_verify_scratchpad) == 0

    # Create a new verify list
    docs_to_verify_scratchpad = list(docs_to_verify_deleted)

    # Verify deletes via bulk_get
    try_get_bulk_docs, errors = client.get_bulk_docs(url=url, db=db, doc_ids=docs_to_verify_deleted, auth=auth, validate=False)
    assert len(try_get_bulk_docs) == 0
    assert len(errors) == len(docs_to_verify_deleted)

    # Verify each deletion
    for err in errors:
        status = err['status']
        assert status in [403, 404]
        if status == 403:
            assert err['error'] == 'forbidden'
            assert err['reason'] == 'forbidden'
        else:
            assert err['error'] == 'not_found'
            assert err['reason'] == 'deleted'

        assert err['id'] in docs_to_verify_deleted
        # Cross off the doc_id
        docs_to_verify_scratchpad.remove(err['id'])

    # Verify that all docs have been removed
    assert len(docs_to_verify_scratchpad) == 0


def verify_sdk_deletes(sdk_client, docs_ids_to_verify_deleted):
    """ Verifies that all doc ids have been deleted from the SDK """

    docs_to_verify_scratchpad = list(docs_ids_to_verify_deleted)

    for doc_id in docs_ids_to_verify_deleted:
        nfe = None
        with pytest.raises(NotFoundError) as nfe:
            sdk_client.get(doc_id)
        assert nfe is not None
        assert 'The key does not exist on the server' in str(nfe)
        docs_to_verify_scratchpad.remove(doc_id)

    # Verify that all docs have been removed
    assert len(docs_to_verify_scratchpad) == 0


def verify_sg_xattrs(mode, sg_client, sg_url, sg_db, doc_id, expected_number_of_revs, expected_number_of_channels, deleted_docs=False):
    """ Verify expected values for xattr sync meta data via Sync Gateway _raw """

    # Get Sync Gateway sync meta
    raw_doc = sg_client.get_raw_doc(sg_url, db=sg_db, doc_id=doc_id)
    sg_sync_meta = raw_doc['_sync']

    log_info('Verifying XATTR (expected num revs: {}, expected num channels: {})'.format(
        expected_number_of_revs,
        expected_number_of_channels,
    ))

    # Distributed index mode uses server's internal vbucket sequence
    # It does not expose this to the '_sync' meta
    if mode != 'di':
        assert isinstance(sg_sync_meta['sequence'], int)
        assert isinstance(sg_sync_meta['recent_sequences'], list)
        assert len(sg_sync_meta['recent_sequences']) == expected_number_of_revs

    assert isinstance(sg_sync_meta['cas'], unicode)
    assert sg_sync_meta['rev'].startswith('{}-'.format(expected_number_of_revs))
    assert isinstance(sg_sync_meta['channels'], dict)
    assert len(sg_sync_meta['channels']) == expected_number_of_channels
    assert isinstance(sg_sync_meta['time_saved'], unicode)
    assert isinstance(sg_sync_meta['history']['channels'], list)
    assert len(sg_sync_meta['history']['channels']) == expected_number_of_revs
    assert isinstance(sg_sync_meta['history']['revs'], list)
    assert len(sg_sync_meta['history']['revs']) == expected_number_of_revs
    assert isinstance(sg_sync_meta['history']['parents'], list)


def verify_no_sg_xattrs(sg_client, sg_url, sg_db, doc_id):
    """ Verify that _sync no longer exists in the the xattrs.
    This should be the case once a document is purged. """

    # Try to get Sync Gateway sync meta
    he = None
    with pytest.raises(HTTPError) as he:
        sg_client.get_raw_doc(sg_url, db=sg_db, doc_id=doc_id)
    assert he is not None
    assert 'HTTPError: 404 Client Error: Not Found for url:' in str(he)
    log_info(he.value)


def verify_doc_ids_in_sg_bulk_response(response, expected_number_docs, expected_ids):
    """ Verify 'expected_ids' are present in Sync Gateway _build_get request """

    log_info('Verifing SG bulk_get response has {} docs with expected ids ...'.format(expected_number_docs))

    expected_ids_scratch_pad = list(expected_ids)
    assert len(expected_ids_scratch_pad) == expected_number_docs
    assert len(response) == expected_number_docs

    # Cross off all the doc ids seen in the response from the scratch pad
    for doc in response:
        expected_ids_scratch_pad.remove(doc["_id"])

    # Make sure all doc ids have been found
    assert len(expected_ids_scratch_pad) == 0


def verify_doc_ids_in_sg_all_docs_response(response, expected_number_docs, expected_ids):
    """ Verify 'expected_ids' are present in Sync Gateway _all_docs request """

    log_info('Verifing SG all_docs response has {} docs with expected ids ...'.format(expected_number_docs))

    expected_ids_scratch_pad = list(expected_ids)
    assert len(expected_ids_scratch_pad) == expected_number_docs
    assert len(response['rows']) == expected_number_docs

    # Cross off all the doc ids seen in the response from the scratch pad
    for doc in response['rows']:
        expected_ids_scratch_pad.remove(doc['id'])

    # Make sure all doc ids have been found
    assert len(expected_ids_scratch_pad) == 0


def verify_doc_ids_in_sdk_get_multi(response, expected_number_docs, expected_ids):
    """ Verify 'expected_ids' are present in Python SDK get_multi() call """

    log_info('Verifing SDK get_multi response has {} docs with expected ids ...'.format(expected_number_docs))

    expected_ids_scratch_pad = list(expected_ids)
    assert len(expected_ids_scratch_pad) == expected_number_docs
    assert len(response) == expected_number_docs

    # Cross off all the doc ids seen in the response from the scratch pad
    for doc_id, value in response.items():
        assert '_sync' not in value.value
        expected_ids_scratch_pad.remove(doc_id)

    # Make sure all doc ids have been found
    assert len(expected_ids_scratch_pad) == 0


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.xattrs
@pytest.mark.changes
@pytest.mark.session
@pytest.mark.parametrize(
    'sg_conf_name, number_docs_per_client, number_updates_per_doc_per_client',
    [
        ('sync_gateway_default_functional_tests', 10, 10),
        ('sync_gateway_default_functional_tests', 100, 10),
        ('sync_gateway_default_functional_tests', 10, 100),
        ('sync_gateway_default_functional_tests', 1, 1000)
    ]
)
def test_sg_sdk_interop_shared_updates_from_sg(params_from_base_test_setup,
                                               sg_conf_name,
                                               number_docs_per_client,
                                               number_updates_per_doc_per_client):
    """
    Scenario:
    - Create docs via SG and get the revision number 1-rev
    - Update docs via SDK and get the revision number 2-rev
    - Update docs via SG with new_edits=false by giving parent revision 1-rev
        and get the revision number 2-rev1
    - update docs via SDK again and get the revision number 3-rev
    - Verify with _all_changes by enabling include docs and verify 2 branched revisions appear in changes feed
    - Verify no errors occur while updating docs via SG
    - Delete docs via SDK
    - Delete docs via SG
    - Verify no errors while deletion
    - Verify changes feed that branched revision are removed
    - Verify changes feed that keys "deleted" is true and keys "removed"
    """

    cluster_conf = params_from_base_test_setup['cluster_config']
    cluster_topology = params_from_base_test_setup['cluster_topology']
    mode = params_from_base_test_setup['mode']
    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']

    # This test should only run when using xattr meta storage
    if not xattrs_enabled:
        pytest.skip('XATTR tests require --xattrs flag')

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_admin_url = cluster_topology['sync_gateways'][0]['admin']
    sg_url = cluster_topology['sync_gateways'][0]['public']

    bucket_name = 'data-bucket'
    cbs_url = cluster_topology['couchbase_servers'][0]
    sg_db = 'db'

    log_info('Num docs per client: {}'.format(number_docs_per_client))
    log_info('Num updates per doc per client: {}'.format(number_updates_per_doc_per_client))

    log_info('sg_conf: {}'.format(sg_conf))
    log_info('sg_admin_url: {}'.format(sg_admin_url))
    log_info('sg_url: {}'.format(sg_url))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    sg_tracking_prop = 'sg_one_updates'
    sdk_tracking_prop = 'sdk_one_updates'

    # Create sg user
    sg_client = MobileRestClient()
    sg_client.create_user(url=sg_admin_url, db=sg_db, name='autotest', password='pass', channels=['shared'])
    autouser_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name='autotest', password='pass')

    # Connect to server via SDK
    cbs_ip = host_for_url(cbs_url)
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password', timeout=SDK_TIMEOUT)

    # Inject custom properties into doc template
    def update_props():
        return {
            'updates': 0,
            sg_tracking_prop: 0,
            sdk_tracking_prop: 0
        }

    # Create / add docs to sync gateway
    sg_docs = document.create_docs(
        'sg_doc',
        number_docs_per_client,
        channels=['shared'],
        prop_generator=update_props
    )
    sg_docs_resp = sg_client.add_bulk_docs(
        url=sg_url,
        db=sg_db,
        docs=sg_docs,
        auth=autouser_session
    )

    sg_doc_ids = [doc['_id'] for doc in sg_docs]
    assert len(sg_docs_resp) == number_docs_per_client

    sg_create_docs, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=sg_doc_ids,
                                                     auth=autouser_session)
    assert len(errors) == 0
    sg_create_doc = sg_create_docs[0]["_rev"]
    assert(sg_create_doc.startswith("1-"))
    log_info("Sg created  doc revision :{}".format(sg_create_doc))

    # Update docs via SDK
    sdk_docs = sdk_client.get_multi(sg_doc_ids)
    assert len(sdk_docs.keys()) == number_docs_per_client
    for doc_id, val in sdk_docs.items():
        doc_body = val.value
        doc_body["updated_by_sdk"] = True
        sdk_client.upsert(doc_id, doc_body)

    sdk_first_update_docs, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=sg_doc_ids,
                                                            auth=autouser_session)
    assert len(errors) == 0
    sdk_first_update_doc = sdk_first_update_docs[0]["_rev"]
    log_info("Sdk first update doc {}".format(sdk_first_update_doc))
    assert(sdk_first_update_doc.startswith("2-"))
    # Update the 'updates' property
    for doc in sg_create_docs:
        # update  docs via sync-gateway
        sg_client.add_conflict(
            url=sg_url,
            db=sg_db,
            doc_id=doc["_id"],
            parent_revisions=doc["_rev"],
            new_revision="2-bar",
            auth=autouser_session
        )

    sg_update_docs, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=sg_doc_ids,
                                                     auth=autouser_session)
    assert len(errors) == 0
    sg_update_doc = sg_update_docs[0]["_rev"]
    log_info("sg update doc revision is : {}".format(sg_update_doc))
    assert(sg_update_doc.startswith("2-"))
    # Update docs via SDK
    sdk_docs = sdk_client.get_multi(sg_doc_ids)
    assert len(sdk_docs.keys()) == number_docs_per_client
    for doc_id, val in sdk_docs.items():
        doc_body = val.value
        doc_body["updated_by_sdk2"] = True
        sdk_client.upsert(doc_id, doc_body)

    sdk_update_docs2, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=sg_doc_ids,
                                                       auth=autouser_session)
    assert len(errors) == 0
    sdk_update_doc2 = sdk_update_docs2[0]["_rev"]
    log_info("sdk 2nd update doc revision is : {}".format(sdk_update_doc2))
    assert(sdk_update_doc2.startswith("3-"))
    time.sleep(1)  # Need some delay to have _changes to update with latest branched revisions
    # Get branched revision tree via _changes with include docs
    docs_changes = sg_client.get_changes_style_all_docs(url=sg_url, db=sg_db, auth=autouser_session, include_docs=True)
    doc_changes_in_changes = [change["changes"] for change in docs_changes["results"]]

    # Iterate through all docs and verify branched revisions appear in changes feed, verify previous revisions
    # which created before branched revisions does not show up in changes feed
    for docs in doc_changes_in_changes[1:]:  # skip first item in list as first item has user information, but not doc information
        revs = [doc['rev'] for doc in docs]
        if sdk_first_update_doc in revs and sdk_update_doc2 in revs:
            assert True
        else:
            log_info("conflict revision does not exist {}".format(revs))
            assert False
        if sg_create_doc not in revs and sg_update_doc not in revs:
                assert True
        else:
            log_info("Non conflict revision exist {} ".format(revs))
            assert False

    # Do SDK deleted and SG delete after branched revision created and check changes feed removed branched revisions
    sdk_client.remove_multi(sg_doc_ids)
    time.sleep(1)  # Need some delay to have _changes to update with latest branched revisions
    sdk_deleted_docs, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=sg_doc_ids,
                                                       auth=autouser_session)
    assert len(errors) == 0
    sdk_deleted_doc = sdk_deleted_docs[0]["_rev"]
    log_info("sdk deleted doc revision :{}".format(sdk_deleted_doc))
    assert(sdk_deleted_doc.startswith("2-"))
    sg_client.delete_docs(url=sg_url, db=sg_db, docs=sg_docs_resp, auth=autouser_session)
    time.sleep(1)  # Need some delay to have _changes to update with latest branched revisions
    docs_changes1 = sg_client.get_changes_style_all_docs(url=sg_url, db=sg_db, auth=autouser_session, include_docs=True)
    doc_changes_in_changes = [change["changes"] for change in docs_changes1["results"]]
    deleted_doc_revisions = [change["doc"]["_deleted"] for change in docs_changes1["results"][1:]]
    removedchannel_doc_revisions = [change["removed"] for change in docs_changes1["results"][1:]]
    assert len(deleted_doc_revisions) == number_docs_per_client
    assert len(removedchannel_doc_revisions) == number_docs_per_client

    # Verify in changes feed that new branched revisions are created after deletion of branced revisions which created
    # by sg update and sdk update.
    for docs in doc_changes_in_changes[1:]:
        revs = [doc['rev'] for doc in docs]
        assert len(revs) == 2
        if sdk_first_update_doc not in revs and sdk_update_doc2 not in revs and sg_create_doc not in revs and sg_update_doc not in revs:
                assert True
        else:
                log_info(
                    "Deleted branched revisions still appear here {}".format(revs))
                assert False


@pytest.mark.syncgateway
@pytest.mark.xattrs
@pytest.mark.parametrize('sg_conf_name', [
    'sync_gateway_default_functional_tests'
])
def test_purge_and_view_compaction(params_from_base_test_setup, sg_conf_name):
    """
    Scenario:
    - Generate some tombstones doc
    - Verify meta data still exists by verifygin sg xattrs using _raw sync gateway API
    - Execute a view query to see the tombstones -> http GET localhost:4985/default/_view/channels
        -> should see tombstone doc
    - Sleep for 5 mins to verify tomstone doc is available in view query and meta data
    - Trigger purge API to force the doc to purge
    - Verify meta data does not exists by verifying sg xattrs using _raw sync gateway API
    - Execute a view query to see the tombstones -> http GET localhost:4985/default/_view/channels
        -> should see tombstone doc after the purge
    - Trigger _compact API to compact the tombstone doc
    - Verify tomstones are not seen in view query
    """

    sg_db = 'db'
    cluster_conf = params_from_base_test_setup['cluster_config']
    cluster_topology = params_from_base_test_setup['cluster_topology']
    mode = params_from_base_test_setup['mode']
    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']

    # This test should only run when using xattr meta storage
    if not xattrs_enabled:
        pytest.skip('XATTR tests require --xattrs flag')

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_admin_url = cluster_topology['sync_gateways'][0]['admin']
    sg_url = cluster_topology['sync_gateways'][0]['public']
    cbs_url = cluster_topology['couchbase_servers'][0]

    log_info('sg_conf: {}'.format(sg_conf))
    log_info('sg_admin_url: {}'.format(sg_admin_url))
    log_info('sg_url: {}'.format(sg_url))
    log_info('cbs_url: {}'.format(cbs_url))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)
    # Create clients
    sg_client = MobileRestClient()
    channels = ['tombstone_test']

    # Create user / session
    auto_user_info = UserInfo(name='autotest', password='pass', channels=channels, roles=[])
    sg_client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=auto_user_info.name,
        password=auto_user_info.password,
        channels=auto_user_info.channels
    )

    test_auth_session = sg_client.create_session(
        url=sg_admin_url,
        db=sg_db,
        name=auto_user_info.name,
        password=auto_user_info.password
    )

    def update_prop():
        return {
            'updates': 0,
            'tombstone': 'true',
        }

    doc_id = 'tombstone_test_sg_doc'
    doc_body = document.create_doc(doc_id=doc_id, channels=['tombstone_test'], prop_generator=update_prop)
    sg_client.add_doc(url=sg_url, db=sg_db, doc=doc_body, auth=test_auth_session)
    doc = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id, auth=test_auth_session)
    sg_client.delete_doc(url=sg_url, db=sg_db, doc_id=doc_id, rev=doc['_rev'], auth=test_auth_session)
    number_revs_per_doc = 1
    verify_sg_xattrs(
        mode,
        sg_client,
        sg_url=sg_admin_url,
        sg_db=sg_db,
        doc_id=doc_id,
        expected_number_of_revs=number_revs_per_doc + 1,
        expected_number_of_channels=len(channels),
        deleted_docs=True
    )
    start = time.time()
    timeout = 10  # timeout for view query in channels due to race condition after compacting the docs
    while True:
        channel_view_query = sg_client.view_query_through_channels(url=sg_admin_url, db=sg_db)
        channel_view_query_string = json.dumps(channel_view_query)
        if(doc_id in channel_view_query_string or time.time() - start > timeout):
                break
    assert doc_id in channel_view_query_string, "doc id not exists in view query"
    time.sleep(300)  # wait for 5 mins and see meta is still available as it is not purged yet
    verify_sg_xattrs(
        mode,
        sg_client,
        sg_url=sg_admin_url,
        sg_db=sg_db,
        doc_id=doc_id,
        expected_number_of_revs=number_revs_per_doc + 1,
        expected_number_of_channels=len(channels),
        deleted_docs=True
    )
    channel_view_query_string = sg_client.view_query_through_channels(url=sg_admin_url, db=sg_db)
    channel_view_query_string = json.dumps(channel_view_query)
    assert doc_id in channel_view_query_string, "doc id not exists in view query"
    docs = []
    docs.append(doc)
    purged_doc = sg_client.purge_docs(url=sg_admin_url, db=sg_db, docs=docs)
    log_info("Purged doc is {}".format(purged_doc))
    verify_no_sg_xattrs(
        sg_client=sg_client,
        sg_url=sg_url,
        sg_db=sg_db,
        doc_id=doc_id
    )
    channel_view_query = sg_client.view_query_through_channels(url=sg_admin_url, db=sg_db)
    channel_view_query_string = json.dumps(channel_view_query)
    assert doc_id in channel_view_query_string, "doc id not exists in view query"
    sg_client.compact_database(url=sg_admin_url, db=sg_db)
    start = time.time()
    timeout = 10  # timeout for view query in channels due to race condition after compacting the docs
    while True:
        channel_view_query = sg_client.view_query_through_channels(url=sg_admin_url, db=sg_db)
        channel_view_query_string = json.dumps(channel_view_query)
        if(doc_id not in channel_view_query_string or time.time() - start > timeout):
                break
    assert doc_id not in channel_view_query_string, "doc id exists in chanel view query after compaction"
