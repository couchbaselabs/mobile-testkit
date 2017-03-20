import time

import pytest

from keywords.utils import log_info
from libraries.testkit.cluster import Cluster
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import sync_gateway_config_path_for_mode

import keywords.exceptions
from keywords import userinfo


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.basicauth
@pytest.mark.parametrize("sg_conf_name", [
    "sync_gateway_default"
])
def test_remove_add_channels_to_doc(params_from_base_test_setup, sg_conf_name):

    cluster_config = params_from_base_test_setup["cluster_config"]
    topology = params_from_base_test_setup["cluster_topology"]
    mode = params_from_base_test_setup["mode"]

    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_db = "db"

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cluster = Cluster(cluster_config)
    cluster.reset(sg_conf)

    client = MobileRestClient()

    admin_user_info = userinfo.UserInfo("admin", "pass", channels=["A", "B"], roles=[])
    a_user_info = userinfo.UserInfo("a_user", "pass", channels=["A"], roles=[])

    admin_user_auth = client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=admin_user_info.name,
        password=admin_user_info.password,
        channels=admin_user_info.channels
    )

    a_user_auth = client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=a_user_info.name,
        password=a_user_info.password,
        channels=a_user_info.channels
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
    client.verify_docs_in_changes(sg_admin_url, sg_db, expected_docs=a_docs)

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
