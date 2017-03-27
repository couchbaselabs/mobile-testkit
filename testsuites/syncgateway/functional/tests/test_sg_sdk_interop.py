import pytest

from couchbase.bucket import Bucket

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

    cluster_conf = params_from_base_test_setup['cluster_config']
    cluster_topology = params_from_base_test_setup['cluster_topology']
    mode = params_from_base_test_setup['mode']

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_admin_url = cluster_topology['sync_gateways'][0]['admin']
    sg_url = cluster_topology['sync_gateways'][0]['public']

    bucket_name = 'data-bucket'
    cbs_url = cluster_topology['couchbase_servers'][0]
    sg_db = "db"
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
    sg_doc_ids = [doc["_id"] for doc in sg_docs]

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
        sg_docs_to_update_resp = sg_client.get_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs_resp, auth=seth_session)
        sg_docs_to_update = sg_docs_to_update_resp['rows']
        for sg_doc in sg_docs_to_update:
            sg_doc['content']['updates'] += 1

        # Bulk add the updates to Sync Gateway
        sg_docs_resp = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs_to_update, auth=seth_session)

    # Get docs from Sync Gateway
    sg_docs_to_update_resp = sg_client.get_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs_resp, auth=seth_session)
    sg_docs_to_update = sg_docs_to_update_resp['rows']

    # TODO: SDK: Verify doc updates (sg + sdk) are present using the doc['content']['updates'] property
    # TODO: SG: Verify doc updates (sg + sdk) are there via _all_docs using the doc['content']['updates'] property and rev prefix
    # TODO: SG: Verify doc updates (sg + sdk) are there via _changes using the doc['content']['updates'] property and rev prefix

    # Bulk add the updates to Sync Gateway
    deleted_docs = sg_client.delete_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs_to_update, auth=seth_session)
    try_get_deleted_docs = sg_client.get_bulk_docs(url=sg_url, db=sg_db, docs=deleted_docs, auth=seth_session)
    try_get_deleted_rows = try_get_deleted_docs['rows']
    # TODO: assert len(try_get_deleted_rows) == number_docs * 2

    all_doc_ids = sdk_doc_ids + sg_doc_ids
    assert len(all_doc_ids) == 2 * number_docs

    for row in try_get_deleted_rows:
        assert row['id'] in all_doc_ids
        assert row['status'] == 404
        assert row['error'] == 'not_found'
        assert row['reason'] == 'deleted'

        # Cross off the doc_id
        all_doc_ids.remove(row['id'])

    # Assert that all of the docs are flagged as deleted
    assert len(all_doc_ids) == 0

    import pdb
    pdb.set_trace()

    # Verify deleted

