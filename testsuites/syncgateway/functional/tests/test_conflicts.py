import time

import pytest
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from libraries.testkit import cluster
from keywords.MobileRestClient import MobileRestClient
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf
from utilities.cluster_config_utils import get_sg_version
from concurrent.futures import ThreadPoolExecutor
from keywords.ClusterKeywords import ClusterKeywords


import keywords.exceptions
import keywords.constants

from keywords import userinfo
from keywords import document


@pytest.mark.syncgateway
@pytest.mark.conflicts
@pytest.mark.basicauth
@pytest.mark.parametrize("sg_conf_name", [
    "sync_gateway_default_functional_tests",
    "sync_gateway_allow_conflicts",
    pytest.param("sync_gateway_default_functional_tests_no_port", marks=pytest.mark.oscertify),
    "sync_gateway_default_functional_tests_couchbase_protocol_withport_11210"
])
def test_non_winning_revisions(params_from_base_test_setup, sg_conf_name):
    """ Add non-winning revisions to the revision tree and ensure
    that the changes feed returns the correct revisions

    Steps:
    - Add a doc
    - Add 5 revs
    - changes, assert rev starts with "6-" from 0, store "last_seq_1"
    - Create a conflict off first revision ("2-foo") (POST docs, new_edits == false)
    - changes, assert rev starts with "6-" from "last_seq_1", store "last_seq_2"
    - changes, assert rev starts with "6-" from 0
    - Add a "3-foo" rev with rev "2-foo" as parent
    - changes, assert rev starts with "6-" from "last_seq_2", store "last_seq_3"
    - changes, assert rev starts with "6-" from 0
    - add tombstone rev as child of "6-" i.e. issue delete on ("6-")
    - changes, assert rev starts with "3-foo" from "last_seq_3"
    - changes, assert rev starts with "3-foo" from 0
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    topology = params_from_base_test_setup["cluster_topology"]
    mode = params_from_base_test_setup["mode"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]

    if no_conflicts_enabled:
        pytest.skip('--no-conflicts is enabled, this test needs to create conflicts, so skipping the test')
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]

    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_db = "db"

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    # Skip the test if ssl disabled as it cannot run without port using http protocol
    if "sync_gateway_default_functional_tests_no_port" in sg_conf_name and get_sg_version(cluster_config) < "1.5.0":
        pytest.skip('couchbase/couchbases ports do not support for versions below 1.5')
    if "sync_gateway_default_functional_tests_no_port" in sg_conf_name and not ssl_enabled:
        pytest.skip('ssl disabled so cannot run without port')
    # Skip the test if ssl enabled as it cannot couchbase protocol
    # TODO : https://github.com/couchbaselabs/sync-gateway-accel/issues/227
    # Remove DI condiiton once above bug is fixed
    if "sync_gateway_default_functional_tests_couchbase_protocol_withport_11210" in sg_conf_name and (ssl_enabled or mode.lower() == "di"):
        pytest.skip('ssl enabled so cannot run with couchbase protocol')

    c = cluster.Cluster(cluster_config)
    c.reset(sg_conf)

    client = MobileRestClient()

    seth_user_info = userinfo.UserInfo(
        name="seth",
        password="pass",
        channels=["NATGEO"],
        roles=[]
    )

    seth_auth = client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=seth_user_info.name,
        password=seth_user_info.password,
        channels=seth_user_info.channels
    )

    test_doc_body = document.create_doc(doc_id="test_doc", channels=seth_user_info.channels)
    rev_gen_1_doc = client.add_doc(url=sg_url, db=sg_db, doc=test_doc_body, auth=seth_auth)

    rev_gen_6_doc = client.update_doc(url=sg_url, db=sg_db, doc_id=rev_gen_1_doc["id"], number_updates=5, auth=seth_auth)
    assert rev_gen_6_doc["rev"].startswith("6-")

    # Get changes until rev generation 6 document shows up
    start = time.time()
    last_seq = 0
    while True:
        if time.time() - start > keywords.constants.CLIENT_REQUEST_TIMEOUT:
            raise keywords.exceptions.TimeoutError("Wait for Replication Status Idle: TIMEOUT")

        changes_1 = client.get_changes(url=sg_url, db=sg_db, since=last_seq, auth=seth_auth, skip_user_docs=True)
        last_seq = changes_1["last_seq"]

        # break when expected rev shows up in changes feed
        if changes_1["results"] and changes_1["results"][0]["changes"][0]["rev"].startswith("6-"):
            break

    assert len(changes_1["results"]) == 1
    assert changes_1["results"][0]["id"] == "test_doc"
    assert changes_1["results"][0]["changes"][0]["rev"].startswith("6-")

    # Create a conflict off of rev one
    rev_gen_2_doc_conflict = client.add_conflict(
        url=sg_url,
        db=sg_db,
        doc_id=rev_gen_1_doc["id"],
        parent_revisions=rev_gen_1_doc["rev"],
        new_revision="2-foo",
        auth=seth_auth
    )
    assert rev_gen_2_doc_conflict["id"] == "test_doc"
    assert rev_gen_2_doc_conflict["rev"] == "2-foo"

    # Issue changes since changes_1 last_seq above
    changes_2 = client.get_changes(url=sg_url, db=sg_db, since=changes_1["last_seq"], auth=seth_auth)
    assert len(changes_2["results"]) == 1
    assert changes_2["results"][0]["id"] == "test_doc"
    assert changes_2["results"][0]["changes"][0]["rev"].startswith("6-")

    # Issue changes since 0, strip user doc and make sure the doc is still the '6-' rev
    changes_from_0_one = client.get_changes(url=sg_url, db=sg_db, since=0, auth=seth_auth, skip_user_docs=True)
    assert len(changes_from_0_one["results"]) == 1
    assert changes_from_0_one["results"][0]["id"] == "test_doc"
    assert changes_from_0_one["results"][0]["changes"][0]["rev"].startswith("6-")

    # Create a 3-foo rev with 2-foo as the parent
    rev_gen_3_doc_conflict = client.add_conflict(
        url=sg_url,
        db=sg_db,
        doc_id=rev_gen_2_doc_conflict["id"],
        parent_revisions=rev_gen_2_doc_conflict["rev"],
        new_revision="3-foo",
        auth=seth_auth
    )
    assert rev_gen_3_doc_conflict["id"] == "test_doc"
    assert rev_gen_3_doc_conflict["rev"] == "3-foo"

    # Issue changes since changes_2 last_seq above
    changes_3 = client.get_changes(url=sg_url, db=sg_db, since=changes_2["last_seq"], auth=seth_auth)
    assert len(changes_3["results"]) == 1
    assert changes_3["results"][0]["id"] == "test_doc"
    assert changes_3["results"][0]["changes"][0]["rev"].startswith("6-")

    # Issue changes since 0, strip user doc and make sure the doc is still the '6-' rev
    changes_from_0_two = client.get_changes(url=sg_url, db=sg_db, since=0, auth=seth_auth, skip_user_docs=True)
    assert len(changes_from_0_two["results"]) == 1
    assert changes_from_0_two["results"][0]["id"] == "test_doc"
    assert changes_from_0_two["results"][0]["changes"][0]["rev"].startswith("6-")

    # Delete test_doc at rev 6-*
    client.delete_doc(url=sg_url, db=sg_db, doc_id=rev_gen_6_doc["id"], rev=rev_gen_6_doc["rev"], auth=seth_auth)

    # Issue changes since changes_3 last_seq above
    changes_4 = client.get_changes(url=sg_url, db=sg_db, since=changes_3["last_seq"], auth=seth_auth)
    assert len(changes_4["results"]) == 1
    assert changes_4["results"][0]["id"] == "test_doc"
    assert changes_4["results"][0]["changes"][0]["rev"] == "3-foo"

    # Issue a oneshot changes since changes_4 last_seq and assert no results are returned
    changes_5 = client.get_changes(url=sg_url, db=sg_db, since=changes_4["last_seq"], feed="normal", auth=seth_auth)
    assert len(changes_5["results"]) == 0


@pytest.mark.syncgateway
@pytest.mark.conflicts
@pytest.mark.basicauth
@pytest.mark.parametrize("sg_conf_name, x509_cert_auth", [
    pytest.param("sync_gateway_default_functional_tests", True, marks=[pytest.mark.sanity, pytest.mark.oscertify]),
    ("sync_gateway_default_functional_tests", False)
])
def test_winning_conflict_branch_revisions(params_from_base_test_setup, sg_conf_name, x509_cert_auth):
    """ Add winning conflict revisions to the revision tree and ensure
    that the changes feed returns the correct revisions

    Steps:
    - Add a doc ('test_doc')
    - Add 5 revs to 'test_doc'
    - POST _changes, assert rev starts with "6-" from 0, store "last_seq_1"
    - Create a conflict off first revision ("2-foo") (POST docs, new_edits == false)
    - Append 5 revisions to the conflicting branch
        (3-foo with 2-foo as parent, 4-foo with 3-foo as parent ... 7-foo with 6-foo as parent)
    - GET 'test_doc' and verify that the rev is '7-foo'
    - POST _changes, assert returns 7-foo
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    topology = params_from_base_test_setup["cluster_topology"]
    mode = params_from_base_test_setup["mode"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    cbs_ce_version = params_from_base_test_setup["cbs_ce"]

    if no_conflicts_enabled:
        pytest.skip('--no-conflicts is enabled, this test needs to create conflicts, so skipping the test')

    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_db = "db"

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    disable_tls_server = params_from_base_test_setup["disable_tls_server"]
    if x509_cert_auth and disable_tls_server:
        pytest.skip("x509 test cannot run tls server disabled")
    if x509_cert_auth and not cbs_ce_version:
        temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
        persist_cluster_config_environment_prop(temp_cluster_config, 'x509_certs', True)
        persist_cluster_config_environment_prop(temp_cluster_config, 'server_tls_skip_verify', False)
        cluster_config = temp_cluster_config

    c = cluster.Cluster(cluster_config)
    c.reset(sg_conf)

    client = MobileRestClient()

    seth_user_info = userinfo.UserInfo(
        name="seth",
        password="pass",
        channels=["NATGEO"],
        roles=[]
    )

    seth_auth = client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=seth_user_info.name,
        password=seth_user_info.password,
        channels=seth_user_info.channels
    )

    test_doc_body = document.create_doc(doc_id="test_doc", channels=seth_user_info.channels)
    rev_gen_1_doc = client.add_doc(url=sg_url, db=sg_db, doc=test_doc_body, auth=seth_auth)

    rev_gen_6_doc = client.update_doc(url=sg_url, db=sg_db, doc_id=rev_gen_1_doc["id"], number_updates=5, auth=seth_auth)
    assert rev_gen_6_doc["rev"].startswith("6-")

    # Wait until doc shows up in changes feed
    last_seq = 0
    start = time.time()
    while True:

        if time.time() - start > keywords.constants.CLIENT_REQUEST_TIMEOUT:
            raise keywords.exceptions.TimeoutError("Wait for Replication Status Idle: TIMEOUT")

        changes_1 = client.get_changes(url=sg_url, db=sg_db, since=last_seq, auth=seth_auth, skip_user_docs=True)
        last_seq = changes_1["last_seq"]
        if len(changes_1["results"]) > 0 and changes_1["results"][0]["changes"][0]["rev"].startswith("6-"):
            break

    assert len(changes_1["results"]) == 1
    assert changes_1["results"][0]["id"] == "test_doc"
    assert changes_1["results"][0]["changes"][0]["rev"].startswith("6-")

    # Create a conflict off of rev one
    rev_gen_1_doc_conflict = client.add_conflict(
        url=sg_url,
        db=sg_db,
        doc_id=rev_gen_1_doc["id"],
        parent_revisions=rev_gen_1_doc["rev"],
        new_revision="2-foo",
        auth=seth_auth
    )

    # Update the conflicting branch 5x
    rev_gen = 3
    for _ in range(5):
        rev_gen_1_doc_conflict = client.add_conflict(
            url=sg_url,
            db=sg_db,
            doc_id=rev_gen_1_doc["id"],
            parent_revisions=rev_gen_1_doc_conflict["rev"],
            new_revision="{}-foo".format(rev_gen),
            auth=seth_auth
        )
        rev_gen += 1

    # Wait until doc shows up in changes feed from last_seq from where last changes loop from above left off
    start = time.time()
    while True:

        if time.time() - start > keywords.constants.CLIENT_REQUEST_TIMEOUT:
            raise keywords.exceptions.TimeoutError("Wait for Replication Status Idle: TIMEOUT")

        changes_2 = client.get_changes(url=sg_url, db=sg_db, since=last_seq, auth=seth_auth)
        last_seq = changes_2["last_seq"]
        if changes_2["results"][0]["changes"][0]["rev"] == "7-foo" and len(changes_2["results"]) > 0:
            break

    # Verify that the the "7-foo" rev is return on the changes feed
    assert len(changes_2["results"]) == 1
    assert changes_2["results"][0]["id"] == "test_doc"
    assert changes_2["results"][0]["changes"][0]["rev"] == "7-foo"


@pytest.mark.syncgateway
@pytest.mark.conflicts
@pytest.mark.parametrize("sg_conf_name, revs_limit", [
    ('sync_gateway_revs_conflict_configurable', 1),
    pytest.param('sync_gateway_revs_conflict_configurable', 19, marks=pytest.mark.oscertify),
    ('sync_gateway_revs_conflict_configurable', "\"a\""),
    ('sync_gateway_revs_conflict_configurable', -1)
    # TODO : commenting as revs_limit 0 behavior is going to change, existing behavior start sg successfully , but it will change to sg fails
    #  Enable it once behavior is changed
    # ('sync_gateway_revs_conflict_configurable', 0)
])
def test_invalid_revs_limit_with_allow_conflicts(params_from_base_test_setup, sg_conf_name, revs_limit):
    """ @summary Verify all borders of revs limit
    Test case in Excel sheet : https://docs.google.com/spreadsheets/d/1YwI_gCeoBebQKBybkzoAEoXSc0XLReszDA-mPFQapgk/edit#gid=0
    Covered Test case #2
    Steps:
    - Add a doc
    - Have allow_conflicts to true in sg config
    - Put revs_limit=1 or any number lower than 20 and restart sync-gateway
    - Verify it fails
    - change revs_limit=20 and start sync-gateway
    - Verify it starts without any error
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]

    if no_conflicts_enabled:
        pytest.skip('--no-conflicts is enabled, this test needs to create conflicts, so skipping the test')

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    clust = cluster.Cluster(cluster_config)
    clust.reset(sg_conf)
    temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
    # persist_cluster_config_environment_prop(temp_cluster_config, 'revs_limit', revs_limit, property_name_check=False)
    status = clust.sync_gateways[0].restart(config=sg_conf, cluster_config=temp_cluster_config)
    '''assert status != 0, "Syncgateway started with revs limit 1 when no conflicts disabled"

    # Now change the revs_limit to 20
    revs_limit = 20
    persist_cluster_config_environment_prop(temp_cluster_config, 'revs_limit', revs_limit, property_name_check=False)
    status = clust.sync_gateways[0].restart(config=sg_conf, cluster_config=temp_cluster_config)
    assert status == 0, "Syncgateway did not start after revs_limit changed to 20" '''


@pytest.mark.syncgateway
@pytest.mark.conflicts
@pytest.mark.oscertify
def test_concurrent_attachment_updatesonDoc(params_from_base_test_setup):
    """ @summary
    1. Create a doc
    2. Add multi process to update same doc with attachment
    3. Repeat step2 and Step 3 for few updates
    4. Verify doc with latest attachment exists on SGW and CBS
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]

    cluster_helper = ClusterKeywords(cluster_config)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_config)
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    sg_url = cluster_hosts["sync_gateways"][0]["public"]

    channel = ["concurrent-updates"]
    username = "autotest"
    password = "password"
    doc_id = "doc_1"
    sg_db = "db"
    sg_conf_name = "sync_gateway_default_functional_tests"
    sg_client = MobileRestClient()

    if no_conflicts_enabled:
        pytest.skip('--no-conflicts is enabled, this test needs to create conflicts, so skipping the test')

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    clust = cluster.Cluster(cluster_config)
    clust.reset(sg_conf)

    sg_client.create_user(sg_admin_url, sg_db, username, password=password, channels=channel)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    # 1. Create a doc
    sg_doc_body = document.create_doc(doc_id=doc_id, content="sg-doc1", channels=channel)
    sg_client.add_doc(url=sg_url, db=sg_db, doc=sg_doc_body, auth=session)

    # 2. Start one thread and update the doc with attachment
    # Update the same documents concurrently from a sync gateway client and and sdk client
    # 3. Repeat step2 and Step 3 for few updates
    with ThreadPoolExecutor(max_workers=30) as tpe:
        update_from_sg_task = tpe.submit(
            sg_client.update_doc,
            url=sg_url,
            db=sg_db,
            doc_id=doc_id,
            number_updates=10,
            auth=session,
            attachment_name="sample_text.txt"
        )

    update_from_sg_task.result()

    # 4. Verify doc with latest attachment exists on SGW and CBS
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True)["rows"]
    for doc in sg_docs:
        assert doc["doc"]["updates"] == 10, "doc did not get updated 10 times"
        try:
            doc["doc"]["_attachments"]
        except KeyError:
            assert False, "attachment is dropped"
