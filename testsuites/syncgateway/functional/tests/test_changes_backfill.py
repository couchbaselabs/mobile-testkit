import pytest
import pdb

from keywords.utils import log_info
from libraries.testkit.cluster import Cluster
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import sync_gateway_config_path_for_mode

from keywords import userinfo
from keywords import document


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.attachments
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

    # User B shoud have recieved 51 docs (a_docs + 1 _user/USER_B doc)
    # TODO: Find out why no user doc for sync function grant?
    changes_results = user_b_changes_after_grant["results"]
    assert len(changes_results) == 51

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

