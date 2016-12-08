import pytest
import concurrent.futures

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
    ("custom_sync/access", "ROLE-SYNC")
])
def test_backfill_channels_oneshot_changes(params_from_base_test_setup, sg_conf_name, grant_type):

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

    else:
        pytest.fail("Unsupported grant_type!!!!")

    user_b_changes_after_grant = client.get_changes(url=sg_url, db=sg_db,
                                                    since=user_b_changes["last_seq"], auth=user_b_session, feed="normal")

    # User B shoud have recieved 51 docs (a_docs + 1 _user/USER_B doc) if a REST grant or 50 changes if the grant
    # is via the sync function
    changes_results = user_b_changes_after_grant["results"]
    assert 50 <= len(changes_results) <= 51

    # Create a list of id rev pair of all the docs that are not "_user/" docs from changes
    ids_and_revs_from_user_changes = [
        {"id": change["id"], "rev": change["changes"][0]["rev"]}
        for change in changes_results if not change["id"].startswith("_user/")
    ]
    assert len(ids_and_revs_from_user_changes) == 50

    # Create a list of id rev pair of all of the channel A docs
    ids_and_revs_from_a_docs = [
        {"id": doc["id"], "rev": doc["rev"]} for doc in a_docs
    ]
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
    ("custom_sync/access", "ROLE-SYNC")
])
def test_backfill_channels_oneshot_limit_changes(params_from_base_test_setup, sg_conf_name, grant_type):

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

    else:
        pytest.fail("Unsupported grant_type!!!!")

    # Create a dictionary keyed on doc id for all of channel A docs
    ids_and_revs_from_a_docs = {doc["id"]: doc["rev"] for doc in a_docs}
    assert len(ids_and_revs_from_a_docs.keys()) == 50

    log_info("Doing 3, 1 shot changes with limit and last seq!")
    # Issue 3 oneshot changes with a limit of 20

    #################
    # Changes Req #1
    #################
    user_b_changes_after_grant_one = client.get_changes(url=sg_url, db=sg_db,
                                                        since=user_b_changes["last_seq"], auth=user_b_session, feed="normal", limit=20)

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

    import pdb
    pdb.set_trace()

    #################
    # Changes Req #3
    #################
    user_b_changes_after_grant_three = client.get_changes(url=sg_url, db=sg_db,
                                                          since=user_b_changes_after_grant_two["last_seq"],
                                                          auth=user_b_session, feed="normal", limit=20)

    # User B shoud have recieved 20 docs due to limit
    assert len(user_b_changes_after_grant_three["results"]) == 10

    for doc in user_b_changes_after_grant_three["results"]:
        # cross off keys found from 'a_docs' dictionary
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
    ("custom_sync/access", "ROLE-SYNC")
])
def test_backfill_channels_looping_longpoll_changes(params_from_base_test_setup, sg_conf_name, grant_type):

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

    with concurrent.futures.ProcessPoolExecutor() as ex:

        # Start long poll changes feed.
        changes_task = ex.submit(client.get_changes,
                                 url=sg_url, db=sg_db, since=user_b_changes["last_seq"], auth=user_b_session, timeout=10, limit=20)

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
