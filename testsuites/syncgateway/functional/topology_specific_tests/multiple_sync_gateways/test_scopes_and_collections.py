
import pytest
import uuid
from keywords.MobileRestClient import MobileRestClient
from keywords.constants import RBAC_FULL_ADMIN
from requests.auth import HTTPBasicAuth
from keywords.ClusterKeywords import ClusterKeywords
from libraries.testkit.cluster import Cluster
from libraries.testkit.admin import Admin
from keywords import couchbaseserver

# test file shared variables
bucket = "data-bucket"
bucket_2 = "data-bucket-2"
sg_password = "password"
cb_server = sg_username = channels = client_auth = None
sgs = {}
admin_auth = [RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']]
sg1_url = ""
sg2_url = ""


@pytest.fixture
def scopes_collections_tests_fixture(params_from_base_test_setup):
    # get/set the parameters
    global sgs
    global cb_server
    global sg_username
    global channels
    global client_auth
    global sg1_url
    global sg2_url

    try:  # To be able to teardon in case of a setup error
        random_suffix = str(uuid.uuid4())[:8]
        scope_prefix = "scope_"
        collection_prefix = "collection_"
        scope = scope_prefix + random_suffix
        collection = collection_prefix + random_suffix
        collection2 = collection_prefix + "2_" + random_suffix
        cluster_config = params_from_base_test_setup["cluster_config"]
        cbs_cluster = Cluster(config=cluster_config)
        client_auth = HTTPBasicAuth(sg_username, sg_password)
        channels = ["A"]

        pre_test_db_exists = pre_test_user_exists = sg_client = None
        cluster_config = params_from_base_test_setup["cluster_config"]
        cluster_helper = ClusterKeywords(cluster_config)
        topology = cluster_helper.get_cluster_topology(cluster_config)
        cbs_url = topology["couchbase_servers"][0]
        sg1_url = topology["sync_gateways"][0]["public"]
        sg2_url = topology["sync_gateways"][1]["public"]

        sg_client = MobileRestClient()
        cb_server = couchbaseserver.CouchbaseServer(cbs_url)

        pre_test_is_bucket_exist = bucket in cb_server.get_bucket_names()
        if pre_test_is_bucket_exist:
            cb_server.delete_bucket(bucket)

        cb_server.create_bucket(cluster_config, bucket, 100)
        cb_server.create_bucket(cluster_config, bucket_2, 100)
        sgs["sg1"] = {"sg_obj": cbs_cluster.sync_gateways[0], "bucket": bucket, "db": "db" + random_suffix, "user": "sg1_user" + random_suffix}
        sgs["sg2"] = {"sg_obj": cbs_cluster.sync_gateways[1], "bucket": bucket_2, "db": "db1" + random_suffix, "user": "sg2_user" + random_suffix}
        import_function = "function filter(doc) { return doc._id == \"should_be_in_sg2_0\" }"

        for key in sgs:
            server_bucket = sgs[key]["bucket"]
            user = sgs[key]["user"]
            db = sgs[key]["db"]
            #data = {"bucket": server_bucket, "scopes": {scope: {"collections": {collection: {"import_filter": import_function}}}}, "num_index_replicas": 0}
            # data = {"bucket": server_bucket, "scopes": {scope: {"collections": {collection: {"import_filter": "function filter(doc) { return doc.key.includes(\"should_be_in_sg2\") }"}}}}, "num_index_replicas": 0}
            data = {"bucket": server_bucket, "scopes": {scope: {"collections": {collection: {}}}}, "num_index_replicas": 0}
            # Scope creation on the Couchbase server
            does_scope_exist = cb_server.does_scope_exist(server_bucket, scope)
            if does_scope_exist is False:
                cb_server.create_scope(server_bucket, scope)
            cb_server.create_collection(server_bucket, scope, collection)
            # SGW database creation
            admin_client = Admin(sgs[key]["sg_obj"])
            pre_test_db_exists = admin_client.does_db_exist(db)
            test_bucket_db = admin_client.get_bucket_db(server_bucket)
            if test_bucket_db is not None:
                admin_client.delete_db(test_bucket_db)
            if pre_test_db_exists is False:
                admin_client.create_db(db, data)

            # Create a user
            pre_test_user_exists = admin_client.does_user_exist(db, user)
            if pre_test_user_exists is False:
                sg_client.create_user(admin_client.admin_url, db, user, sg_password, channels=channels, auth=admin_auth)

        yield sg_client, scope, collection
    except Exception as e:
        raise e
    finally:
        cb_server.delete_scope_if_exists(bucket, scope)
        cb_server.delete_bucket(bucket)
        cb_server.delete_bucket(bucket_2)
        if pre_test_is_bucket_exist:
            cb_server.create_bucket(cluster_config, bucket)

        for key in sgs:
            admin_client = Admin(sgs[key]["sg_obj"])
            # Cleanup everything that was created
            if (pre_test_user_exists is not None) and (pre_test_user_exists is False):
                admin_client.delete_user_if_exists(sgs[key]["db"], sgs[key]["user"])
            if (pre_test_db_exists is not None) and (pre_test_db_exists is False):
                if admin_client.does_db_exist(sgs[key]["db"]) is True:
                    admin_client.delete_db(sgs[key]["db"])


@pytest.mark.syncgateway
@pytest.mark.collections
def test_scopes_and_collections_import_filters(scopes_collections_tests_fixture, params_from_base_test_setup):
    """
        @summary:
        Channel Access Revocation Test Plan (ISGR) #1
        1. on passive SGW, create docs:
                doc_A belongs to channel A only,
                doc_AnB belongs to channel A and channel B
        2. start a pull continous replication on active SGW with auto_purge_setting parameter
        3. verify active SGW have pulled the doc_A and doc_AnB
        4. revoke the user access to channel A
        5. verify expected doc auto purge result on active SGW
    """
    sg1 = sgs["sg1"]
    sg2 = sgs["sg2"]
    admin_client_1 = Admin(sgs["sg1"]["sg_obj"])
    admin_client_2 = Admin(sgs["sg2"]["sg_obj"])
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]

    sg_client, scope, collection = scopes_collections_tests_fixture

    # check sync gateway version
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with Sync Gateway version below 3.0')

    sg_client = MobileRestClient()

    # create users, user sessions
    password = "password"
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$" + str(sgs["sg1"]["user"]))
    user1_auth = sgs["sg1"]["user"], "password"
    user2_auth = sgs["sg2"]["user"], "password"
    # 1. Update the db config's import filter.
    #import_function = "function filter(doc) { return doc.id == \"should_be_in_sg2_0\"}"
    #data = {"bucket": bucket, "scopes": {scope: {"collections": {collection: {"import_filter": import_function}}}}, "num_index_replicas": 0, "import_docs": True, "enable_shared_bucket_access": True}
    #admin_client_1.post_db_config(sg1["db"], data)
    #admin_client_2.post_db_config(sg2["db"], data)
   # sg_client.create_user(admin_client_1.admin_url, sg1["db"], "sg1_user", "password", collection_access=collection, auth=admin_auth)
    #sg_client.create_user(admin_client_2.admin_url, sg2["db"], "sg2_user", "password", collection_access=collection, auth=admin_auth)

    # 1. on passive SGW, create docs: doc_A belongs to channel A only, doc_AnB belongs to channel A and channel B
    sg_client.add_docs(url=sg1_url, db=sg1["db"], number=3, id_prefix="should_be_in_sg2", channels=["A"], auth=user1_auth, scope=scope, collection=collection)
    sg_client.add_docs(url=sg1_url, db=sg1["db"], number=3, id_prefix="should_not_be_in_sg2", channels=["A", "B"], auth=user1_auth, scope=scope, collection=collection)

    # sg2_docs = sg_client.get_all_docs(url=sg2.url, db=db2, auth=auth_session2, include_docs=True)
    # sg2_doc_ids = [doc["id"] for doc in sg2_docs["rows"]]
    user_2_docs = sg_client.get_all_docs(url=sg1_url, db=sg1["db"], scope=scope, collection=collection, auth=user1_auth, include_docs=True)
    print("=================================================================" + str(user_2_docs))
    sdkjlsdkjflksdjflk
    # 2. start a pull continous replication sg1 <- sg2 with auto_purge_setting parameter
    replicator2_id = sg2["sg_obj"].start_replication2(
        local_db=sg2["db"],
        remote_url=sg1["sg_obj"].url,
        remote_db=sg1["db"],
        remote_user=sg1["user"],
        remote_password=password,
        direction="pull",
        continuous=False,
        collections_enabled=True
    )
    #if auth:
     #   sg1.admin.auth = HTTPBasicAuth(auth[0], auth[1])
    admin_client_2.wait_until_sgw_replication_done(sg2["db"], replicator2_id, read_flag=True, max_times=3000)

    user_2_docs = sg_client.get_all_docs(url=admin_client_2.admin_url, db=sg2["db"], scope=scope, collection=collection, auth=auth, include_docs=True)
    print("=================================================================" + str(user_2_docs))

