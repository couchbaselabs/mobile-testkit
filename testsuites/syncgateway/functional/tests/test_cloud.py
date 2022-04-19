import pytest
import time

# from requests.exceptions import HTTPError

from keywords import exceptions
from keywords import userinfo

from keywords.utils import log_info
from keywords.ClusterKeywords import ClusterKeywords
from keywords.constants import RBAC_FULL_ADMIN
from keywords.MobileRestClient import MobileRestClient
# from keywords.SyncGateway import SyncGateway
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.SyncGateway import SyncGateway

from requests import Session

from keywords import couchbaseserver
from keywords import document
from keywords import attachment
from libraries.testkit.cluster import Cluster
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf
from requests.auth import HTTPBasicAuth
# from utilities.cluster_config_utils import is_ipv6\


# Row 2 of https://docs.google.com/spreadsheets/d/15MdEneeLGENRjqPTFE9MTsDnbBGaV1wk9Rl-XVjvKJ4/edit#gid=0
@pytest.mark.cloud
@pytest.mark.parametrize("sg_conf_name", [
    "sync_gateway_default"
])
def test_writing_attachment_to_couchbase_server(params_from_base_test_setup, sg_conf_name):
    """
    1. Start sync_gateway with sync function that rejects all writes:
    function(doc, oldDoc) {
      throw({forbidden:"No writes!"});
    }
    2. Create a doc with attachment
    3. Use CBS sdk to see if attachment doc exists.  Doc ID will look like _sync:att:sha1-Kq5sNclPz7QV2+lfQIuc6R7oRu0= (where the suffix is the digest)
    4. Assert att doc does not exist
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cluster_helper = ClusterKeywords(cluster_config)
    # cluster_helper.reset_cluster(cluster_config, sg_conf)
    cluster = Cluster(config=cluster_config)

    topology = cluster_helper.get_cluster_topology(cluster_config)

    cbs_url = topology["couchbase_servers"][0]
    sg_url = topology["sync_gateways"][0]["public"]
    sg_url_admin = topology["sync_gateways"][0]["admin"]
    sg_db = "db"
    bucket = "data-bucket"

    log_info("Running 'test_writing_attachment_to_couchbase_server'")
    log_info("Using cbs_url: {}".format(cbs_url))
    log_info("Using sg_url: {}".format(sg_url))
    log_info("Using sg_url_admin: {}".format(sg_url_admin))
    log_info("Using sg_db: {}".format(sg_db))
    log_info("Using bucket: {}".format(bucket))

    sg_user_name = "sg_user"
    sg_user_password = "sg_user_password"

    sg_user_channels = ["NBC"]

    client = MobileRestClient()

    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    client.create_user(url=sg_url_admin, db=sg_db, name=sg_user_name, password=sg_user_password, channels=sg_user_channels, auth=auth)
    sg_user_session = client.create_session(url=sg_url_admin, db=sg_db, name=sg_user_name, auth=auth)

    docs = client.add_docs(url=sg_url, db=sg_db, number=100, id_prefix=sg_db, channels=sg_user_channels, auth=sg_user_session)
    assert len(docs) == 100

    # Create doc with attachment and push to sync_gateway
    atts = attachment.load_from_data_dir(["sample_text.txt"])
    doc_with_att = document.create_doc(doc_id="att_doc", content={"sample_key": "sample_val"}, attachments=atts, channels=sg_user_channels)

    client.add_doc(url=sg_url, db=sg_db, doc=doc_with_att, auth=sg_user_session)
    server = couchbaseserver.CouchbaseServer(cbs_url)

    # Assert that the attachment doc gets written to couchbase server
    if sync_gateway_version >= "3.0.0":
        server_att_docs = server.get_server_docs_with_prefix(bucket=bucket, prefix="_sync:att2:", ipv6=cluster.ipv6)
    else:
        server_att_docs = server.get_server_docs_with_prefix(bucket=bucket, prefix="_sync:att:", ipv6=cluster.ipv6)
    num_att_docs = len(server_att_docs)
    assert num_att_docs == 1


# Row 5 of https://docs.google.com/spreadsheets/d/15MdEneeLGENRjqPTFE9MTsDnbBGaV1wk9Rl-XVjvKJ4/edit#gid=0
@pytest.mark.cloud
@pytest.mark.parametrize("sg_conf_name, x509_cert_auth", [
    ("sync_gateway_default", False),
])
def test_deleted_docs_from_changes_active_only(params_from_base_test_setup, sg_conf_name, x509_cert_auth):
    """
    https://github.com/couchbase/sync_gateway/issues/2955
    1. Create a document
    2. Delete the document
    3. Restart Sync Gateway (to force rebuild of cache from view)
    4. Issue an active_only=true changes request
    5. Issue an active_only=false changes request
    The deleted document was not being included in the result set in step 5.
    """
    cluster_config = params_from_base_test_setup["cluster_config"]
    topology = params_from_base_test_setup["cluster_topology"]
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_db = "db"
    num_docs = 10
    mode = params_from_base_test_setup["mode"]
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

    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    # Add doc to SG
    added_doc = client.add_docs(
        url=sg_admin_url,
        db=sg_db,
        number=num_docs,
        id_prefix="test_changes",
        auth=auth
    )

    # Delete 1 doc
    doc_id = added_doc[0]["id"]
    log_info("Deleting {}".format(doc_id))
    doc = client.get_doc(url=sg_admin_url, db=sg_db, doc_id=doc_id, auth=auth)
    doc_rev = doc['_rev']
    client.delete_doc(sg_admin_url, sg_db, doc_id, doc_rev, auth=auth)

    # Restart SG
    sg_obj = SyncGateway()
    sg_obj.restart_sync_gateways(cluster_config)

    # Changes request with active_only=true
    session = Session()
    if auth:
        session.auth = HTTPBasicAuth(auth[0], auth[1])
    request_url = "{}/{}/_changes?active_only=true".format(sg_admin_url, sg_db)
    log_info("Issuing changes request {}".format(request_url))
    resp = session.get(request_url)
    resp.raise_for_status()
    resp_obj = resp.json()
    log_info("Checking that the deleted doc is not included in the active_only=true changes request")
    for d in resp_obj["results"]:
        assert doc_id not in d

    # Changes request with active_only=false
    request_url = "{}/{}/_changes?active_only=false".format(sg_admin_url, sg_db)
    log_info("Issuing changes request {}".format(request_url))
    resp = session.get(request_url)
    resp.raise_for_status()
    resp_obj = resp.json()
    doc_found = False
    for d in resp_obj["results"]:
        if doc_id != d["id"]:
            continue
        else:
            assert doc_id == d["id"]
            assert d["deleted"]
            doc_found = True
            break

    log_info("Checking that the deleted doc is included in the active_only=false changes request")
    assert doc_found


# Row 6 of https://docs.google.com/spreadsheets/d/15MdEneeLGENRjqPTFE9MTsDnbBGaV1wk9Rl-XVjvKJ4/edit#gid=0
@pytest.mark.cloud
@pytest.mark.parametrize("sg_conf_name, grant_type, x509_cert_auth", [
    ("custom_sync/access", "CHANNEL-SYNC", False)
])
def test_backfill_channels_oneshot_changes(params_from_base_test_setup, sg_conf_name, grant_type, x509_cert_auth):
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
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]

    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_db = "db"

    log_info("grant_type: {}".format(grant_type))

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
    # cluster.reset(sg_conf)

    client = MobileRestClient()

    admin_user_info = userinfo.UserInfo("admin", "pass", channels=["A"], roles=[])
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None

    if grant_type == "CHANNEL-TO-ROLE-REST" or grant_type == "CHANNEL-TO-ROLE-SYNC":
        client.create_role(url=sg_admin_url, db=sg_db, name="empty_role", channels=[], auth=auth)
        user_b_user_info = userinfo.UserInfo("USER_B", "pass", channels=["B"], roles=["empty_role"])
    else:
        user_b_user_info = userinfo.UserInfo("USER_B", "pass", channels=["B"], roles=[])

    # Create users / sessions
    client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=admin_user_info.name,
        password=admin_user_info.password,
        channels=admin_user_info.channels,
        auth=auth
    )

    client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=user_b_user_info.name,
        password=user_b_user_info.password,
        channels=user_b_user_info.channels,
        roles=user_b_user_info.roles,
        auth=auth
    )

    admin_session = client.create_session(
        url=sg_admin_url,
        db=sg_db,
        name=admin_user_info.name,
        auth=auth
    )
    user_b_session = client.create_session(
        url=sg_admin_url,
        db=sg_db,
        name=user_b_user_info.name,
        auth=auth
    )

    # Create 50 "A" channel docs
    a_docs = client.add_docs(url=sg_url, db=sg_db, number=50, id_prefix=None, auth=admin_session, channels=["A"])
    assert len(a_docs) == 50

    b_docs = client.add_docs(url=sg_url, db=sg_db, number=1, id_prefix="b_doc", auth=user_b_session, channels=["B"])
    assert len(b_docs) == 1

    user_doc = {"id": "_user/USER_B", "rev": None}
    b_docs.append(user_doc)

    # Loop until admin user sees docs in changes
    client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=a_docs, auth=admin_session)

    # Loop until user_b sees b_doc_0 doc and _user/USER_B doc
    client.verify_docs_in_changes(url=sg_url, db=sg_db, expected_docs=b_docs, auth=user_b_session, strict=True)

    # Get last_seq for user_b
    user_b_changes = client.get_changes(url=sg_url, db=sg_db, since=0, auth=user_b_session, feed="normal")

    # Grant access to channel "A"
    if grant_type == "CHANNEL-REST":
        log_info("Granting user access to channel A via Admin REST user update")
        # Grant via update to user in Admin API
        client.update_user(url=sg_admin_url, db=sg_db, name=user_b_user_info.name, channels=["A", "B"], auth=auth)

    elif grant_type == "CHANNEL-SYNC":
        log_info("Granting user access to channel A sync function access()")
        # Grant via access() in sync_function, then id 'channel_access' will trigger an access(doc.users, doc.channels)
        access_doc = document.create_doc("channel_access", channels=["A"])
        access_doc["users"] = ["USER_B"]
        client.add_doc(url=sg_url, db=sg_db, doc=access_doc, auth=admin_session)

    elif grant_type == "ROLE-REST":
        log_info("Granting user access to channel A via Admin REST role grant")
        # Create role with channel A
        client.create_role(url=sg_admin_url, db=sg_db, name="channel-A-role", channels=["A"], auth=auth)
        client.update_user(url=sg_admin_url, db=sg_db, name="USER_B", channels=["B"], roles=["channel-A-role"], auth=auth)

    elif grant_type == "ROLE-SYNC":
        log_info("Granting user access to channel A via sync function role() grant")
        # Create role with channel A
        client.create_role(url=sg_admin_url, db=sg_db, name="channel-A-role", channels=["A"], auth=auth)

        # Grant via role() in sync_function, then id 'role_access' will trigger an role(doc.users, doc.roles)
        role_access_doc = document.create_doc("role_access")
        role_access_doc["users"] = ["USER_B"]
        role_access_doc["roles"] = ["role:channel-A-role"]
        client.add_doc(sg_url, db=sg_db, doc=role_access_doc, auth=admin_session)

    elif grant_type == "CHANNEL-TO-ROLE-REST":
        # Update the empty_role to have channel "A"
        client.update_role(url=sg_admin_url, db=sg_db, name="empty_role", channels=["A"], auth=auth)

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
