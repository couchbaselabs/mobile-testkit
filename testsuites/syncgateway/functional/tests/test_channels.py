import time

import pytest

from keywords.utils import log_info
from libraries.testkit.cluster import Cluster
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.SyncGateway import SyncGateway
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf
from keywords.constants import RBAC_FULL_ADMIN

import keywords.exceptions
from keywords import userinfo
from keywords import document


@pytest.mark.syncgateway
@pytest.mark.session
@pytest.mark.channel
@pytest.mark.oscertify
@pytest.mark.parametrize('sg_conf_name', [
    'sync_gateway_default'
])
def test_channels_view_after_restart(params_from_base_test_setup, sg_conf_name):
    """
    - Add 10000 docs to Sync Gateway
    - Restart Sync Gateway (to flush channel cache)
    - Add 1 doc (to initialize the channel cache)
    - Make a changes request
    - Verify view expvar (expvar["syncGateway_changeCache"]["view_queries"]) == 1
    - Make a changes request
    - Verify view expvar (expvar["syncGateway_changeCache"]["view_queries"]) == 1
    """

    cluster_config = params_from_base_test_setup['cluster_config']
    topology = params_from_base_test_setup['cluster_topology']
    mode = params_from_base_test_setup['mode']
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]

    sg_url = topology['sync_gateways'][0]['public']
    sg_admin_url = topology['sync_gateways'][0]['admin']
    sg_db_name = 'db'
    num_docs = 10000

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cluster = Cluster(cluster_config)
    cluster.reset(sg_conf)

    client = MobileRestClient()

    seth_user_info = userinfo.UserInfo('seth', 'pass', channels=['NASA'], roles=[])

    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    client.create_user(
        url=sg_admin_url,
        db=sg_db_name,
        name=seth_user_info.name,
        password=seth_user_info.password,
        channels=seth_user_info.channels,
        auth=auth
    )

    seth_session = client.create_session(
        url=sg_admin_url,
        db=sg_db_name,
        name=seth_user_info.name,
        auth=auth
    )

    # Add docs to Sync Gateway
    doc_bodies = document.create_docs(doc_id_prefix='seth_doc', number=num_docs, channels=seth_user_info.channels)
    bulk_docs_resp = client.add_bulk_docs(url=sg_url, db=sg_db_name, docs=doc_bodies, auth=seth_session)
    assert len(bulk_docs_resp) == num_docs

    client.verify_docs_in_changes(url=sg_url, db=sg_db_name, expected_docs=bulk_docs_resp, auth=seth_session)

    # Reset sync gateway to clear channel cache
    sg = SyncGateway()
    sg.stop_sync_gateways(cluster_config=cluster_config, url=sg_url)
    sg.start_sync_gateways(cluster_config=cluster_config, url=sg_url, config=sg_conf)

    # Add 1 doc to Sync Gateway (to initialize the channel cache)
    doc_bodies = document.create_docs(doc_id_prefix='doc_new', number=1, channels=seth_user_info.channels)
    bulk_docs_resp_new = client.add_bulk_docs(url=sg_url, db=sg_db_name, docs=doc_bodies, auth=seth_session)
    assert len(bulk_docs_resp_new) == 1

    # Changes request to trigger population of channel cache with view call
    bulk_docs_resp += bulk_docs_resp_new
    client.verify_docs_in_changes(url=sg_url, db=sg_db_name, expected_docs=bulk_docs_resp, auth=seth_session)

    # Get Sync Gateway Expvars
    expvars = client.get_expvars(url=sg_admin_url, auth=auth)

    # Only check the view querys if in channel cache mode
    if mode == 'cc':
        log_info('Looking for view queries == 1 in expvars')
        if sync_gateway_version < "3.0.0":
            assert expvars['syncGateway_changeCache']['view_queries'] == 3
        else:
            assert expvars['syncgateway']['per_db'][sg_db_name]['cache']['view_queries'] == 3

    # Issue a second changes request that shouldn't trigger a view call
    client.verify_docs_in_changes(url=sg_url, db=sg_db_name, expected_docs=bulk_docs_resp, auth=seth_session)

    # Get Sync Gateway Expvars
    expvars = client.get_expvars(url=sg_admin_url, auth=auth)

    # Only check the view querys if in channel cache mode
    if mode == 'cc':
        log_info('Looking for view queries == 1 in expvars')
        if sync_gateway_version < "3.0.0":
            assert expvars['syncGateway_changeCache']['view_queries'] == 5
        else:
            assert expvars['syncgateway']['per_db'][sg_db_name]['cache']['view_queries'] == 5


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.basicauth
@pytest.mark.channel
@pytest.mark.oscertify
@pytest.mark.parametrize("sg_conf_name, x509_cert_auth", [
    ("sync_gateway_default", False),
])
def test_remove_add_channels_to_doc(params_from_base_test_setup, sg_conf_name, x509_cert_auth):
    cluster_config = params_from_base_test_setup["cluster_config"]
    topology = params_from_base_test_setup["cluster_topology"]
    mode = params_from_base_test_setup["mode"]
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]

    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_db = "db"

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    disable_tls_server = params_from_base_test_setup["disable_tls_server"]
    if x509_cert_auth and disable_tls_server:
        pytest.skip("x509 test cannot run tls server disabled")
    if x509_cert_auth:
        temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
        persist_cluster_config_environment_prop(temp_cluster_config, 'x509_certs', True)
        persist_cluster_config_environment_prop(temp_cluster_config, 'server_tls_skip_verify', False)
        cluster_config = temp_cluster_config

    cluster = Cluster(cluster_config)
    cluster.reset(sg_conf)

    client = MobileRestClient()

    admin_user_info = userinfo.UserInfo("admin", "pass", channels=["A", "B"], roles=[])
    a_user_info = userinfo.UserInfo("a_user", "pass", channels=["A"], roles=[])

    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    admin_user_auth = client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=admin_user_info.name,
        password=admin_user_info.password,
        channels=admin_user_info.channels,
        auth=auth
    )

    a_user_auth = client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=a_user_info.name,
        password=a_user_info.password,
        channels=a_user_info.channels,
        auth=auth
    )

    a_docs = client.add_docs(
        url=sg_url,
        db=sg_db,
        number=50,
        id_prefix="a_doc",
        auth=admin_user_auth,
        channels=admin_user_info.channels
    )

    # Build dictionay of a_docs
    a_docs_id_rev = {doc["id"]: doc["rev"] for doc in a_docs}
    assert len(a_docs_id_rev) == 50

    # Wait for all docs to show up in changes
    client.verify_doc_id_in_changes(sg_url, sg_db, expected_doc_id="_user/a_user", auth=a_user_auth)
    client.verify_docs_in_changes(sg_url, sg_db, expected_docs=a_docs, auth=a_user_auth)

    # Wait for all docs to also show up on admin changes feed
    # Reproduces https://github.com/couchbaselabs/sync-gateway-accel/issues/68
    client.verify_docs_in_changes(sg_admin_url, sg_db, expected_docs=a_docs, auth=auth)

    # Get changes for 'a_user'
    a_user_changes = client.get_changes(url=sg_url, db=sg_db, since=0, auth=a_user_auth, feed="normal")

    # 'a_user' should get 50 'a_doc_*' doc and 1 '_user/a_user' doc
    assert len(a_user_changes["results"]) == 51

    ###########################
    # Remove Channels from doc
    ###########################

    # Copy a_docs_id_rev to dictionary to scratch off values
    remove_docs_scratch_off = a_docs_id_rev.copy()
    assert len(remove_docs_scratch_off) == 50

    # Use admin user to update the docs to remove 'A' from the channels property on the doc and add 'B'
    client.update_docs(url=sg_url, db=sg_db, docs=a_docs, number_updates=1, auth=admin_user_auth, channels=['B'])

    # Longpoll loop requires due to the delay that changes take to permeate to the client
    changes_timeout = 10
    start = time.time()
    last_seq = a_user_changes["last_seq"]
    while True:

        # If take longer than 10 seconds, fail the test
        if time.time() - start > changes_timeout:
            raise keywords.exceptions.TimeoutException("Could not find all expected docs in changs feed")

        # We found everything, exit loop!
        if remove_docs_scratch_off == {}:
            log_info("All expected docs found to be removed")
            break

        # Get changes for 'a_user' from last_seq
        a_user_changes = client.get_changes(url=sg_url, db=sg_db, since=last_seq, auth=a_user_auth, timeout=10)
        assert len(a_user_changes["results"]) > 0

        # Loop over changes found and perform the following
        #   1. Check that the docs is flagged with 'removed'
        #   2. Cross off the doc fromt the the 'remove_docs_scratch_off'
        for change in a_user_changes["results"]:
            assert change["removed"] == ["A"]
            assert change["changes"][0]["rev"].startswith("2-")
            # This will blow up if any change is not found in that dictionary
            del remove_docs_scratch_off[change["id"]]

        # Update last_seq
        last_seq = a_user_changes["last_seq"]

    # Issue changes request from 'last_seq' and verify that the changes are up to date and returns no results
    a_user_changes = client.get_changes(url=sg_url, db=sg_db, since=last_seq, auth=a_user_auth, feed="normal")
    assert len(a_user_changes["results"]) == 0

    #########################
    # Add Channels to doc
    #########################

    # Copy the a_docs_id_rev dictionary for scratch ovee
    add_docs_scratch_off = a_docs_id_rev.copy()
    assert len(add_docs_scratch_off) == 50

    # Use admin user to update the docs to add ['A'] back to document channels
    client.update_docs(url=sg_url, db=sg_db, docs=a_docs, number_updates=1, auth=admin_user_auth, channels=["A"])

    # Longpoll loop requires due to the delay that changes take to permeate to the client
    changes_timeout = 10
    start = time.time()
    last_seq = a_user_changes["last_seq"]
    while True:

        # If take longer than 10 seconds, fail the test
        if time.time() - start > changes_timeout:
            raise keywords.exceptions.TimeoutException("Could not find all expected docs in changs feed")

        # We found everything, exit loop!
        if add_docs_scratch_off == {}:
            log_info("All expected docs found to be removed")
            break

        # Get changes for 'a_user' from last_seq
        a_user_changes = client.get_changes(url=sg_url, db=sg_db, since=last_seq, auth=a_user_auth, timeout=10)
        assert len(a_user_changes["results"]) > 0

        # Loop over changes found and perform the following
        #   1. Check that the docs has a 3rd gen rev prefix
        #   2. Cross off the doc fromt the the 'add_docs_scratch_off'
        for change in a_user_changes["results"]:
            assert change["changes"][0]["rev"].startswith("3-")
            # This will blow up if any change is not found in that dictionary
            del add_docs_scratch_off[change["id"]]

        # Update last_seq
        last_seq = a_user_changes["last_seq"]

    # Issue changes request from 'last_seq' and verify that the changes are up to date and returns no results
    a_user_changes = client.get_changes(url=sg_url, db=sg_db, since=last_seq, auth=a_user_auth, feed="normal")
    assert len(a_user_changes["results"]) == 0
