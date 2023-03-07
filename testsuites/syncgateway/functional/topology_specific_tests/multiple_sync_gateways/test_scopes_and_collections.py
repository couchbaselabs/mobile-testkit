
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
bucket2 = "data-bucket-2"
sg_password = "password"
cb_server = sg_username = channels = client_auth = None
sgs = {}
admin_auth = [RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']]
sg1_url = ""
sg2_url = ""
sync_function = "function(doc){channel(doc.channels);}"


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
        cb_server.create_bucket(cluster_config, bucket2, 100)
        sgs["sg1"] = {"sg_obj": cbs_cluster.sync_gateways[0], "bucket": bucket, "db": "db1" + random_suffix, "user": "sg1_user" + random_suffix}
        sgs["sg2"] = {"sg_obj": cbs_cluster.sync_gateways[1], "bucket": bucket2, "db": "db2" + random_suffix, "user": "sg2_user" + random_suffix}

        for key in sgs:
            server_bucket = sgs[key]["bucket"]
            user = sgs[key]["user"]
            db = sgs[key]["db"]
            data = {"bucket": server_bucket, "scopes": {scope: {"collections": {collection: {"sync": sync_function}}}}, "num_index_replicas": 0}
            # Scope creation on the Couchbase server
            does_scope_exist = cb_server.does_scope_exist(server_bucket, scope)
            if does_scope_exist is False:
                cb_server.create_scope(server_bucket, scope)
            cb_server.create_collection(server_bucket, scope, collection)
            cb_server.create_collection(server_bucket, scope, collection2)
            # SGW database creation
            admin_client = Admin(sgs[key]["sg_obj"])
            pre_test_db_exists = admin_client.does_db_exist(db)
            test_bucket_db = admin_client.get_bucket_db(server_bucket)
            if test_bucket_db is not None:
                admin_client.delete_db(test_bucket_db)
            if pre_test_db_exists is False:
                admin_client.create_db(db, data)
            collection_access = {scope: {collection: {"admin_channels": channels}}}
            # Create a user
            pre_test_user_exists = admin_client.does_user_exist(db, user)
            if pre_test_user_exists is False:
                sg_client.create_user(admin_client.admin_url, db, user, sg_password, channels=channels, auth=admin_auth, collection_access=collection_access)

        yield sg_client, scope, collection, collection2
    except Exception as e:
        raise e
    finally:
        cb_server.delete_scope_if_exists(bucket, scope)
        cb_server.delete_bucket(bucket)
        cb_server.delete_bucket(bucket2)
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
def test_scopes_and_collections_replication(scopes_collections_tests_fixture, params_from_base_test_setup):
    """
        @summary:
        # 1. Create users, user sessions
        # 2. Upload documents to the pushing SGW and make sure that there are no document on the passive SGW
        # 3. Start a pull continous replication sg1 <- sg2
        # 4. Upload new documents to sgw1
        # 5. Add another collection
        # 6. Start a push replication
         # 7. Check that the new documents were replicated to sgw2
    """
    sg1 = sgs["sg1"]
    sg2 = sgs["sg2"]
    admin_client_1 = Admin(sg1["sg_obj"])
    admin_client_2 = Admin(sg2["sg_obj"])
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    num_of_docs = 3

    pull_replication_prefix = "should_be_in_sg2_after_pull"
    push_replication_prefix = "should_be_in_sg2_after_push"
    sg_client, scope, collection, collection2 = scopes_collections_tests_fixture

    if sync_gateway_version < "3.1.0":
        pytest.skip('This test cannot run with Sync Gateway version below 3.1.0')

    sg_client = MobileRestClient()

    # 1. Create users, user sessions
    password = "password"
    user1_auth = sgs["sg1"]["user"], password
    user2_auth = sgs["sg2"]["user"], password

    # 2. Upload documents to the pushing SGW and make sure that there are no document on the passive SGW
    uploaded_for_pull = sg_client.add_docs(url=sg1_url, db=sg1["db"], number=num_of_docs, id_prefix=pull_replication_prefix, channels=["A"], auth=user1_auth, scope=scope, collection=collection)
    with pytest.raises(Exception) as e:
        sg_client.get_doc(sg2_url, sg2["db"], uploaded_for_pull[0]["id"], rev=uploaded_for_pull[0]["rev"], auth=user2_auth, scope=scope, collection=collection)
    e.match("Not Found")

    # 3. start a pull continous replication sg1 <- sg2
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
    admin_client_2.wait_until_sgw_replication_done(sg2["db"], replicator2_id, read_flag=True, max_times=3000)

    # 3. Check that the documents were replicated to sgw2
    for i in range(0, num_of_docs - 1):
        sg_client.get_doc(sg2_url, sg2["db"], uploaded_for_pull[i]["id"], rev=uploaded_for_pull[i]["rev"], auth=user2_auth, scope=scope, collection=collection)

    # 4. Upload new documents to sgw1
    uploaded_for_push = sg_client.add_docs(url=sg1_url, db=sg1["db"], number=num_of_docs, id_prefix=push_replication_prefix, channels=["A"], auth=user1_auth, scope=scope, collection=collection)

    # 5. Add another collection
    data1 = {"bucket": bucket, "scopes": {scope: {"collections": {collection: {"sync": sync_function}, collection2: {"sync": sync_function}}}}, "num_index_replicas": 0, "import_docs": True, "enable_shared_bucket_access": True}
    data2 = {"bucket": bucket2, "scopes": {scope: {"collections": {collection: {"sync": sync_function}, collection2: {"sync": sync_function}}}}, "num_index_replicas": 0, "import_docs": True, "enable_shared_bucket_access": True}
    admin_client_1.post_db_config(sg1["db"], data1)
    admin_client_2.post_db_config(sg2["db"], data2)

    # 6. Start a push replication
    replicator2_id = sg1["sg_obj"].start_replication2(
        local_db=sg1["db"],
        remote_url=sg2["sg_obj"].url,
        remote_db=sg2["db"],
        remote_user=sg2["user"],
        remote_password=password,
        direction="push",
        continuous=False,
        collections_enabled=True
    )

    # 7. Check that the new documents were replicated to sgw2
    for i in range(0, num_of_docs - 1):
        with pytest.raises(Exception) as e:
            sg_client.get_doc(sg2_url, sg2["db"], uploaded_for_push[i]["id"], rev=uploaded_for_push[i]["rev"], auth=user2_auth, scope=scope, collection=collection)
        e.match("Not Found")
