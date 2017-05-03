import random

import pytest
from concurrent.futures import ThreadPoolExecutor
from couchbase.bucket import Bucket
from couchbase import subdocument
from couchbase.exceptions import NotFoundError
from requests.exceptions import HTTPError

from keywords import attachment, document
from keywords.userinfo import UserInfo
from keywords.constants import DATA_DIR
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.utils import host_for_url, log_info
from libraries.testkit.cluster import Cluster


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
    - Sync Gateway delete 1/2 the docs
    - Sync Gateway purge all docs
    - Verify SDK can't see the docs
    - Verify SG can't see the docs
    - Verify XATTRS are gone using SDK client with full bucket permissions via subdoc?
    """

    cluster_conf = params_from_base_test_setup['cluster_config']
    cluster_topology = params_from_base_test_setup['cluster_topology']
    mode = params_from_base_test_setup['mode']

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
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')

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
        verify_xattrs(
            sdk_client=sdk_client,
            sg_client=sg_client,
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

    assert len(doc_id_choice_pool) == number_docs_per_client
    assert len(deleted_doc_ids) == number_docs_per_client

    import pdb
    pdb.set_trace()

    # Sync Gateway purge all docs
    sg_client.purge_docs(url=sg_admin_url, db=sg_db, docs=sg_docs)

    # Verify SG can't see the docs. Bulk get should only return errors
    sg_docs_visible_after_purge, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=all_doc_ids, auth=seth_auth, validate=False)
    assert len(sg_docs_visible_after_purge) == 0
    assert len(errors) == number_docs_per_client * 2

    sg_deleted_doc_scratch_pad = list(all_doc_ids)
    for error in errors:
        # TODO: Are these the expected errors?
        assert error['status'] == 403
        assert error['reason'] == 'forbidden'
        assert error['error'] == 'forbidden'
        assert error['id'] in sg_deleted_doc_scratch_pad
        sg_deleted_doc_scratch_pad.remove(error['id'])

    assert len(deleted_doc_ids) == 0

    # Verify SDK can't see the docs
    sdk_docs_visible_after_purge = sdk_client.get_multi(all_doc_ids)
    assert len(sdk_docs_visible_after_purge) == 0

    # Verify XATTRS are gone using SDK client with full bucket permissions via subdoc?
    for doc_id in all_doc_ids:
        verify_no_xattrs()

    import pdb
    pdb.set_trace()


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
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')

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
    - TODO: SDK should verify it does not see _sync
    - Bulk update each doc 'number_updates' from SG for 'sg' docs
    - TODO: SDK: Verify doc updates (sg + sdk) are present using the doc['content']['updates'] property
    - TODO: SG: Verify doc updates (sg + sdk) are there via _all_docs using the doc['content']['updates'] property and rev prefix
    - TODO: SG: Verify doc updates (sg + sdk) are there via _changes using the doc['content']['updates'] property and rev prefix
    - Bulk delete 'sdk' docs from SDK
    - Bulk delete 'sg' docs from SG
    - Verify SDK sees all docs (sg + sdk) as deleted
    - Verify SG sees all docs (sg + sdk) as deleted
    """

    cluster_conf = params_from_base_test_setup['cluster_config']
    cluster_topology = params_from_base_test_setup['cluster_topology']
    mode = params_from_base_test_setup['mode']

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
    cbs_ip = host_for_url(cbs_url)
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')

    # Create docs and add them via sdk
    sdk_doc_bodies = document.create_docs('sdk', number_docs_per_client, content={'foo': 'bar', 'updates': 1}, channels=['sdk'])
    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    sdk_doc_ids = [doc for doc in sdk_docs]
    sdk_client.upsert_multi(sdk_docs)

    # Create sg user
    sg_client = MobileRestClient()
    sg_client.create_user(url=sg_admin_url, db=sg_db, name='seth', password='pass', channels=['sg', 'sdk'])
    seth_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name='seth', password='pass')

    # Create / add docs to sync gateway
    sg_docs = document.create_docs('sg', number_docs_per_client, content={'foo': 'bar', 'updates': 1}, channels=['sg'])
    log_info('Adding bulk_docs')
    sg_docs_resp = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs, auth=seth_session)
    sg_doc_ids = [doc['_id'] for doc in sg_docs]
    assert len(sg_docs_resp) == number_docs_per_client

    all_doc_ids = sdk_doc_ids + sg_doc_ids

    # Verify docs all docs are present via SG _bulk_get
    all_docs_via_sg, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=all_doc_ids, auth=seth_session)
    assert len(all_docs_via_sg) == number_docs_per_client * 2
    assert len(errors) == 0

    # Verify docs all docs are present via SG _all_docs
    all_docs_resp = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=seth_session)
    assert len(all_docs_resp["rows"]) == number_docs_per_client * 2
    all_docs_scratch_pad = list(all_doc_ids)
    assert len(all_docs_scratch_pad) == number_docs_per_client * 2
    for doc in all_docs_resp["rows"]:
        all_docs_scratch_pad.remove(doc["id"])
    assert len(all_docs_scratch_pad) == 0

    # Verify docs all docs are present via SDK get_multi
    all_sdk_docs_scratch_pad = list(all_doc_ids)
    assert len(all_sdk_docs_scratch_pad) == number_docs_per_client * 2
    all_docs_via_sdk = sdk_client.get_multi(all_doc_ids)
    for doc_id in all_docs_via_sdk:
        all_sdk_docs_scratch_pad.remove(doc_id)
    assert len(all_sdk_docs_scratch_pad) == 0

    # SG: Verify docs (sg + sdk) are there via _changes
    # Format docs for changes verification
    all_docs_via_sg_formatted = [{"id": doc["_id"], "rev": doc["_rev"]} for doc in all_docs_via_sg]
    assert len(all_docs_via_sg_formatted) == number_docs_per_client * 2
    sg_client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=all_docs_via_sg_formatted, auth=seth_session)

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
    all_docs_from_sg, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=all_doc_ids, auth=seth_session)
    assert len(all_docs_from_sg) == number_docs_per_client * 2
    assert len(errors) == 0
    for doc in all_docs_from_sg:
        # If it is an SG doc the revision prefix should match the number of updates.
        # This may not be the case due to batched importing of SDK updates
        if doc['_id'].startswith('sg_'):
            assert doc['_rev'].startswith('{}-'.format(number_updates + 1))
        assert doc['content']['updates'] == number_updates + 1

    # Verify updates from SG via _all_docs
    all_docs_from_sg = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=seth_session, include_docs=True)
    assert len(all_docs_from_sg['rows']) == number_docs_per_client * 2
    for doc in all_docs_from_sg['rows']:
        # If it is an SG doc the revision prefix should match the number of updates.
        # This may not be the case due to batched importing of SDK updates
        if doc['id'].startswith('sg_'):
            assert doc['value']['rev'].startswith('{}-'.format(number_updates + 1))
            assert doc['doc']['_rev'].startswith('{}-'.format(number_updates + 1))

        assert doc['id'] == doc['doc']['_id']
        assert doc['doc']['content']['updates'] == number_updates + 1
    
    # Verify updates from SG via _changes
    # Verify updates from SDK via get_multi

    # TODO: SDK: Verify doc updates (sg + sdk) are present using the doc['content']['updates'] property
    # TODO: SG: Verify doc updates (sg + sdk) are there via _all_docs using the doc['content']['updates'] property and rev prefix
    # TODO: SG: Verify doc updates (sg + sdk) are there via _changes using the doc['content']['updates'] property and rev prefix

    # Delete the sync gateway docs
    # sg_client.delete_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs_to_delete, auth=seth_session)
    # TODO: assert len(try_get_deleted_rows) == number_docs * 2

    # Delete the sdk docs
    sdk_client.remove_multi(sdk_doc_ids)

    # Verify all docs are deleted on the sync_gateway side
    all_doc_ids = sdk_doc_ids + sg_doc_ids
    assert len(all_doc_ids) == 2 * number_docs_per_client

    # Check deletes via GET /db/doc_id and bulk_get
    verify_sg_deletes(client=sg_client, url=sg_url, db=sg_db, docs_to_verify_deleted=all_doc_ids, auth=seth_session)

    # Verify all docs are deleted on sdk, deleted docs should rase and exception
    for doc_id in all_doc_ids:
        with pytest.raises(NotFoundError) as nfe:
            sdk_client.get(doc_id)
        log_info(nfe.value)
        all_doc_ids.remove(nfe.value.key)

    # Assert that all of the docs are flagged as deleted
    assert len(all_doc_ids) == 0


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.xattrs
@pytest.mark.changes
@pytest.mark.session
@pytest.mark.parametrize('sg_conf_name', [
    'sync_gateway_default_functional_tests'
])
def test_sg_sdk_interop_shared_docs(params_from_base_test_setup, sg_conf_name):
    """
    Scenario:
    - Bulk create 'number_docs' docs from SDK with prefix 'doc_set_one' and channels ['shared']
      with 'sg_one_updates' and 'sdk_one_updates' counter properties
    - Bulk create 'number_docs' docs from SG with prefix 'doc_set_two' and channels ['shared']
      with 'sg_one_updates' and 'sdk_one_updates' counter properties
    - TODO: SDK: Verify docs (sg + sdk) are present
    - TODO: SG: Verify docs (sg + sdk) are there via _all_docs
    - TODO: SG: Verify docs (sg + sdk) are there via _changes
    - Start concurrent updates:
        - Start update from sg / sdk to a shared set of docs. Sync Gateway and SDK will try to update
          random docs from the shared set and update the corresponding counter property as well as the
          'updates' properties
    - TODO: SDK: Verify doc updates (sg + sdk) are present using the counter properties
    - TODO: SG: Verify doc updates (sg + sdk) are there via _all_docs using the counter properties and rev prefix
    - TODO: SG: Verify doc updates (sg + sdk) are there via _changes using the counter properties and rev prefix
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

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_admin_url = cluster_topology['sync_gateways'][0]['admin']
    sg_url = cluster_topology['sync_gateways'][0]['public']

    bucket_name = 'data-bucket'
    cbs_url = cluster_topology['couchbase_servers'][0]
    sg_db = 'db'
    number_docs_per_client = 10
    number_updates_per_client = 10

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
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')

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

    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    doc_set_two_ids = [sdk_doc['_id'] for sdk_doc in sdk_doc_bodies]
    sdk_docs_resp = sdk_client.upsert_multi(sdk_docs)
    assert len(sdk_docs_resp) == number_docs_per_client

    # TODO: SDK: Verify docs (sg + sdk) are present
    # TODO: SG: Verify docs (sg + sdk) are there via _all_docs
    # TODO: SG: Verify docs (sg + sdk) are there via _changes

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
            number_updates=number_updates_per_client,
            auth=seth_session
        )

        update_from_sdk_task = tpe.submit(
            update_sdk_docs,
            client=sdk_client,
            docs_to_update=all_doc_ids,
            prop_to_update=sdk_tracking_prop,
            number_updates=number_docs_per_client
        )

        # Make sure to block on the result to catch any exceptions that may have been thrown
        # during execution of the future
        update_from_sg_task.result()
        update_from_sdk_task.result()

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

        assert doc_body['updates'] == number_updates_per_client * 2
        assert doc_body[sg_tracking_prop] == number_updates_per_client
        assert doc_body[sdk_tracking_prop] == number_updates_per_client

        # Get doc from Sync Gateway
        doc = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id, auth=seth_session)

        assert doc['updates'] == number_updates_per_client * 2
        assert doc[sg_tracking_prop] == number_updates_per_client
        assert doc[sdk_tracking_prop] == number_updates_per_client
        assert doc['_rev'].startswith('21')
        assert len(doc['_revisions']['ids']) == (number_updates_per_client * 2) + 1

    # TODO: Verify sync gateway changes feed

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

    assert len(all_doc_ids) == number_docs_per_client
    verify_sg_deletes(client=sg_client, url=sg_url, db=sg_db, docs_to_verify_deleted=all_doc_ids, auth=seth_session)


def delete_sg_docs(client, url, db, docs_to_delete, auth):

    # Create a copy of all doc ids
    docs_to_remove = list(docs_to_delete)
    while len(docs_to_remove) > 0:
        random_doc_id = random.choice(docs_to_remove)
        log_info('Attempting to delete from SG: {}'.format(random_doc_id))
        # TODO reenable: doc_to_delete = client.get_doc(url=url, db=db, doc_id=random_doc_id, auth=auth)
        # TODO reenable: deleted_doc = client.delete_doc(url=url, db=db, doc_id=random_doc_id, rev=doc_to_delete['_rev'], auth=auth)
        # Todo: Add assertion
        docs_to_remove.remove(random_doc_id)


def delete_sdk_docs(client, docs_to_delete):

    # Create a copy of all doc ids
    docs_to_remove = list(docs_to_delete)
    while len(docs_to_remove) > 0:
        random_doc_id = random.choice(docs_to_remove)
        log_info('Attempting to delete from SDK: {}'.format(random_doc_id))
        # TODO reenable: deleted_doc = client.remove(random_doc_id)
        # Todo: Add assertion
        docs_to_remove.remove(random_doc_id)


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
                client.update_doc(url=url, db=db, doc_id=random_doc_id, property_updater=property_updater, auth=auth)
            except HTTPError as e:
                # This is possible if hitting a conflict. Check that it is. If it is not, we want to raise
                if not is_conflict(e):
                    raise
                else:
                    log_info('Hit a conflict! Will retry later ...')


def is_conflict(httperror):
    if httperror.response.status_code == 409 \
            and httperror.message.startswith('409 Client Error: Conflict for url:'):
        return True
    else:
        return False


def update_sdk_docs(client, docs_to_update, prop_to_update, number_updates):
    log_info("Client: {}".format(id(client)))

    # Store copy of list to avoid mutating 'docs_to_update'
    local_docs_to_update = list(docs_to_update)

    while len(local_docs_to_update) > 0:
        random_doc_id = random.choice(local_docs_to_update)
        log_info(random_doc_id)

        doc = client.get(random_doc_id)
        doc_body = doc.value

        if doc_body[prop_to_update] == number_updates:
            local_docs_to_update.remove(random_doc_id)
        else:
            # TODO: Make sure it is a CAS safe write
            doc_body[prop_to_update] += 1
            doc_body['updates'] += 1
            client.upsert(random_doc_id, doc_body)


def verify_sg_deletes(client, url, db, docs_to_verify_deleted, auth):

    docs_to_verify_scratchpad = list(docs_to_verify_deleted)

    # Verify deletes via individual GETs
    for doc_id in docs_to_verify_deleted:
        with pytest.raises(HTTPError) as he:
            client.get_doc(url=url, db=db, doc_id=doc_id, auth=auth)

        log_info(he.value.message)

        # u'404 Client Error: Not Found for url: http://192.168.33.11:4984/db/sg_0?conflicts=true&revs=true'
        assert he.value.message.startswith('404 Client Error: Not Found for url:')

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
    try_get_bulk_docs = client.get_bulk_docs(url=url, db=db, doc_ids=docs_to_verify_deleted, auth=auth)
    assert len(try_get_bulk_docs["rows"]) == len(docs_to_verify_deleted)

    # TODO: Verify with Adam, should this be reason=deleted or reason=missing?
    for row in try_get_bulk_docs['rows']:
        assert row['id'] in docs_to_verify_deleted
        assert row['status'] == 404
        assert row['error'] == 'not_found'
        assert row['reason'] == 'deleted'

        # Cross off the doc_id
        docs_to_verify_scratchpad.remove(row['id'])

    # Verify that all docs have been removed
    assert len(docs_to_verify_scratchpad) == 0


def verify_xattrs(sdk_client, sg_client, sg_url, sg_db, doc_id, expected_number_of_revs, expected_number_of_channels):
    """ Verify expected values for xattr sync meta data with regard to expected inputs """

    # Get SDK sync meta
    sdk_sync_xattrs = sdk_client.lookup_in(doc_id, subdocument.get("_sync", xattr=True))
    sdk_sync_meta = sdk_sync_xattrs.get("_sync")[1]

    # Get Sync Gateway sync meta
    raw_doc = sg_client.get_raw_doc(sg_url, db=sg_db, doc_id=doc_id)
    sg_sync_meta = raw_doc["_sync"]

    # Verfy the propery
    for sync_meta in [sdk_sync_meta, sg_sync_meta]:

        log_info("Verifying XATTR (expected num revs: {}, expected num channels: {}): {}".format(
            expected_number_of_revs,
            expected_number_of_channels,
            sync_meta
        ))

        assert isinstance(sync_meta["sequence"], int)
        assert isinstance(sync_meta["recent_sequences"], list)
        assert len(sync_meta["recent_sequences"]) == expected_number_of_revs
        assert isinstance(sync_meta["cas"], unicode)

        assert sync_meta["rev"].startswith("{}-".format(expected_number_of_revs))

        assert isinstance(sync_meta["channels"], dict)
        assert len(sync_meta["channels"]) == expected_number_of_channels
        assert sync_meta["channels"]["NASA"] is None

        assert isinstance(sync_meta["time_saved"], unicode)

        assert isinstance(sync_meta["history"]["channels"], list)
        assert len(sync_meta["history"]["channels"]) == expected_number_of_revs
        assert len(sync_meta["history"]["channels"][0]) == expected_number_of_channels

        assert isinstance(sync_meta["history"]["revs"], list)
        assert len(sync_meta["history"]["revs"]) == expected_number_of_revs

        assert isinstance(sync_meta["history"]["parents"], list)
        assert sync_meta["history"]["parents"] == [-1]

    assert sdk_sync_meta == sg_sync_meta


def verify_no_xattrs():
    raise NotImplementedError()
