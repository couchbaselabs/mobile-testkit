import time

import pytest
from couchbase.bucket import Bucket

from keywords import document
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.userinfo import UserInfo
from keywords.utils import host_for_url, log_info
from libraries.testkit.admin import Admin
from libraries.testkit.cluster import Cluster
from libraries.testkit.parallelize import in_parallel
from libraries.testkit.web_server import WebServer
from keywords.exceptions import TimeoutError
from keywords.constants import CLIENT_REQUEST_TIMEOUT


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.onlineoffline
@pytest.mark.webhooks
@pytest.mark.basicauth
@pytest.mark.channel
@pytest.mark.parametrize("sg_conf_name, num_users, num_channels, num_docs, num_revisions", [
    ("webhooks/webhook_offline", 5, 1, 1, 2),
])
def test_webhooks(params_from_base_test_setup, sg_conf_name, num_users, num_channels, num_docs, num_revisions):
    """
    Scenario:
    - Start a webserver on machine running the test to recieved webhook events
    - Create users
    - Add docs to Sync Gateway
    - Update docs on Sync Gateway
    - Verify the webserver recieved all expected webhook events
    """

    start = time.time()

    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'test_webhooks'")
    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using num_users: {}".format(num_users))
    log_info("Using num_channels: {}".format(num_channels))
    log_info("Using num_docs: {}".format(num_docs))
    log_info("Using num_revisions: {}".format(num_revisions))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_conf)

    init_completed = time.time()
    log_info("Initialization completed. Time taken:{}s".format(init_completed - start))

    channels = ["channel-" + str(i) for i in range(num_channels)]
    password = "password"
    ws = WebServer()
    ws.start()

    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])

    # Register User
    log_info("Register User")
    user_objects = admin.register_bulk_users(target=sgs[0], db="db", name_prefix="User",
                                             number=num_users, password=password, channels=channels)

    # Add User
    log_info("Add docs")
    in_parallel(user_objects, 'add_docs', num_docs)

    # Update docs
    log_info("Update docs")
    in_parallel(user_objects, 'update_docs', num_revisions)
    time.sleep(30)
    expected_events = (num_users * num_docs * num_revisions) + (num_users * num_docs)
    received_events = len(ws.get_data())
    log_info("expected_events: {} received_events {}".format(expected_events, received_events))
    assert expected_events == received_events

    ws.stop()


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.xattrs
@pytest.mark.session
@pytest.mark.webhooks
@pytest.mark.parametrize('sg_conf_name', [
    'webhooks/webhook'
])
def test_webhooks_crud(params_from_base_test_setup, sg_conf_name):
    """ Tests for webhook notification on import

    The following run in non-filter / filter scenarios
    1. Start sync gateway with autoimport
    1. Write 100 docs via SDK
    1. Verify 100 webhook events (id, rev, body)
    1. Write 100 docs via SG
    1. Verify 100 webhook events (id, rev, body)
    1. Update SG docs once each via SDK
    1. Verify 100 webhook events (id, rev, body)
    1. Update SDK docs once each via SG
    1. Verify 100 webhook events (id, rev, body)
    1. Delete SG docs via SDK
    1. Verify 100 webhook events (id, rev, body)
    1. Delete SDK docs via SG
    1. Verify 100 webhook events (id, rev, body)

    to verify no dups, wait 10s after recieveing expected webhooks
    """
    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']

    cluster_conf = params_from_base_test_setup['cluster_config']
    cluster_topology = params_from_base_test_setup['cluster_topology']
    mode = params_from_base_test_setup['mode']
    sg_admin_url = cluster_topology['sync_gateways'][0]['admin']
    sg_url = cluster_topology['sync_gateways'][0]['public']
    cbs_url = cluster_topology['couchbase_servers'][0]

    sg_db = 'db'
    bucket_name = 'data-bucket'
    num_docs_per_client = 100

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_conf)

    # Start webhook server on test runner
    webhook_server = WebServer()
    webhook_server.start()

    sg_client = MobileRestClient()
    cbs_ip = host_for_url(cbs_url)
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password')

    sg_info = UserInfo('sg_user', 'pass', channels=['shared'], roles=[])
    sdk_info = UserInfo('sdk_user', 'pass', channels=['shared'], roles=[])
    sg_client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=sg_info.name,
        password=sg_info.password,
        channels=sg_info.channels
    )
    sg_user_auth = sg_client.create_session(
        url=sg_admin_url,
        db=sg_db,
        name=sg_info.name,
        password=sg_info.password
    )

    doc_content = {'aphex': 'twin'}
    seth_docs = document.create_docs(
        doc_id_prefix='sg_user_doc',
        number=num_docs_per_client,
        content=doc_content,
        channels=sg_info.channels
    )
    sg_user_doc_ids = [doc['_id'] for doc in seth_docs]
    assert len(sg_user_doc_ids) == num_docs_per_client

    # Add sg docs
    sg_user_docs = sg_client.add_bulk_docs(
        url=sg_url,
        db=sg_db,
        docs=seth_docs,
        auth=sg_user_auth
    )
    assert len(sg_user_docs) == num_docs_per_client

    # Wait for sg doc writes to trigger webhook events
    poll_for_webhook_data(webhook_server, sg_user_doc_ids, 1, doc_content)
    webhook_server.clear_data()

    # Add sdk docs
    sdk_user_docs = {
        'sdk_user_doc_{}'.format(i): {
            'channels': sdk_info.channels,
            'content': doc_content
        }
        for i in range(num_docs_per_client)
    }
    sdk_user_doc_ids = [doc for doc in sdk_user_docs]
    assert len(sdk_user_doc_ids) == num_docs_per_client
    sdk_client.upsert_multi(sdk_user_docs)

    # Wait for sdk doc imports to trigger webhook events
    poll_for_webhook_data(webhook_server, sdk_user_doc_ids, 1, doc_content)
    webhook_server.clear_data()

    updated_doc_content = {'brian': 'eno'}

    # Update sdk docs from sg
    updated_doc_body = {
        'channels': sg_info.channels,
        'content': updated_doc_content
    }
    for sdk_user_doc_id in sdk_user_doc_ids:
        doc = sg_client.get_doc(
            url=sg_url,
            db=sg_db,
            doc_id=sdk_user_doc_id,
            auth=sg_user_auth
        )
        sg_client.put_doc(
            url=sg_url,
            db=sg_db,
            doc_id=sdk_user_doc_id,
            rev=doc['_rev'],
            doc_body=updated_doc_body,
            auth=sg_user_auth
        )

    # Poll to make sure sg updates of sdk docs come through
    poll_for_webhook_data(webhook_server, sdk_user_doc_ids, 2, updated_doc_content)
    webhook_server.clear_data()

    # Update all sg docs from sdk
    for sg_user_doc_id in sg_user_doc_ids:
        sdk_client.get(sg_user_doc_id)
        sdk_client.upsert(sg_user_doc_id, updated_doc_body)

    # Wait for sdk update to sg doc imports to trigger webhook events
    poll_for_webhook_data(webhook_server, sg_user_doc_ids, 2, updated_doc_content)
    webhook_server.clear_data()

    # Delete all sdk docs from Sync Gateway
    for sdk_user_doc_id in sdk_user_doc_ids:
        doc = sg_client.get_doc(
            url=sg_url,
            db=sg_db,
            doc_id=sdk_user_doc_id,
            auth=sg_user_auth
        )
        sg_client.delete_doc(
            url=sg_url,
            db=sg_db,
            doc_id=sdk_user_doc_id,
            rev=doc['_rev'],
            auth=sg_user_auth
        )

    # Wait for sg deletes of sdk docs to trigger webhook events
    poll_for_webhook_data(webhook_server, sdk_user_doc_ids, 3, updated_doc_content, deleted=True)
    webhook_server.clear_data()

    # Delete all sg docs from sdk
    for sg_user_doc_id in sg_user_doc_ids:
        sdk_client.remove(sg_user_doc_id)

    # Wait for sdk deletes of sg docs to trigger webhook events
    poll_for_webhook_data(webhook_server, sg_user_doc_ids, 3, updated_doc_content, deleted=True)
    webhook_server.clear_data()

    webhook_server.stop()


def poll_for_webhook_data(webhook_server, expected_doc_ids, expected_num_revs, expected_content, deleted=False):

    # TODO: Verify doc body

    start = time.time()
    while True:

        if time.time() - start > CLIENT_REQUEST_TIMEOUT:
            raise TimeoutError('Timed out waiting for webhook events!!')

        # Get web hook sent data and build a dictionary
        expected_docs_scratch_pad = list(expected_doc_ids)

        log_info('Getting posted webhook data ...')

        data = webhook_server.get_data()
        posted_webhook_events = {item['_id']: item for item in data}
        posted_webhook_events_len = len(posted_webhook_events)

        # If more webhook data is sent then we are expecting, blow up
        assert posted_webhook_events_len <= len(expected_doc_ids)

        all_docs_revs_found = True

        if posted_webhook_events_len < len(expected_doc_ids):
            # We have not seen the expected number of docs yet.
            # Wait a sec and try again
            log_info('Still waiting for webhook events. Expecting: {}, We have only seen: {}'.format(
                posted_webhook_events_len,
                len(expected_doc_ids)
            ))
            all_docs_revs_found = False

        else:
            for doc_id, doc in posted_webhook_events.items():

                if deleted:
                    assert doc['_deleted']
                    assert 'content' not in doc
                else:
                    assert doc['content'] == expected_content

                if doc_id in expected_docs_scratch_pad and doc['_rev'].startswith("{}-".format(expected_num_revs)):
                    expected_docs_scratch_pad.remove(doc_id)
                else:
                    log_info('Unexpected posted webhook notification: {}'.format(doc))

            if len(expected_docs_scratch_pad) != 0:
                log_info('Missing expected revisions. Retrying ...')
                all_docs_revs_found = False

        if all_docs_revs_found:
            log_info('Found all webhook events')
            break

        time.sleep(1)
