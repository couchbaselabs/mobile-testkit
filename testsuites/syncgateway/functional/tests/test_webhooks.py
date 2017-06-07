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

    xattr mode
    1. Start sync gateway with autoimport

    1. Write 'num_docs_per_client' docs via SDK
    1. Write 'num_docs_per_client' docs via SG
    1. Verify 'num_docs_per_client' * 2 webhook events (id, rev, body)

    1. Update SG docs once each via SDK
    1. Update SDK docs once each via SG
    1. Verify 'num_docs_per_client' * 2 webhook events (id, rev, body)

    1. Delete SG docs via SDK
    1. Delete SDK docs via SG
    1. Verify 'num_docs_per_client' * 2 webhook events (id, rev, body)

    to verify no dups, wait 10s after recieveing expected webhooks

    docmeta mode
    1. Write 'num_docs_per_client' docs via SG
    1. Verify 'num_docs_per_client' webhook events (id, rev, body)

    1. Update SG docs once each via SG
    1. Verify 'num_docs_per_client' webhook events (id, rev, body)

    1. Delete SG docs via SG
    1. Verify 'num_docs_per_client' webhook events (id, rev, body)
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
    sg_auth = sg_client.create_session(
        url=sg_admin_url,
        db=sg_db,
        name=sg_info.name,
        password=sg_info.password
    )

    # Create sg docs
    doc_content = {'aphex': 'twin'}
    sg_docs = document.create_docs(
        doc_id_prefix='sg_user_doc',
        number=num_docs_per_client,
        content=doc_content,
        channels=sg_info.channels
    )
    sg_doc_ids = [doc['_id'] for doc in sg_docs]
    assert len(sg_doc_ids) == num_docs_per_client

    # Create sdk docs
    sdk_docs = {
        'sdk_user_doc_{}'.format(i): {
            'channels': sdk_info.channels,
            'content': doc_content
        }
        for i in range(num_docs_per_client)
    }
    sdk_doc_ids = [doc for doc in sdk_docs]
    assert len(sdk_doc_ids) == num_docs_per_client

    all_docs = sg_doc_ids + sdk_doc_ids
    assert len(all_docs) == num_docs_per_client * 2

    # If xattr mode, add sg + sdk docs
    # If non xattr mode, add sg docs
    add_docs(
        sg_client=sg_client,
        sg_url=sg_url,
        sg_db=sg_db,
        sg_docs=sg_docs,
        sg_auth=sg_auth,
        sdk_client=sdk_client,
        sdk_docs=sdk_docs,
        num_docs_per_client=num_docs_per_client,
        xattrs=xattrs_enabled
    )

    # Wait for added docs to trigger webhooks
    if xattrs_enabled:
        poll_for_webhook_data(webhook_server, all_docs, 1, doc_content)
    else:
        poll_for_webhook_data(webhook_server, sg_doc_ids, 1, doc_content)
    webhook_server.clear_data()

    # Update sdk docs from sg
    updated_doc_content = {'brian': 'eno'}
    updated_doc_body = {
        'channels': sg_info.channels,
        'content': updated_doc_content
    }
    update_docs(
        sg_client=sg_client,
        sg_url=sg_url,
        sg_db=sg_db,
        sg_doc_ids=sg_doc_ids,
        sg_auth=sg_auth,
        sdk_client=sdk_client,
        sdk_doc_ids=sdk_doc_ids,
        updated_doc_body=updated_doc_body,
        xattrs=xattrs_enabled
    )

    if xattrs_enabled:
        # Poll to make sure sg + sdk updates come through
        poll_for_webhook_data(webhook_server, all_docs, 2, updated_doc_content)
    else:
        # Poll to make sure sg updates come through
        poll_for_webhook_data(webhook_server, sg_doc_ids, 2, updated_doc_content)
    webhook_server.clear_data()

    delete_docs(
        sg_client=sg_client,
        sg_url=sg_url,
        sg_db=sg_db,
        sg_doc_ids=sg_doc_ids,
        sg_auth=sg_auth,
        sdk_client=sdk_client,
        sdk_doc_ids=sdk_doc_ids,
        xattrs=xattrs_enabled
    )

    # Wait for sg deletes of sdk docs to trigger webhook events
    if xattrs_enabled:
        # Poll to make sure sg + sdk deletes come through
        poll_for_webhook_data(webhook_server, all_docs, 3, updated_doc_content, deleted=True)
    else:
        poll_for_webhook_data(webhook_server, sg_doc_ids, 3, updated_doc_content, deleted=True)

    webhook_server.clear_data()
    webhook_server.stop()


def add_docs(sg_client, sg_url, sg_db, sg_docs, sg_auth, sdk_client, sdk_docs, num_docs_per_client, xattrs):
    """ Add docs
    
    if in xattr mode:
        - add num_docs_per_client docs from sg
        - add num_docs_per_client docs from sdk
    else:
        - add num_docs_per_client docs from sg
    """

    # Create sync gateway docs
    log_info('Adding sg docs ...')
    sg_user_docs = sg_client.add_bulk_docs(
        url=sg_url,
        db=sg_db,
        docs=sg_docs,
        auth=sg_auth
    )
    assert len(sg_user_docs) == num_docs_per_client

    if xattrs:
        log_info('Adding sdk docs ...')
        sdk_client.upsert_multi(sdk_docs)


def update_docs(sg_client, sg_url, sg_db, sg_doc_ids, sg_auth, sdk_client, sdk_doc_ids, updated_doc_body, xattrs):
    """ Update docs

    if in xattr mode:
        - sync gateway will update the sdk docs
        - sdk will update the sync gateway docs
    else:
        - sync gateway will update the sync gateway docs
    """

    sg_doc_ids_to_update = sg_doc_ids
    if xattrs:
        sg_doc_ids_to_update = sdk_doc_ids

    for doc_id in sg_doc_ids_to_update:
        doc = sg_client.get_doc(
            url=sg_url,
            db=sg_db,
            doc_id=doc_id,
            auth=sg_auth
        )
        sg_client.put_doc(
            url=sg_url,
            db=sg_db,
            doc_id=doc_id,
            rev=doc['_rev'],
            doc_body=updated_doc_body,
            auth=sg_auth
        )

    # Update sg docs from sdk in xattr mode
    if xattrs:
        for sg_user_doc_id in sg_doc_ids:
            sdk_client.get(sg_user_doc_id)
            sdk_client.upsert(sg_user_doc_id, updated_doc_body)


def delete_docs(sg_client, sg_url, sg_db, sg_doc_ids, sg_auth, sdk_client, sdk_doc_ids, xattrs):
    """ Delete docs

    if in xattr mode:
        - sync gateway will delete the sdk docs
        - sdk will delete the sync gateway docs
    else:
        - sync gateway will delete the sync gateway docs
    """

    sg_doc_ids_to_delete = sg_doc_ids
    if xattrs:
        sg_doc_ids_to_delete = sdk_doc_ids

    # Delete docs from Sync Gateway
    for doc_id in sg_doc_ids_to_delete:
        doc = sg_client.get_doc(
            url=sg_url,
            db=sg_db,
            doc_id=doc_id,
            auth=sg_auth
        )
        sg_client.delete_doc(
            url=sg_url,
            db=sg_db,
            doc_id=doc_id,
            rev=doc['_rev'],
            auth=sg_auth
        )

    if xattrs:
        # Delete all sg docs from sdk
        sdk_client.remove_multi(sg_doc_ids)


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
                len(expected_doc_ids),
                posted_webhook_events_len
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
