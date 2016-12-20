import time

import pytest
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from libraries.testkit import cluster
from keywords.MobileRestClient import MobileRestClient

import keywords.exceptions
import keywords.constants

from keywords import userinfo
from keywords import document



@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.conflicts
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf_name", [
    "sync_gateway_default_functional_tests"
])
def test_non_winning_revisions(params_from_base_test_setup, sg_conf_name):
    """ Add non-winning revisions to the revision tree and ensure
    that the changes feed returns the correct revisions

    Steps:
    - Create a doc
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

    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_db = "db"

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

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


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.conflicts
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf_name", [
    "sync_gateway_default_functional_tests"
])
def test_winning_conflict_branch_revisions(params_from_base_test_setup, sg_conf_name):
    """ Add winning conflict revisions to the revision tree and ensure
    that the changes feed returns the correct revisions

    Steps:
    - Create a doc ('test_doc')
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

    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_db = "db"

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

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
        if len(changes_2["results"]) > 0:
            break

    # Verify that the the "7-foo" rev is return on the changes feed
    assert len(changes_2["results"]) == 1
    assert changes_2["results"][0]["id"] == "test_doc"
    assert changes_2["results"][0]["changes"][0]["rev"] == "7-foo"
