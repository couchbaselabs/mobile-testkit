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
    sdk_docs = document.create_docs('sdk', number_docs, content={'foo': 'bar', 'updates': 1}, channels=['sdk'])
    for doc in sdk_docs:
        bucket.upsert(doc['_id'], doc)

    # Create sg user
    sg_client = MobileRestClient()
    sg_client.create_user(url=sg_admin_url, db=sg_db, name='seth', password='pass', channels=['sg', 'sdk'])
    seth_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name='seth', password='pass')

    # Create / add docs to sync gateway
    sg_docs = document.create_docs('sg', number_docs, content={'foo': 'bar', 'updates': 1}, channels=['sg'])
    sg_docs_resp = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs, auth=seth_session)
    assert len(sg_docs_resp) == number_docs

    # Since seth has channels from 'sg' and 'sdk', verify that the sdk docs and sg docs show up in
    # seth's changes feed

    # TODO: validation
    # sg_client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=sdk_docs + sg_docs, auth=seth_session)

    sdk_doc_ids = [doc["_id"] for doc in sdk_docs]
    for _ in range(number_updates):
        for sdk_doc_id in sdk_doc_ids:
            doc = bucket.get(sdk_doc_id)
            doc_body = doc.value
            update_count = doc_body['content']['updates']
            update_count += 1
            doc_body['content']['updates'] = update_count
            bucket.upsert(sdk_doc_id, doc_body)

    updated_sg_docs = sg_client.update_docs(
        url=sg_url,
        db=sg_db,
        docs=sg_docs_resp,
        number_updates=number_updates,
        auth=seth_session
    )
