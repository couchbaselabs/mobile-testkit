import random

import pytest
from requests.exceptions import HTTPError
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import wait

from couchbase.bucket import Bucket
from couchbase.exceptions import NotFoundError

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.utils import log_info
from keywords.utils import host_for_url
from keywords import document
from libraries.testkit.cluster import Cluster
from keywords.MobileRestClient import MobileRestClient


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.sdk
@pytest.mark.changes
@pytest.mark.session
@pytest.mark.parametrize('sg_conf_name', [
    'sync_gateway_default_functional_tests'
])
def test_sdk_interop_unique_docs(params_from_base_test_setup, sg_conf_name):

    """
    Scenario:
    - Bulk create 'number_docs' docs from SDK with prefix 'sdk' and channels ['sdk']
    - Bulk create 'number_docs' docs from SG with prefix 'sg' and channels ['sg']
    - TODO: SDK: Verify docs (sg + sdk) are present
    - TODO: SG: Verify docs (sg + sdk) are there via _all_docs
    - TODO: SG: Verify docs (sg + sdk) are there via _changes 
    - Bulk update each doc 'number_updates' from SDK for 'sdk' docs
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
    number_docs = 10
    number_updates = 10

    log_info('sg_conf: {}'.format(sg_conf))
    log_info('sg_admin_url: {}'.format(sg_admin_url))
    log_info('sg_url: {}'.format(sg_url))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    # Connect to server via SDK
    cbs_ip = host_for_url(cbs_url)
    bucket = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name))

    # Create docs and add them via sdk
    sdk_doc_bodies = document.create_docs('sdk', number_docs, content={'foo': 'bar', 'updates': 1}, channels=['sdk'])
    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    sdk_doc_ids = [doc for doc in sdk_docs]
    bucket.upsert_multi(sdk_docs)

    # Create sg user
    sg_client = MobileRestClient()
    sg_client.create_user(url=sg_admin_url, db=sg_db, name='seth', password='pass', channels=['sg', 'sdk'])
    seth_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name='seth', password='pass')

    # Create / add docs to sync gateway
    sg_docs = document.create_docs('sg', number_docs, content={'foo': 'bar', 'updates': 1}, channels=['sg'])
    sg_docs_resp = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs, auth=seth_session)
    sg_doc_ids = [doc['_id'] for doc in sg_docs]

    assert len(sg_docs_resp) == number_docs

    # Since seth has channels from 'sg' and 'sdk', verify that the sdk docs and sg docs show up in
    # seth's changes feed

    # TODO: SDK: Verify docs (sg + sdk) are present
    # TODO: SG: Verify docs (sg + sdk) are there via _all_docs
    # TODO: SG: Verify docs (sg + sdk) are there via _changes

    for i in range(number_updates):

        # Get docs and extract doc_id (key) and doc_body (value.value)
        sdk_docs_resp = bucket.get_multi(sdk_doc_ids)
        docs = {k: v.value for k, v in sdk_docs_resp.items()}

        # update the updates property for every doc
        for _, v in docs.items():
            v['content']['updates'] += 1

        # Push the updated batch to Couchbase Server
        bucket.upsert_multi(docs)

        # Get docs from Sync Gateway
        sg_docs_to_update_resp = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=sg_doc_ids, auth=seth_session)
        sg_docs_to_update = sg_docs_to_update_resp['rows']
        for sg_doc in sg_docs_to_update:
            sg_doc['content']['updates'] += 1

        # Bulk add the updates to Sync Gateway
        sg_docs_resp = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs_to_update, auth=seth_session)

    # Get docs from Sync Gateway
    sg_docs_to_update_resp = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=sg_doc_ids, auth=seth_session)
    sg_docs_to_update = sg_docs_to_update_resp['rows']

    # TODO: SDK: Verify doc updates (sg + sdk) are present using the doc['content']['updates'] property
    # TODO: SG: Verify doc updates (sg + sdk) are there via _all_docs using the doc['content']['updates'] property and rev prefix
    # TODO: SG: Verify doc updates (sg + sdk) are there via _changes using the doc['content']['updates'] property and rev prefix

    # Delete the sync gateway docs
    sg_client.delete_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs_to_update, auth=seth_session)
    # TODO: assert len(try_get_deleted_rows) == number_docs * 2

    # Delete the sdk docs
    bucket.remove_multi(sdk_doc_ids)

    # Verify all docs are deleted on the sync_gateway side
    all_doc_ids = sdk_doc_ids + sg_doc_ids
    assert len(all_doc_ids) == 2 * number_docs

    # Check GET /db/doc_id
    for doc_id in all_doc_ids:
        with pytest.raises(HTTPError) as he:
            sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id, auth=seth_session)

        log_info(he.value.message)

        # u'404 Client Error: Not Found for url: http://192.168.33.11:4984/db/sg_0?conflicts=true&revs=true'
        assert he.value.message.startswith('404 Client Error: Not Found for url:')

        # Parse out the doc id
        # sg_0?conflicts=true&revs=true
        parts = he.value.message.split('/')[-1]
        doc_id_from_parts = parts.split('?')[0]

        # Remove the doc id from the list
        all_doc_ids.remove(doc_id_from_parts)

    # Assert that all of the docs are flagged as deleted
    # TODO: assert len(all_doc_ids) == 0

    # Check /db/_bulk_get
    all_doc_ids = sdk_doc_ids + sg_doc_ids
    try_get_bulk_docs = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=all_doc_ids, auth=seth_session)

    # TODO: assert len(try_get_bulk_docs["rows"]) == number_docs * 2

    for row in try_get_bulk_docs['rows']:
        assert row['id'] in all_doc_ids
        assert row['status'] == 404
        assert row['error'] == 'not_found'
        assert row['reason'] == 'deleted'

        # Cross off the doc_id
        all_doc_ids.remove(row['id'])

    # Verify all docs are deleted on the sdk side
    all_doc_ids = sdk_doc_ids + sg_doc_ids

    # Verify all docs are deleted on sdk, deleted docs should rase and exception
    for doc_id in all_doc_ids:
        with pytest.raises(NotFoundError) as nfe:
            bucket.get(doc_id)
        log_info(nfe.value)
        all_doc_ids.remove(nfe.value.key)

    # Assert that all of the docs are flagged as deleted
    assert len(all_doc_ids) == 0


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.sdk
@pytest.mark.changes
@pytest.mark.session
@pytest.mark.parametrize('sg_conf_name', [
    'sync_gateway_default_functional_tests'
])
def test_sdk_interop_shared_docs(params_from_base_test_setup, sg_conf_name):
    """
    Scenario:
    - Bulk create 'number_docs' docs from SDK with prefix 'doc_set_one' and channels ['shared']
    - Bulk create 'number_docs' docs from SG with prefix 'doc_set_two' and channels ['shared']
    - TODO: SDK: Verify docs (sg + sdk) are present
    - TODO: SG: Verify docs (sg + sdk) are there via _all_docs
    - TODO: SG: Verify docs (sg + sdk) are there via _changes 
    - Start concurrent updates:
        loop until sg map and sdk map are len 0
        - Maintain map of each doc id to number of updates for sg
        - Maintain map of each doc id to number of updates for sdk
        - Pick random doc from sg map
        - Try to update doc from SG
        - If successful and num_doc_updates == number_updates_per_client, mark doc as finished in sg tracking map
        - Pick random doc from sdk map
        - Try to update doc from SDK
        - If successful and num_doc_updates == number_updates_per_client, mark doc as finished in sdk tracking map
    - TODO: SDK: Verify doc updates (sg + sdk) are present using the doc['content']['updates'] property
    - TODO: SG: Verify doc updates (sg + sdk) are there via _all_docs using the doc['content']['updates'] property and rev prefix
    - TODO: SG: Verify doc updates (sg + sdk) are there via _changes using the doc['content']['updates'] property and rev prefix
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

    sg_one_tracking_prop = 'sg_one_updates'
    sg_two_tracking_prop = 'sg_two_updates'
    sdk_one_tracking_prop = 'sdk_one_updates'
    sdk_two_tracking_prop = 'sdk_two_updates'

    # Create sg user
    sg_client_one = MobileRestClient()
    sg_client_two = MobileRestClient()

    sg_client_one.create_user(url=sg_admin_url, db=sg_db, name='seth', password='pass', channels=['shared'])
    seth_session = sg_client_one.create_session(url=sg_admin_url, db=sg_db, name='seth', password='pass')

    # Inject custom properties into doc template
    def update_props():
        return {
            'updates': 0,
            sg_one_tracking_prop: 0,
            sg_two_tracking_prop: 0,
            sdk_one_tracking_prop: 0,
            sdk_two_tracking_prop: 0
        }

    # Create / add docs to sync gateway
    sg_docs = document.create_docs(
        'doc_set_one',
        number_docs_per_client,
        channels=['shared'],
        prop_generator=update_props
    )
    sg_docs_resp = sg_client_one.add_bulk_docs(
        url=sg_url,
        db=sg_db,
        docs=sg_docs,
        auth=seth_session
    )
    doc_set_one_ids = [doc['_id'] for doc in sg_docs]
    assert len(sg_docs_resp) == number_docs_per_client

    # Create / add docs to sync gateway
    sg_docs = document.create_docs(
        'doc_set_two',
        number_docs_per_client,
        channels=['shared'],
        prop_generator=update_props
    )
    sg_docs_resp = sg_client_two.add_bulk_docs(
        url=sg_url,
        db=sg_db,
        docs=sg_docs,
        auth=seth_session
    )
    doc_set_two_ids = [doc['_id'] for doc in sg_docs]
    assert len(sg_docs_resp) == number_docs_per_client

    # TODO: SDK: Verify docs (sg + sdk) are present
    # TODO: SG: Verify docs (sg + sdk) are there via _all_docs
    # TODO: SG: Verify docs (sg + sdk) are there via _changes

    # Build a dictionary of all the doc ids with default number of updates (1 for created)
    docs_to_update = doc_set_one_ids + doc_set_two_ids
    assert len(docs_to_update) == number_docs_per_client * 2

    with ProcessPoolExecutor() as pex:
        update_task_one = pex.submit(
            update_sg_docs,
            client=sg_client_one,
            url=sg_url,
            db=sg_db,
            docs_to_update=docs_to_update,
            prop_to_update=sg_one_tracking_prop,
            number_updates=number_updates_per_client,
            auth=seth_session
        )

        update_task_two = pex.submit(
            update_sg_docs,
            client=sg_client_two,
            url=sg_url,
            db=sg_db,
            docs_to_update=docs_to_update,
            prop_to_update=sg_two_tracking_prop,
            number_updates=number_updates_per_client,
            auth=seth_session
        )

        # Make sure to block on the result to catch any exceptions that may have been thrown
        # during execution of the future
        update_task_one.result()
        update_task_two.result()

    # TODO: Verify doc properties readable from either client and are expected.
    # TODO: Verify everything shows up in changes

    # Connect to server via SDK
    cbs_ip = host_for_url(cbs_url)
    sdk_client_one = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name))
    sdk_client_two = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name))

    docs_to_update = doc_set_one_ids + doc_set_two_ids
    assert len(docs_to_update) == number_docs_per_client * 2

    with ThreadPoolExecutor(max_workers=5) as tpe:
        sdk_update_task_one = tpe.submit(
            update_sdk_docs,
            sdk_client_one,
            docs_to_update=docs_to_update,
            prop_to_update=sdk_one_tracking_prop,
            number_updates=number_docs_per_client
        )

        sdk_update_task_two = tpe.submit(
            update_sdk_docs,
            sdk_client_two,
            docs_to_update=docs_to_update,
            prop_to_update=sdk_two_tracking_prop,
            number_updates=number_docs_per_client
        )

        # Make sure to block on the result to catch any exceptions that may have been thrown
        # during execution of the future
        sdk_update_task_one.result()
        sdk_update_task_two.result()

    # Get all of the docs and verify that all updates we applied
    log_info('Verifying that all docs have the expected number of updates.')
    for doc_id in docs_to_update:
        doc_result = sdk_client_one.get(doc_id)
        doc_body = doc_result.value

        log_info('doc: {} -> {}:{}, {}:{}, {}:{}, {}:{}'.format(
            doc_id,
            sg_one_tracking_prop, doc_body[sg_one_tracking_prop],
            sg_two_tracking_prop, doc_body[sg_two_tracking_prop],
            sdk_one_tracking_prop, doc_body[sdk_one_tracking_prop],
            sdk_two_tracking_prop, doc_body[sdk_two_tracking_prop],
        ))

        assert doc_body[sg_one_tracking_prop] == number_updates_per_client
        assert doc_body[sg_two_tracking_prop] == number_updates_per_client
        assert doc_body[sdk_one_tracking_prop] == number_updates_per_client
        assert doc_body[sdk_two_tracking_prop] == number_updates_per_client

    # TODO: Move concurrent SDK updates to same block as SG updates and make sure both
    #  clients are updating the same document


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
        random_doc_id = random.choice(list(local_docs_to_update))
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
        random_doc_id = random.choice(list(local_docs_to_update))
        log_info(random_doc_id)

        doc = client.get(random_doc_id)
        doc_body = doc.value

        if doc_body[prop_to_update] == number_updates:
            local_docs_to_update.remove(random_doc_id)
        else:
            doc_body[prop_to_update] += 1
            client.upsert(random_doc_id, doc_body)
