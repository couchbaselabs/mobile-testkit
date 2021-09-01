import time
import pytest
import subprocess
from keywords import document
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.userinfo import UserInfo
from keywords.utils import host_for_url, log_info, get_local_ip
from libraries.testkit.admin import Admin
from libraries.testkit.cluster import Cluster
from libraries.testkit.parallelize import in_parallel
from libraries.testkit.web_server import WebServer
from keywords.exceptions import TimeoutError
from keywords.constants import CLIENT_REQUEST_TIMEOUT
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf, get_cluster
from keywords.ClusterKeywords import ClusterKeywords
from keywords.couchbaseserver import get_sdk_client_with_bucket
from utilities.cluster_config_utils import copy_sgconf_to_temp, replace_string_on_sgw_config


@pytest.mark.syncgateway
@pytest.mark.webhooks
@pytest.mark.basicauth
@pytest.mark.basicsgw
@pytest.mark.parametrize("sg_conf_name, num_users, num_channels, num_docs, num_revisions, x509_cert_auth", [
    pytest.param("webhooks/webhook_offline", 5, 1, 1, 2, True, marks=[pytest.mark.sanity, pytest.mark.oscertify]),
    ("webhooks/webhook_offline", 5, 1, 1, 2, False)
])
def test_webhooks(params_from_base_test_setup, sg_conf_name, num_users, num_channels, num_docs,
                  num_revisions, x509_cert_auth):
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
    cbs_ce_version = params_from_base_test_setup["cbs_ce"]
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'test_webhooks'")
    log_info("Using cluster_conf: {}".format(cluster_conf))
    log_info("Using num_users: {}".format(num_users))
    log_info("Using num_channels: {}".format(num_channels))
    log_info("Using num_docs: {}".format(num_docs))
    log_info("Using num_revisions: {}".format(num_revisions))
    disable_tls_server = params_from_base_test_setup["disable_tls_server"]
    if x509_cert_auth and disable_tls_server:
        pytest.skip("x509 test cannot run tls server disabled")
    if x509_cert_auth and not cbs_ce_version:
        temp_cluster_config = copy_to_temp_conf(cluster_conf, mode)
        persist_cluster_config_environment_prop(temp_cluster_config, 'x509_certs', True)
        persist_cluster_config_environment_prop(temp_cluster_config, 'server_tls_skip_verify', False)
        cluster_conf = temp_cluster_config
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
    bulk = True
    in_parallel(user_objects, 'add_docs', num_docs, bulk)

    # Update docs
    log_info("Update docs")
    in_parallel(user_objects, 'update_docs', num_revisions)
    time.sleep(30)
    expected_events = (num_users * num_docs * num_revisions) + (num_users * num_docs)
    received_events = ws.get_data()
    received_doc_events = []
    for ev in received_events:
        if "_id" in ev:
            received_doc_events.append(ev)

    log_info("expected_events: {} received_events {}".format(expected_events, received_events))
    # Stop ws before asserting
    # Else successive tests will fail to start ws
    ws.stop()
    assert expected_events == len(received_doc_events)


@pytest.mark.syncgateway
@pytest.mark.session
@pytest.mark.webhooks
@pytest.mark.basicsgw
@pytest.mark.oscertify
@pytest.mark.parametrize('sg_conf_name, filtered', [
    ('webhooks/webhook', False),
    ('webhooks/webhook_filter', True)
])
def test_webhooks_crud(params_from_base_test_setup, sg_conf_name, filtered):
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

    if filtered, the scenario will add a filtered propery to every other doc.
    The webhook validation will only look for the filtered docs

    """
    xattrs_enabled = params_from_base_test_setup['xattrs_enabled']

    log_info('Webhooks filtered?: {}'.format(filtered))

    cluster_conf = params_from_base_test_setup['cluster_config']
    cluster_topology = params_from_base_test_setup['cluster_topology']
    mode = params_from_base_test_setup['mode']
    sg_admin_url = cluster_topology['sync_gateways'][0]['admin']
    sg_url = cluster_topology['sync_gateways'][0]['public']
    cbs_url = cluster_topology['couchbase_servers'][0]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]

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
    if ssl_enabled and cluster.ipv6:
        connection_url = "couchbases://{}?ssl=no_verify&ipv6=allow".format(cbs_ip)
    elif ssl_enabled and not cluster.ipv6:
        connection_url = "couchbases://{}?ssl=no_verify".format(cbs_ip)
    elif not ssl_enabled and cluster.ipv6:
        connection_url = "couchbase://{}?ipv6=allow".format(cbs_ip)
    else:
        connection_url = 'couchbase://{}'.format(cbs_ip)
    sdk_client = get_cluster(connection_url, bucket_name)
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
        name=sg_info.name
    )

    # Create sg docs
    doc_content = {'aphex': 'twin'}
    sg_docs = document.create_docs(
        doc_id_prefix='sg_user_doc',
        number=num_docs_per_client,
        content=doc_content,
        channels=sg_info.channels
    )

    # Add filtered property to every other doc
    count = 0
    for sg_doc in sg_docs:
        if count % 2 == 0:
            sg_doc['filtered'] = True
        count += 1

    sg_doc_ids = [doc['_id'] for doc in sg_docs]
    sg_filtered_doc_ids = [doc['_id'] for doc in sg_docs if 'filtered' in doc]
    assert len(sg_doc_ids) == num_docs_per_client
    assert len(sg_filtered_doc_ids) == num_docs_per_client / 2

    # Create sdk docs
    sdk_docs = {
        'sdk_user_doc_{}'.format(i): {
            'channels': sdk_info.channels,
            'content': doc_content
        }
        for i in range(num_docs_per_client)
    }

    # Add filtered property to every other doc
    count = 0
    for _, doc_val in list(sdk_docs.items()):
        if count % 2 == 0:
            doc_val['filtered'] = True
        count += 1

    sdk_doc_ids = [doc for doc in sdk_docs]
    sdk_filtered_doc_ids = [k for k, v in list(sdk_docs.items()) if 'filtered' in v]
    assert len(sdk_doc_ids) == num_docs_per_client
    assert len(sdk_filtered_doc_ids) == num_docs_per_client / 2

    all_docs = sg_doc_ids + sdk_doc_ids
    all_filtered_docs = sg_filtered_doc_ids + sdk_filtered_doc_ids
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
    if xattrs_enabled and filtered:
        poll_for_webhook_data(webhook_server, all_filtered_docs, 1, doc_content)
    elif xattrs_enabled and not filtered:
        poll_for_webhook_data(webhook_server, all_docs, 1, doc_content)
    elif not xattrs_enabled and filtered:
        poll_for_webhook_data(webhook_server, sg_filtered_doc_ids, 1, doc_content)
    else:
        poll_for_webhook_data(webhook_server, sg_doc_ids, 1, doc_content)
    webhook_server.clear_data()

    # Update sdk docs from sg
    # If xattr mode, update sdk docs from sg, update sg docs from SDK
    # If non xattr mode, update sg docs from sg
    updated_doc_content = {'brian': 'eno'}
    update_docs(
        sg_client=sg_client,
        sg_url=sg_url,
        sg_db=sg_db,
        sg_doc_ids=sg_doc_ids,
        sg_auth=sg_auth,
        sdk_client=sdk_client,
        sdk_doc_ids=sdk_doc_ids,
        updated_doc_content=updated_doc_content,
        xattrs=xattrs_enabled
    )

    # Wait for updates to trigger webhooks
    if xattrs_enabled and filtered:
        poll_for_webhook_data(webhook_server, all_filtered_docs, 2, updated_doc_content)
    elif xattrs_enabled and not filtered:
        poll_for_webhook_data(webhook_server, all_docs, 2, updated_doc_content)
    elif not xattrs_enabled and filtered:
        poll_for_webhook_data(webhook_server, sg_filtered_doc_ids, 2, updated_doc_content)
    else:
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

    # Wait for deletes to trigger webhook events, filter includes all deleted docs
    if xattrs_enabled:
        poll_for_webhook_data(webhook_server, all_docs, 3, updated_doc_content, deleted=True)
    else:
        poll_for_webhook_data(webhook_server, sg_doc_ids, 3, updated_doc_content, deleted=True)
    webhook_server.clear_data()

    # Stop webhook server
    webhook_server.stop()


@pytest.mark.syncgateway
@pytest.mark.webhooks
@pytest.mark.oscertify
def test_webhook_filter_external_js(params_from_base_test_setup, setup_webserver):
    """
    "1. Create valid js function  for import filter and host it in local machine to access jscode with http url
    webhook filter : add doc.type if doc has data with webhook filter value, otherwise add doc.type is ignore
    2. Create sgw config and point the webhook filter jsfunction to the webhook function hosted in the localmachine and can be accessed by http url
    Start sync gateway
    3. Verify SGW starts sucessfully
    4. create docs in SDK few docs with data as webhook_filter and some without non_webhook_filter data
    5. Verfiy webhook events generated and the docs with webhook filter should have in in the events
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    webhook_server = setup_webserver["webhook_server"]
    xattrs_enabled = params_from_base_test_setup["xattrs_enabled"]
    sg_conf_name = "webhooks/webhook_filter_external_js"

    if sync_gateway_version < "3.0.0" or not xattrs_enabled:
        pytest.skip("this feature cannot run with SGW version below 3.0.0 or xattrs not enabled")
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    cluster_helper = ClusterKeywords(cluster_config)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_config)
    sg_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_db = "db"
    channel = ["sgw-env-var"]
    sdk_non_webhook = "sdk_non_webhook"
    sdk_webhook = "sdk_webhook"
    sdk_webhook_docs = 7
    sdk_non_webhook_docs = 4

    cluster = Cluster(config=cluster_config)

    # Create and set up sdk client
    cbs_ip = cluster.servers[0].host
    bucket = cluster.servers[0].get_bucket_names()[0]
    sdk_client = get_sdk_client_with_bucket(ssl_enabled, cluster, cbs_ip, bucket)
    js_func_key = "\"filter\":\""
    path = "http://{}:5007/webhookFilter".format(get_local_ip())
    path = js_func_key + path + "\","
    temp_sg_config, _ = copy_sgconf_to_temp(sg_conf, mode)
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ webhook_filter }}", path)
    cluster.reset(sg_config_path=temp_sg_config)

    topology = cluster_helper.get_cluster_topology(cluster_config)

    cbs_url = topology["couchbase_servers"][0]
    sg_url = topology["sync_gateways"][0]["public"]
    sg_url_admin = topology["sync_gateways"][0]["admin"]
    sg_db = "db"

    log_info("Running 'test_attachment_revpos_when_ancestor_unavailable'")
    log_info("Using cbs_url: {}".format(cbs_url))
    log_info("Using sg_url: {}".format(sg_url))
    log_info("Using sg_url_admin: {}".format(sg_url_admin))
    log_info("Using sg_db: {}".format(sg_db))
    log_info("Using bucket: {}".format(bucket))

    # webhook_filter verification
    def update_webhook_prop():
        return {'updates': 0, 'data': 'webhook_filter'}

    def update_non_webhook_prop():
        return {'updates': 0, 'data': 'non_webhook_filter'}
    log_info('Adding {} docs via SDK ...')
    sdk_doc_bodies = document.create_docs(sdk_webhook, number=sdk_webhook_docs, content={"data": "webhook_filter"}, channels=channel, prop_generator=update_webhook_prop)
    sdk_doc_ids1 = [doc['_id'] for doc in sdk_doc_bodies]
    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    sdk_client.upsert_multi(sdk_docs)

    sdk_doc_bodies = document.create_docs(sdk_non_webhook, number=sdk_non_webhook_docs, content={"data": "non_webhook_filter"}, channels=channel)
    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    sdk_client.upsert_multi(sdk_docs)

    count = 0
    retries = 8
    while count < retries:
        data = webhook_server.get_data()
        # Remove unwanted data from the response
        for item in data:
            if "_id" not in item:
                data.remove(item)

        posted_webhook_events_ids = [item['_id'] for item in data]
        if len(posted_webhook_events_ids) < len(sdk_doc_ids1):
            time.sleep(2)
            count += 1
            continue
        else:
            break
    assert len(posted_webhook_events_ids) == len(sdk_doc_ids1)


@pytest.mark.syncgateway
@pytest.mark.webhooks
def test_webhook_filter_external_https_js(params_from_base_test_setup, setup_webserver_js_sslon):
    """
    "1. Create valid js function  for import filter and host it in local machine to access jscode with https url
    webhook filter : add doc.type if doc has data with webhook filter value, otherwise add doc.type is ignore
    2. Create sgw config and point the webhook filter jsfunction to the webhook function hosted in the localmachine and can be accessed by https url
    Start sync gateway
    3. Verify SGW starts sucessfully
    4. create docs in SDK few docs with data as webhook_filter and some without non_webhook_filter data
    5. Verify webhook events generated and the docs with webhook filter should have in in the events
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    webhook_server = setup_webserver_js_sslon["webhook_server"]
    xattrs_enabled = params_from_base_test_setup["xattrs_enabled"]
    sg_conf_name = "webhooks/webhook_filter_external_js"

    if sync_gateway_version < "3.0.0" or not xattrs_enabled:
        pytest.skip("this feature cannot run with SGW version below 3.0.0 or xattrs not enabled")

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    cluster_helper = ClusterKeywords(cluster_config)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_config)
    sg_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_db = "db"
    channel = ["sgw-env-var"]
    sdk_non_webhook = "sdk_non_webhook"
    sdk_webhook = "sdk_webhook"
    sdk_webhook_docs = 7
    sdk_non_webhook_docs = 4

    cluster = Cluster(config=cluster_config)

    # Create and set up sdk client
    cbs_ip = cluster.servers[0].host
    bucket = cluster.servers[0].get_bucket_names()[0]
    sdk_client = get_sdk_client_with_bucket(ssl_enabled, cluster, cbs_ip, bucket)
    js_func_key = "\"filter\":\""
    path = "https://{}:5007/webhookFilter".format(get_local_ip())
    path = js_func_key + path + "\","
    temp_sg_config, _ = copy_sgconf_to_temp(sg_conf, mode)
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ webhook_filter }}", path)
    cluster.reset(sg_config_path=temp_sg_config)

    topology = cluster_helper.get_cluster_topology(cluster_config)

    cbs_url = topology["couchbase_servers"][0]
    sg_url = topology["sync_gateways"][0]["public"]
    sg_url_admin = topology["sync_gateways"][0]["admin"]
    sg_db = "db"

    log_info("Running 'test_attachment_revpos_when_ancestor_unavailable'")
    log_info("Using cbs_url: {}".format(cbs_url))
    log_info("Using sg_url: {}".format(sg_url))
    log_info("Using sg_url_admin: {}".format(sg_url_admin))
    log_info("Using sg_db: {}".format(sg_db))
    log_info("Using bucket: {}".format(bucket))

    # webhook_filter verification
    def update_webhook_prop():
        return {'updates': 0, 'data': 'webhook_filter'}

    def update_non_webhook_prop():
        return {'updates': 0, 'data': 'non_webhook_filter'}
    log_info('Adding {} docs via SDK ...')
    sdk_doc_bodies = document.create_docs(sdk_webhook, number=sdk_webhook_docs, content={"data": "webhook_filter"}, channels=channel, prop_generator=update_webhook_prop)
    sdk_doc_ids1 = [doc['_id'] for doc in sdk_doc_bodies]
    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    sdk_client.upsert_multi(sdk_docs)

    sdk_doc_bodies = document.create_docs(sdk_non_webhook, number=sdk_non_webhook_docs, content={"data": "non_webhook_filter"}, channels=channel)
    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    sdk_client.upsert_multi(sdk_docs)

    count = 0
    retries = 10
    while count < retries:
        data = webhook_server.get_data()
        # Remove unwanted data from the response
        for item in data:
            if "_id" not in item:
                data.remove(item)

        posted_webhook_events_ids = [item['_id'] for item in data]
        if len(posted_webhook_events_ids) < len(sdk_doc_ids1):
            time.sleep(2)
            count += 1
            continue
        else:
            break
    assert len(posted_webhook_events_ids) == len(sdk_doc_ids1)


@pytest.fixture(scope="function")
def setup_webserver():
    webhook_server = WebServer()
    webhook_server.start()
    process = subprocess.Popen(args=["nohup", "python", "libraries/utilities/host_sgw_jscode.py", "--start", "&"], stdout=subprocess.PIPE)
    yield{
        "webhook_server": webhook_server
    }

    webhook_server.stop()
    process.kill()


@pytest.fixture(scope="function")
def setup_webserver_js_sslon():
    webhook_server = WebServer()
    webhook_server.start()
    process = subprocess.Popen(args=["nohup", "python", "libraries/utilities/host_sgw_jscode.py", "--sslstart", "&"], stdout=subprocess.PIPE)
    yield{
        "webhook_server": webhook_server
    }
    webhook_server.stop()
    process.kill()


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
        for sdk_doc in sdk_docs:
            sdk_client.upsert(sdk_doc, sdk_docs[sdk_doc])


def update_docs(sg_client, sg_url, sg_db, sg_doc_ids, sg_auth, sdk_client, sdk_doc_ids, updated_doc_content, xattrs):
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
        doc['content'] = updated_doc_content
        sg_client.put_doc(
            url=sg_url,
            db=sg_db,
            doc_id=doc_id,
            rev=doc['_rev'],
            doc_body=doc,
            auth=sg_auth
        )

    # Update sg docs from sdk in xattr mode
    if xattrs:
        for sg_user_doc_id in sg_doc_ids:
            doc = sdk_client.get(sg_user_doc_id)

            doc_body = doc.content
            doc_body['content'] = updated_doc_content

            sdk_client.upsert(sg_user_doc_id, doc_body)


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
        for sg_docid in sg_doc_ids:
            sdk_client.remove(sg_docid)


def poll_for_webhook_data(webhook_server, expected_doc_ids, expected_num_revs, expected_content, deleted=False):

    start = time.time()
    while True:

        if time.time() - start > CLIENT_REQUEST_TIMEOUT:
            webhook_server.stop()
            raise TimeoutError('Timed out waiting for webhook events!!')
        # Get web hook sent data and build a dictionary
        expected_docs_scratch_pad = list(expected_doc_ids)

        log_info('Getting posted webhook data ...')

        data = webhook_server.get_data()
        # Remove unwanted data from the response
        for item in data:
            if "_id" not in item:
                data.remove(item)

        posted_webhook_events = {item['_id']: item for item in data}
        posted_webhook_events_ids = [item['_id'] for item in data]
        posted_webhook_events_len = len(posted_webhook_events)

        # If more webhook data is sent then we are expecting, blow up
        assert posted_webhook_events_len <= len(expected_doc_ids)

        all_docs_revs_found = True

        if posted_webhook_events_len < len(expected_doc_ids):
            # We have not seen the expected number of docs yet.
            # Wait a sec and try again
            delta = set(expected_doc_ids) - set(posted_webhook_events_ids)
            log_info('Still waiting for webhook events. Expecting: {}, We have only seen: {}.  Missing: {}'.format(
                len(expected_doc_ids),
                posted_webhook_events_len,
                delta,
            ))
            all_docs_revs_found = False

        else:
            for doc_id, doc in list(posted_webhook_events.items()):

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

        time.sleep(5)
