import pytest
import concurrent.futures
import time

from keywords.utils import log_info
from libraries.testkit.cluster import Cluster
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import sync_gateway_config_path_for_mode

from keywords import userinfo
from keywords import document
from keywords import exceptions


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf_name, grant_type", [
    ("custom_sync/access", "CHANNEL-REST"),
    ("custom_sync/access", "CHANNEL-SYNC"),
    ("custom_sync/access", "ROLE-REST"),
    ("custom_sync/access", "ROLE-SYNC"),
    ("custom_sync/access", "CHANNEL-TO-ROLE-REST"),
    ("custom_sync/access", "CHANNEL-TO-ROLE-SYNC")
])
def test_backfill_channels_oneshot_changes(params_from_base_test_setup, sg_conf_name, grant_type):
    """
    Test that checks that docs are backfilled for one shot changes for a access grant (via REST or SYNC)

    CHANNEL-REST = Channel is granted to user via REST
    CHANNEL-SYNC = Channel is granted to user via sync function access()
    ROLE-REST = Role is granted to user via REST
    ROLE-SYNC = Role is granted to user via sync function role()
    CHANNEL-TO-ROLE-REST = Channel is added to existing role via REST
    CHANNEL-TO-ROLE-SYNC = Channel is added to existing role via sync access()
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    topology = params_from_base_test_setup["cluster_topology"]
    mode = params_from_base_test_setup["mode"]

    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_db = "db"

    log_info("grant_type: {}".format(grant_type))

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cluster = Cluster(cluster_config)
    cluster.reset(sg_conf)

    client = MobileRestClient()

    admin_user_info = userinfo.UserInfo("admin", "pass", channels=["A"], roles=[])

    if grant_type == "CHANNEL-TO-ROLE-REST" or grant_type == "CHANNEL-TO-ROLE-SYNC":
        client.create_role(url=sg_admin_url, db=sg_db, name="empty_role", channels=[])
        user_b_user_info = userinfo.UserInfo("USER_B", "pass", channels=["B"], roles=["empty_role"])
    else:
        user_b_user_info = userinfo.UserInfo("USER_B", "pass", channels=["B"], roles=[])

    # Create users / sessions
    client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=admin_user_info.name,
        password=admin_user_info.password,
        channels=admin_user_info.channels
    )

    client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=user_b_user_info.name,
        password=user_b_user_info.password,
        channels=user_b_user_info.channels,
        roles=user_b_user_info.roles
    )

    admin_session = client.create_session(
        url=sg_admin_url,
        db=sg_db,
        name=admin_user_info.name,
        password=admin_user_info.password
    )
    user_b_session = client.create_session(
        url=sg_admin_url,
        db=sg_db,
        name=user_b_user_info.name,
        password=user_b_user_info.password
    )

    # Create 50 "A" channel docs
    a_docs = client.add_docs(url=sg_url, db=sg_db, number=50, id_prefix=None, auth=admin_session, channels=["A"])
    assert len(a_docs) == 50

    b_docs = client.add_docs(url=sg_url, db=sg_db, number=1, id_prefix="b_doc", auth=user_b_session, channels=["B"])
    assert len(b_docs) == 1

    user_doc = {"id": "_user/USER_B", "rev": None}
    b_docs.append(user_doc)

    # Loop until user_b sees b_doc_0 doc and _user/USER_B doc
    client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=b_docs, auth=user_b_session, strict=True)

    # Get last_seq for user_b
    user_b_changes = client.get_changes(url=sg_url, db=sg_db, since=0, auth=user_b_session, feed="normal")

    # Grant access to channel "A"
    if grant_type == "CHANNEL-REST":
        log_info("Granting user access to channel A via Admin REST user update")
        # Grant via update to user in Admin API
        client.update_user(url=sg_admin_url, db=sg_db, name=user_b_user_info.name, channels=["A", "B"])

    elif grant_type == "CHANNEL-SYNC":
        log_info("Granting user access to channel A sync function access()")
        # Grant via access() in sync_function, then id 'channel_access' will trigger an access(doc.users, doc.channels)
        access_doc = document.create_doc("channel_access", channels=["A"])
        access_doc["users"] = ["USER_B"]
        client.add_doc(url=sg_url, db=sg_db, doc=access_doc, auth=admin_session)

    elif grant_type == "ROLE-REST":
        log_info("Granting user access to channel A via Admin REST role grant")
        # Create role with channel A
        client.create_role(url=sg_admin_url, db=sg_db, name="channel-A-role", channels=["A"])
        client.update_user(url=sg_admin_url, db=sg_db, name="USER_B", roles=["channel-A-role"])

    elif grant_type == "ROLE-SYNC":
        log_info("Granting user access to channel A via sync function role() grant")
        # Create role with channel A
        client.create_role(url=sg_admin_url, db=sg_db, name="channel-A-role", channels=["A"])

        # Grant via role() in sync_function, then id 'role_access' will trigger an role(doc.users, doc.roles)
        role_access_doc = document.create_doc("role_access")
        role_access_doc["users"] = ["USER_B"]
        role_access_doc["roles"] = ["role:channel-A-role"]
        client.add_doc(sg_url, db=sg_db, doc=role_access_doc, auth=admin_session)

    elif grant_type == "CHANNEL-TO-ROLE-REST":
        # Update the empty_role to have channel "A"
        client.update_role(url=sg_admin_url, db=sg_db, name="empty_role", channels=["A"])

    elif grant_type == "CHANNEL-TO-ROLE-SYNC":
        # Grant empty_role access to channel "A" via sync function
        # Grant channel access to role via sync function
        access_doc = document.create_doc("channel_grant_to_role")
        access_doc["roles"] = ["role:empty_role"]
        access_doc["channels"] = ["A"]
        client.add_doc(url=sg_url, db=sg_db, doc=access_doc, auth=admin_session, use_post=True)

    else:
        pytest.fail("Unsupported grant_type!!!!")

    # Issue one shot changes to make sure access grant is successful, the change may not propagate immediately so retry.
    num_retries = 3
    count = 0
    while True:
        if count == num_retries:
            raise exceptions.ChangesError("Didn't get all expected changes before timing out!")

        user_b_changes_after_grant = client.get_changes(
            url=sg_url,
            db=sg_db,
            since=user_b_changes["last_seq"],
            auth=user_b_session,
            feed="normal"
        )

        if len(user_b_changes_after_grant["results"]) > 0:
            # Found changes, break out an validate changes!
            break

        time.sleep(1)
        count += 1

    # User B shoud have recieved 51 docs (a_docs + 1 _user/USER_B doc) if a REST grant or 50 changes if the grant
    # is via the sync function
    changes_results = user_b_changes_after_grant["results"]
    assert 50 <= len(changes_results) <= 51

    # Create a dictionary of id rev pair of all the docs that are not "_user/" docs from changes
    ids_and_revs_from_user_changes = {
        change["id"]: change["changes"][0]["rev"]
        for change in changes_results if not change["id"].startswith("_user/")
    }

    assert len(ids_and_revs_from_user_changes) == 50

    # Create a list of id rev pair of all of the channel A docs
    ids_and_revs_from_a_docs = {doc["id"]: doc["rev"] for doc in a_docs}

    assert len(ids_and_revs_from_a_docs) == 50

    # Check that the changes and the a_docs are identical in id and rev
    assert ids_and_revs_from_user_changes == ids_and_revs_from_a_docs

    # Get changes from last_seq of the changes request after the grant. There should be no new changes
    user_b_changes = client.get_changes(url=sg_url, db=sg_db,
                                        since=user_b_changes_after_grant["last_seq"], auth=user_b_session, feed="normal")
    assert len(user_b_changes["results"]) == 0


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf_name, grant_type", [
    ("custom_sync/access", "CHANNEL-REST"),
    ("custom_sync/access", "CHANNEL-SYNC"),
    ("custom_sync/access", "ROLE-REST"),
    ("custom_sync/access", "ROLE-SYNC"),
    ("custom_sync/access", "CHANNEL-TO-ROLE-REST"),
    ("custom_sync/access", "CHANNEL-TO-ROLE-SYNC")
])
def test_backfill_channels_oneshot_limit_changes(params_from_base_test_setup, sg_conf_name, grant_type):
    """
    Test that checks that docs are backfilled for one shot changes with limit for a access grant (via REST or SYNC)

    CHANNEL-REST = Channel is granted to user via REST
    CHANNEL-SYNC = Channel is granted to user via sync function access()
    ROLE-REST = Role is granted to user via REST
    ROLE-SYNC = Role is granted to user via sync function role()
    CHANNEL-TO-ROLE-REST = Channel is added to existing role via REST
    CHANNEL-TO-ROLE-SYNC = Channel is added to existing role via sync access()
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    topology = params_from_base_test_setup["cluster_topology"]
    mode = params_from_base_test_setup["mode"]

    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_db = "db"

    log_info("grant_type: {}".format(grant_type))

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cluster = Cluster(cluster_config)
    cluster.reset(sg_conf)

    client = MobileRestClient()

    admin_user_info = userinfo.UserInfo("admin", "pass", channels=["A"], roles=[])

    if grant_type == "CHANNEL-TO-ROLE-REST" or grant_type == "CHANNEL-TO-ROLE-SYNC":
        client.create_role(url=sg_admin_url, db=sg_db, name="empty_role", channels=[])
        user_b_user_info = userinfo.UserInfo("USER_B", "pass", channels=["B"], roles=["empty_role"])
    else:
        user_b_user_info = userinfo.UserInfo("USER_B", "pass", channels=["B"], roles=[])

    # Create users / sessions
    client.create_user(url=sg_admin_url, db=sg_db,
                       name=admin_user_info.name, password=admin_user_info.password, channels=admin_user_info.channels)

    client.create_user(url=sg_admin_url, db=sg_db,
                       name=user_b_user_info.name, password=user_b_user_info.password, channels=user_b_user_info.channels)

    admin_session = client.create_session(url=sg_admin_url, db=sg_db, name=admin_user_info.name, password=admin_user_info.password)
    user_b_session = client.create_session(url=sg_admin_url, db=sg_db, name=user_b_user_info.name, password=user_b_user_info.password)

    # Create 50 "A" channel docs
    a_docs = client.add_docs(url=sg_url, db=sg_db, number=50, id_prefix=None, auth=admin_session, channels=["A"])
    assert len(a_docs) == 50

    b_docs = client.add_docs(url=sg_url, db=sg_db, number=1, id_prefix="b_doc", auth=user_b_session, channels=["B"])
    assert len(b_docs) == 1

    user_doc = {"id": "_user/USER_B", "rev": None}
    b_docs.append(user_doc)

    # Loop until user_b sees b_doc_0 doc and _user/USER_B doc
    client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=b_docs, auth=user_b_session, strict=True)

    # Get last_seq for user_b
    user_b_changes = client.get_changes(url=sg_url, db=sg_db, since=0, auth=user_b_session, feed="normal")

    # Grant access to channel "A"
    if grant_type == "CHANNEL-REST":
        log_info("Granting user access to channel A via Admin REST user update")
        # Grant via update to user in Admin API
        client.update_user(url=sg_admin_url, db=sg_db,
                           name=user_b_user_info.name, channels=["A", "B"])

    elif grant_type == "CHANNEL-SYNC":
        log_info("Granting user access to channel A sync function access()")
        # Grant via access() in sync_function, then id 'channel_access' will trigger an access(doc.users, doc.channels)
        access_doc = document.create_doc("channel_access", channels=["A"])
        access_doc["users"] = ["USER_B"]
        client.add_doc(url=sg_url, db=sg_db, doc=access_doc, auth=admin_session)

    elif grant_type == "ROLE-REST":
        log_info("Granting user access to channel A via Admin REST role grant")
        # Create role with channel A
        client.create_role(url=sg_admin_url, db=sg_db, name="channel-A-role", channels=["A"])
        client.update_user(url=sg_admin_url, db=sg_db, name="USER_B", roles=["channel-A-role"])

    elif grant_type == "ROLE-SYNC":
        log_info("Granting user access to channel A via sync function role() grant")
        # Create role with channel A
        client.create_role(url=sg_admin_url, db=sg_db, name="channel-A-role", channels=["A"])

        # Grant via role() in sync_function, then id 'role_access' will trigger an role(doc.users, doc.roles)
        role_access_doc = document.create_doc("role_access")
        role_access_doc["users"] = ["USER_B"]
        role_access_doc["roles"] = ["role:channel-A-role"]
        client.add_doc(sg_url, db=sg_db, doc=role_access_doc, auth=admin_session)

    elif grant_type == "CHANNEL-TO-ROLE-REST":
        # Update the empty_role to have channel "A"
        client.update_role(url=sg_admin_url, db=sg_db, name="empty_role", channels=["A"])

    elif grant_type == "CHANNEL-TO-ROLE-SYNC":
        # Grant empty_role access to channel "A" via sync function
        # Grant channel access to role via sync function
        access_doc = document.create_doc("channel_grant_to_role")
        access_doc["roles"] = ["role:empty_role"]
        access_doc["channels"] = ["A"]
        client.add_doc(url=sg_url, db=sg_db, doc=access_doc, auth=admin_session, use_post=True)

    else:
        pytest.fail("Unsupported grant_type!!!!")

    # Create a dictionary keyed on doc id for all of channel A docs
    ids_and_revs_from_a_docs = {doc["id"]: doc["rev"] for doc in a_docs}
    assert len(ids_and_revs_from_a_docs.keys()) == 50

    log_info("Doing 3, 1 shot changes with limit and last seq!")
    # Issue 3 oneshot changes with a limit of 20

    # Issue one shot changes to make sure access grant is successful, the change may not propagate immediately so retry.
    num_retries = 3
    count = 0
    while True:
        if count == num_retries:
            raise exceptions.ChangesError("Didn't get all expected changes before timing out!")

        user_b_changes_after_grant_one = client.get_changes(
            url=sg_url,
            db=sg_db,
            since=user_b_changes["last_seq"],
            auth=user_b_session,
            feed="normal",
            limit=20
        )

        if len(user_b_changes_after_grant_one["results"]) > 0:
            # Found changes, break out an validate changes!
            break

        time.sleep(1)
        count += 1

    #################
    # Changes Req #1
    #################

    # User B shoud have recieved 20 docs due to limit
    assert len(user_b_changes_after_grant_one["results"]) == 20

    for doc in user_b_changes_after_grant_one["results"]:
        # cross off keys found from 'a_docs' dictionary
        del ids_and_revs_from_a_docs[doc["id"]]

    #################
    # Changes Req #2
    #################
    user_b_changes_after_grant_two = client.get_changes(url=sg_url, db=sg_db,
                                                        since=user_b_changes_after_grant_one["last_seq"],
                                                        auth=user_b_session, feed="normal", limit=20)

    # User B shoud have recieved 20 docs due to limit
    assert len(user_b_changes_after_grant_two["results"]) == 20

    for doc in user_b_changes_after_grant_two["results"]:
        # cross off keys found from 'a_docs' dictionary
        del ids_and_revs_from_a_docs[doc["id"]]

    #################
    # Changes Req #3
    #################
    user_b_changes_after_grant_three = client.get_changes(url=sg_url, db=sg_db,
                                                          since=user_b_changes_after_grant_two["last_seq"],
                                                          auth=user_b_session, feed="normal", limit=20)

    # User B should have recieved 10 docs due to limit or 11 docs with with a terminating _user doc
    # The terminating user doc only happens with a grant via REST
    assert 10 <= len(user_b_changes_after_grant_three["results"]) <= 11

    for doc in user_b_changes_after_grant_three["results"]:
        # cross off non user doc keys found from 'a_docs' dictionary
        if not doc["id"].startswith("_user/"):
            del ids_and_revs_from_a_docs[doc["id"]]

    # Make sure all the docs have been crossed out
    assert len(ids_and_revs_from_a_docs) == 0

    #################
    # Changes Req #4
    #################
    user_b_changes_after_grant_four = client.get_changes(url=sg_url, db=sg_db,
                                                         since=user_b_changes_after_grant_three["last_seq"],
                                                         auth=user_b_session, feed="normal", limit=20)

    # Changes should be caught up and there should be no results
    assert len(user_b_changes_after_grant_four["results"]) == 0


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf_name, grant_type", [
    ("custom_sync/access", "CHANNEL-REST"),
    ("custom_sync/access", "CHANNEL-SYNC"),
    ("custom_sync/access", "ROLE-REST"),
    ("custom_sync/access", "ROLE-SYNC"),
    ("custom_sync/access", "CHANNEL-TO-ROLE-REST"),
    ("custom_sync/access", "CHANNEL-TO-ROLE-SYNC")
])
def test_backfill_awaken_channels_longpoll_changes_with_limit(params_from_base_test_setup, sg_conf_name, grant_type):
    """
    Test that checks that docs are backfilled for logpoll changes with limit for a access grant (via REST or SYNC)

    CHANNEL-REST = Channel is granted to user via REST
    CHANNEL-SYNC = Channel is granted to user via sync function access()
    ROLE-REST = Role is granted to user via REST
    ROLE-SYNC = Role is granted to user via sync function role()
    CHANNEL-TO-ROLE-REST = Channel is added to existing role via REST
    CHANNEL-TO-ROLE-SYNC = Channel is added to existing role via sync access()
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    topology = params_from_base_test_setup["cluster_topology"]
    mode = params_from_base_test_setup["mode"]

    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_db = "db"

    log_info("grant_type: {}".format(grant_type))

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cluster = Cluster(cluster_config)
    cluster.reset(sg_conf)

    client = MobileRestClient()

    admin_user_info = userinfo.UserInfo("admin", "pass", channels=["A"], roles=[])

    if grant_type == "CHANNEL-TO-ROLE-REST" or grant_type == "CHANNEL-TO-ROLE-SYNC":
        client.create_role(url=sg_admin_url, db=sg_db, name="empty_role", channels=[])
        user_b_user_info = userinfo.UserInfo("USER_B", "pass", channels=["B"], roles=["empty_role"])
    else:
        user_b_user_info = userinfo.UserInfo("USER_B", "pass", channels=["B"], roles=[])

    # Create users / sessions
    client.create_user(url=sg_admin_url, db=sg_db,
                       name=admin_user_info.name, password=admin_user_info.password, channels=admin_user_info.channels)

    client.create_user(url=sg_admin_url, db=sg_db,
                       name=user_b_user_info.name, password=user_b_user_info.password, channels=user_b_user_info.channels)

    admin_session = client.create_session(url=sg_admin_url, db=sg_db, name=admin_user_info.name, password=admin_user_info.password)
    user_b_session = client.create_session(url=sg_admin_url, db=sg_db, name=user_b_user_info.name, password=user_b_user_info.password)

    # Create 50 "A" channel docs
    a_docs = client.add_docs(url=sg_url, db=sg_db, number=50, id_prefix=None, auth=admin_session, channels=["A"])
    assert len(a_docs) == 50

    b_docs = client.add_docs(url=sg_url, db=sg_db, number=1, id_prefix="b_doc", auth=user_b_session, channels=["B"])
    assert len(b_docs) == 1

    user_doc = {"id": "_user/USER_B", "rev": None}
    b_docs.append(user_doc)

    # Loop until user_b sees b_doc_0 doc and _user/USER_B doc
    client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=b_docs, auth=user_b_session, strict=True)

    # Create a dictionary keyed on doc id for all of channel A docs
    ids_and_revs_from_a_docs = {doc["id"]: doc["rev"] for doc in a_docs}
    assert len(ids_and_revs_from_a_docs.keys()) == 50

    # Get last_seq for user_b
    user_b_changes = client.get_changes(url=sg_url, db=sg_db, since=0, auth=user_b_session, feed="normal")

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:

        # Start long poll changes feed.
        changes_task = ex.submit(
            client.get_changes,
            url=sg_url,
            db=sg_db,
            since=user_b_changes["last_seq"],
            auth=user_b_session,
            timeout=10,
            limit=20
        )

        # Grant access to channel "A"
        if grant_type == "CHANNEL-REST":
            log_info("Granting user access to channel A via Admin REST user update")
            # Grant via update to user in Admin API
            client.update_user(
                url=sg_admin_url,
                db=sg_db,
                name=user_b_user_info.name,
                channels=["A", "B"]
            )

        elif grant_type == "CHANNEL-SYNC":
            log_info("Granting user access to channel A sync function access()")
            # Grant via access() in sync_function,
            # then id 'channel_access' will trigger an access(doc.users, doc.channels)
            access_doc = document.create_doc("channel_access", channels=["A"])
            access_doc["users"] = ["USER_B"]
            client.add_doc(url=sg_url, db=sg_db, doc=access_doc, auth=admin_session)

        elif grant_type == "ROLE-REST":
            log_info("Granting user access to channel A via Admin REST role grant")
            # Create role with channel A
            client.create_role(url=sg_admin_url, db=sg_db, name="channel-A-role", channels=["A"])
            client.update_user(
                url=sg_admin_url,
                db=sg_db,
                name=user_b_user_info.name,
                roles=["channel-A-role"]
            )

        elif grant_type == "ROLE-SYNC":
            log_info("Granting user access to channel A via sync function role() grant")
            # Create role with channel A
            client.create_role(url=sg_admin_url, db=sg_db, name="channel-A-role", channels=["A"])

            # Grant via role() in sync_function, then id 'role_access' will trigger an role(doc.users, doc.roles)
            role_access_doc = document.create_doc("role_access")
            role_access_doc["users"] = ["USER_B"]
            role_access_doc["roles"] = ["role:channel-A-role"]
            client.add_doc(sg_url, db=sg_db, doc=role_access_doc, auth=admin_session)

        elif grant_type == "CHANNEL-TO-ROLE-REST":
            # Update the empty_role to have channel "A"
            client.update_role(url=sg_admin_url, db=sg_db, name="empty_role", channels=["A"])

        elif grant_type == "CHANNEL-TO-ROLE-SYNC":
            # Grant empty_role access to channel "A" via sync function
            # Grant channel access to role via sync function
            access_doc = document.create_doc("channel_grant_to_role")
            access_doc["roles"] = ["role:empty_role"]
            access_doc["channels"] = ["A"]
            client.add_doc(url=sg_url, db=sg_db, doc=access_doc, auth=admin_session, use_post=True)

        else:
            pytest.fail("Unsupported grant_type!!!!")

        # Block on return of longpoll changes, feed should wake up and return 20 results
        changes = changes_task.result()

    assert len(changes["results"]) == 20
    num_requests = 1

    # Cross the results off from the 'a_docs' dictionary
    for doc in changes["results"]:
        del ids_and_revs_from_a_docs[doc["id"]]

    # Start looping longpoll changes with limit, cross off changes from dictionary each time one is found
    # Since 20 changes should be crossed off already, this should execute 2x.
    log_info("Starting looping longpoll changes with limit!")
    last_seq = changes["last_seq"]
    while True:

        if len(ids_and_revs_from_a_docs.keys()) == 0:
            log_info("All docs were found! Exiting polling loop")
            break

        changes = client.get_changes(url=sg_url, db=sg_db, since=last_seq, auth=user_b_session, limit=20, timeout=10)
        num_requests += 1

        # There are more than 2 requests, throw an exception.
        if num_requests == 2:
            assert len(changes["results"]) == 20
        elif num_requests == 3:
            # This will be 10 or 11 depending on if the _user/ doc is returned
            assert 10 <= len(changes["results"]) <= 11
        else:
            raise exceptions.ChangesError("Looping longpoll should only have to perform 3 requests to get all the changes!!")

        # Cross the results off from the 'a_docs' dictionary.
        # This will blow up in docs duplicate docs are sent to changes
        for doc in changes["results"]:
            if doc["id"] != "_user/USER_B":
                del ids_and_revs_from_a_docs[doc["id"]]

        last_seq = changes["last_seq"]

    # Shanges after longpoll
    zero_results = client.get_changes(url=sg_url, db=sg_db,
                                      since=last_seq,
                                      auth=user_b_session, feed="normal")

    # Changes should be caught up and there should be no results
    assert len(zero_results["results"]) == 0


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.role
@pytest.mark.parametrize("sg_conf_name, grant_type, channels_to_grant", [
    ("custom_sync/access", "CHANNEL-REST", ["A"]),
    ("custom_sync/access", "CHANNEL-REST", ["A", "B", "C"]),
    ("custom_sync/access", "CHANNEL-SYNC", ["A"]),
    ("custom_sync/access", "CHANNEL-SYNC", ["A", "B", "C"])
])
def test_backfill_channel_grant_to_role_longpoll(params_from_base_test_setup, sg_conf_name, grant_type, channels_to_grant):
    """
    Test that check that docs are backfilled for a channel grant (via REST or SYNC) to existing role

    1. Create a 'grantee' user with an empty role
    2. 'pusher' user adds docs with channel(s) that will later be granted to 'grantee'
    3. Verify that the 'pusher' sees the docs on its changes feed
    4. Grant the 'grantee's role access to the pushers channels (either via REST or via sync function)
    5. Verify that 'grantee' gets all of the docs after the grant
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    topology = params_from_base_test_setup["cluster_topology"]
    mode = params_from_base_test_setup["mode"]

    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_db = "db"
    num_docs_per_channel = 100
    empty_role_name = "empty_role"

    log_info("grant_type: {}".format(grant_type))
    log_info("channels to grant access to: {}".format(channels_to_grant))

    is_multi_channel_grant = False
    if len(channels_to_grant) == 3:
        is_multi_channel_grant = True
    log_info("is_multi_channel_grant: {}".format(is_multi_channel_grant))

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cluster = Cluster(cluster_config)
    cluster.reset(sg_conf)

    client = MobileRestClient()
    client.create_role(url=sg_admin_url, db=sg_db, name=empty_role_name, channels=[])

    pusher_info = userinfo.UserInfo("pusher", "pass", channels=channels_to_grant, roles=[])
    grantee_info = userinfo.UserInfo("grantee", "pass", channels=[], roles=["empty_role"])

    # Create users
    client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=pusher_info.name,
        password=pusher_info.password,
        channels=pusher_info.channels,
        roles=pusher_info.roles
    )
    pusher_session = client.create_session(
        url=sg_admin_url,
        db=sg_db,
        name=pusher_info.name,
        password=pusher_info.password
    )

    client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=grantee_info.name,
        password=grantee_info.password,
        channels=grantee_info.channels,
        roles=grantee_info.roles
    )
    grantee_session = client.create_session(
        url=sg_admin_url,
        db=sg_db,
        name=grantee_info.name,
        password=grantee_info.password
    )

    pusher_changes = client.get_changes(url=sg_url, db=sg_db, since=0, auth=pusher_session)

    # Make sure _user docs shows up in the changes feed
    assert len(pusher_changes["results"]) == 1 and pusher_changes["results"][0]["id"] == "_user/pusher"

    # Add docs with the appropriate channels
    a_docs = client.add_docs(
        url=sg_url,
        db=sg_db,
        number=num_docs_per_channel,
        id_prefix=None,
        auth=pusher_session,
        channels=["A"]
    )
    assert len(a_docs) == 100
    expected_docs = a_docs

    if is_multi_channel_grant:
        b_docs = client.add_docs(
            url=sg_url,
            db=sg_db,
            number=num_docs_per_channel,
            id_prefix=None,
            auth=pusher_session,
            channels=["B"]
        )
        assert len(b_docs) == 100
        expected_docs += b_docs

        c_docs = client.add_docs(
            url=sg_url,
            db=sg_db,
            number=num_docs_per_channel,
            id_prefix=None,
            auth=pusher_session,
            channels=["C"]
        )
        assert len(c_docs) == 100
        expected_docs += c_docs

    # Wait for all docs to show up on the changes feed before access grant
    client.verify_docs_in_changes(
        url=sg_url,
        db=sg_db,
        expected_docs=expected_docs,
        auth=pusher_session
    )

    # Get changes for granted before grant and assert the only changes is the user doc
    grantee_changes_before_grant = client.get_changes(url=sg_url, db=sg_db, since=0, auth=grantee_session)
    assert len(grantee_changes_before_grant["results"]) == 1
    assert grantee_changes_before_grant["results"][0]["id"] == "_user/grantee"

    if grant_type == "CHANNEL-REST":
        # Grant channel access to role via REST
        client.update_role(url=sg_admin_url, db=sg_db, name=empty_role_name, channels=channels_to_grant)
    elif grant_type == "CHANNEL-SYNC":
        # Grant channel access to role via sync function
        access_doc = document.create_doc(doc_id="channel_grant_to_role")
        access_doc["roles"] = ["role:{}".format(empty_role_name)]
        access_doc["channels"] = channels_to_grant
        client.add_doc(
            url=sg_url,
            db=sg_db,
            doc=access_doc,
            auth=pusher_session,
            use_post=True
        )

    # Issue changes request after grant
    grantee_changes_post_grant = client.get_changes(
        url=sg_url,
        db=sg_db,
        since=grantee_changes_before_grant["last_seq"],
        auth=grantee_session,
        feed="longpoll"
    )

    # grantee should have all the docs now
    if is_multi_channel_grant:
        # Check that the grantee gets all of the docs for channels ["A", "B", "C"]
        assert len(grantee_changes_post_grant["results"]) == num_docs_per_channel * 3
    else:
        # Check that the grantee gets all of the docs for channels ["A"]
        assert len(grantee_changes_post_grant["results"]) == num_docs_per_channel

    # Issue one more changes request from the post grant last seq and make sure there are no other changes
    grantee_changes_post_post_grant = client.get_changes(
        url=sg_url,
        db=sg_db,
        since=grantee_changes_post_grant["last_seq"],
        auth=grantee_session,
        feed="longpoll"
    )
    assert len(grantee_changes_post_post_grant["results"]) == 0
