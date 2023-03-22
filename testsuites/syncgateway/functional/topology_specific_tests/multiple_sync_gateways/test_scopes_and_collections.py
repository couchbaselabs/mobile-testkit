
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
bucket3 = "data-bucket-3"
sg_password = "password"
cb_server = sg_username = channels = client_auth = None
sgs = {}
admin_auth = [RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']]
admin_auth_tuple = (admin_auth[0], admin_auth[1])
sg1_url = ""
sg2_url = ""
sg3_url = ""
sync_function = "function(doc){channel(doc.channels);}"
sg1_admin_url = ""
sg2_admin_url = ""
sg3_admin_url = ""
random_suffix = ""


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
    global sg3_url
    global sg1_admin_url
    global sg2_admin_url
    global sg3_admin_url
    global random_suffix

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
        sg3_url = topology["sync_gateways"][2]["public"]
        sg1_admin_url = topology["sync_gateways"][0]["admin"]
        sg2_admin_url = topology["sync_gateways"][1]["admin"]
        sg3_admin_url = topology["sync_gateways"][2]["admin"]

        sg_client = MobileRestClient()
        cb_server = couchbaseserver.CouchbaseServer(cbs_url)

        pre_test_is_bucket_exist = bucket in cb_server.get_bucket_names()
        if pre_test_is_bucket_exist:
            cb_server.delete_bucket(bucket)

        cb_server.create_bucket(cluster_config, bucket, 100)
        cb_server.create_bucket(cluster_config, bucket2, 100)
        cb_server.create_bucket(cluster_config, bucket3, 100)
        sgs["sg1"] = {"sg_obj": cbs_cluster.sync_gateways[0], "bucket": bucket, "db": "db1" + random_suffix, "user": "sg1_user" + random_suffix}
        sgs["sg2"] = {"sg_obj": cbs_cluster.sync_gateways[1], "bucket": bucket2, "db": "db2" + random_suffix, "user": "sg2_user" + random_suffix}
        sgs["sg3"] = {"sg_obj": cbs_cluster.sync_gateways[2], "bucket": bucket3, "db": "db3" + random_suffix, "user": "sg3_user" + random_suffix}

        for key in sgs:
            server_bucket = sgs[key]["bucket"]
            user = sgs[key]["user"]
            db = sgs[key]["db"]
            #data = {"bucket": server_bucket, "scopes": {scope: {"collections": {collection: {"sync": sync_function}, collection2: {"sync": sync_function}}}}, "num_index_replicas": 0}
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
            #collection_access = {scope: {collection: {"admin_channels": channels}, collection2: {"admin_channels": channels}}}
            collection_access = {scope: {collection: {"admin_channels": channels}}}
            # Create a user
            pre_test_user_exists = admin_client.does_user_exist(db, user)
            if pre_test_user_exists is False:
                sg_client.create_user(admin_client.admin_url, db, user, sg_password, channels=channels, auth=admin_auth, collection_access=collection_access)

        yield sg_client, scope, collection, collection2
    except Exception as e:
        raise e
    finally:
        for key in sgs:
            admin_client = Admin(sgs[key]["sg_obj"])
            # Cleanup everything that was created
            if (pre_test_user_exists is not None) and (pre_test_user_exists is False):
                admin_client.delete_user_if_exists(sgs[key]["db"], sgs[key]["user"])
            if (pre_test_db_exists is not None) and (pre_test_db_exists is False):
                if admin_client.does_db_exist(sgs[key]["db"]) is True:
                    admin_client.delete_db(sgs[key]["db"])

        cb_server.delete_scope_if_exists(bucket, scope)
        cb_server.delete_scope_if_exists(bucket2, scope)
        cb_server.delete_buckets()
        if pre_test_is_bucket_exist:
            cb_server.create_bucket(cluster_config, bucket)


@pytest.mark.syncgateway
@pytest.mark.collections
def test_scopes_and_collections_replication(scopes_collections_tests_fixture, params_from_base_test_setup):
    """
    TODO: If the fixture setup includes two collections on SG1 and SG2 and corresponding collections_access for users
          then the check after the pull replication in step 3 fails
          Currently adjust other tests to initialise multi-collection outside of fixture setup, but may potentially
          be able to revert if this is a SGW issue that is fixed in future
        @summary:
        # 1. Create users, user sessions
        # 2. Upload documents to the pushing SGW and make sure that there are no document on the passive SGW
        # 3. Start a pull continous replication sg1 <- sg2
        # 4. Add another collection
        # 5. Upload new documents to sgw1, both collections
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

    # 3. start a pull continous replication sg2 <- sg1
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
        sg_client.get_doc(sg2_url, sg2["db"], uploaded_for_pull[i]["id"], auth=user2_auth, scope=scope, collection=collection)

    # 4. Add another collection
    data1 = {"bucket": bucket, "scopes": {scope: {"collections": {collection: {"sync": sync_function}, collection2: {"sync": sync_function}}}}, "num_index_replicas": 0, "import_docs": True, "enable_shared_bucket_access": True}
    data2 = {"bucket": bucket2, "scopes": {scope: {"collections": {collection: {"sync": sync_function}, collection2: {"sync": sync_function}}}}, "num_index_replicas": 0, "import_docs": True, "enable_shared_bucket_access": True}
    admin_client_1.post_db_config(sg1["db"], data1)
    admin_client_2.post_db_config(sg2["db"], data2)

    # 5. Upload new documents to sgw1, both collections
    uploaded_for_push = sg_client.add_docs(url=sg1_url, db=sg1["db"], number=num_of_docs, id_prefix=push_replication_prefix, channels=["A"], auth=user1_auth, scope=scope, collection=collection)
    uploaded_for_push_c2 = sg_client.add_docs(url=sg1_url, db=sg1["db"], number=num_of_docs, id_prefix=push_replication_prefix + "c2", channels=["A"], auth=user1_auth, scope=scope, collection=collection2)

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

    admin_client_2.wait_until_sgw_replication_done(sg1["db"], replicator2_id, read_flag=True, max_times=3000)

    # 7. Check that the new documents were replicated to sgw2
    for i in range(0, num_of_docs - 1):
        sg_client.get_doc(sg2_url, sg2["db"], uploaded_for_push[i]["id"], rev=uploaded_for_push[i]["rev"], auth=user2_auth, scope=scope, collection=collection)
        sg_client.get_doc(sg2_url, sg2["db"], uploaded_for_push_c2[i]["id"], rev=uploaded_for_push_c2[i]["rev"], auth=user2_auth, scope=scope, collection=collection2)


@pytest.mark.syncgateway
@pytest.mark.collections
def test_replication_implicit_mapping_filtered_collection(scopes_collections_tests_fixture, params_from_base_test_setup):
    """
    TODO check all_docs endpoint is working correctly at end of test and add assertions rather than prints
        can be fixed via channel access grants and doc routing
    Test that ISGR implicit mapping works with a subset of collections on the active sync gateway
    1. Update configs to have identical keyspaces on both SG1 and SG2
    2. Upload docs to SG1 collections
    3. Start one-shot pull replication SG1->SG2, filtering one collection
    4. Assert that docs in non-filtered collection are pulled, but filtered is not
    """
    sg1 = sgs["sg1"]
    sg2 = sgs["sg2"]
    admin_client_1 = Admin(sg1["sg_obj"])
    admin_client_2 = Admin(sg2["sg_obj"])
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    sg_client, scope, collection, collection2 = scopes_collections_tests_fixture

    # check sync gateway version
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with Sync Gateway version below 3.0')

    # create users, user sessions
    password = "password"
    user1_auth = sgs["sg1"]["user"], password
    user2_auth = sgs["sg2"]["user"], password

    # 1. Update configs to have identical keyspaces on both SG1 and SG2
    config_1 = {"bucket": bucket, "scopes": {scope: {"collections": {collection: {"sync": sync_function}, collection2: {"sync": sync_function}}}}, "num_index_replicas": 0, "import_docs": True, "enable_shared_bucket_access": True}
    config_2 = {"bucket": bucket2, "scopes": {scope: {"collections": {collection: {"sync": sync_function}, collection2: {"sync": sync_function}}}}, "num_index_replicas": 0, "import_docs": True, "enable_shared_bucket_access": True}
    admin_client_1.post_db_config(sg1["db"], config_1)
    admin_client_2.post_db_config(sg2["db"], config_2)

    # 2. Upload docs to SG1 collections
    sg1_collection_docs = sg_client.add_docs(url=sg1_url, db=sg1["db"], number=3, id_prefix="collection_1_doc", auth=user1_auth, scope=scope, collection=collection, channels=["A"])
    sg1_collection_2_docs = sg_client.add_docs(url=sg1_url, db=sg1["db"], number=3, id_prefix="collection_2_doc", auth=user1_auth, scope=scope, collection=collection2, channels=["A"])
    """
    # 3. Start one-shot pull replication SG1->SG2, filtering one collection
    replicator_id = sg2["sg_obj"].start_replication2(
        local_db=sg2["db"],
        remote_url=sg1["sg_obj"].url,
        remote_db=sg1["db"],
        remote_user=sg1["user"],
        remote_password=password,
        direction="pull",
        continuous=False,
        collections_enabled=True,
        collections_local=[collection]
    )
    admin_client_2.wait_until_sgw_replication_done(sg2["db"], replicator_id, read_flag=True, max_times=3000)
   """
    # 3. Start one-shot push replication SG1->SG2, filtering one collection
    replicator_id = sg1["sg_obj"].start_replication2(
        local_db=sg1["db"],
        remote_url=sg2["sg_obj"].url,
        remote_db=sg2["db"],
        remote_user=sg2["user"],
        remote_password=password,
        direction="push",
        continuous=False,
        collections_enabled=True,
        collections_local=[collection]
    )
    admin_client_1.wait_until_sgw_replication_done(sg1["db"], replicator_id, read_flag=True, max_times=3000)

    # 4.Assert that docs in non-filtered collection are pulled, but filtered is not
    sg2_collection_docs = sg_client.get_all_docs(url=sg2_admin_url, db=sg2["db"], auth=user2_auth, scope=scope, collection=collection)
    sg2_collection_2_docs = sg_client.get_all_docs(url=sg2_admin_url, db=sg2["db"], auth=user2_auth, scope=scope, collection=collection2)
    print(sg1_collection_docs)
    print(sg1_collection_2_docs)
    print(sg2_collection_docs)
    print(sg2_collection_2_docs)

    for doc_id in [doc["id"] for doc in sg1_collection_docs]:
        try:
            sg_client.get_doc(sg2_url, sg2["db"], doc_id, auth=user2_auth, scope=scope, collection=collection)
        except:
            print(f"could not get doc {doc_id} in collection")
    for doc_id in [doc["id"] for doc in sg1_collection_2_docs]:
        try:
            sg_client.get_doc(sg2_url, sg2["db"], doc_id, auth=user2_auth, scope=scope, collection=collection2)
        except:
            print(f"could not get doc {doc_id} in collection2")


@pytest.mark.syncgateway
@pytest.mark.collections
def test_multiple_replicators_multiple_scopes(scopes_collections_tests_fixture, params_from_base_test_setup):
    """
    TODO Finish test case by adding assertions where prints are
    Test that ISGR for multiple scopes(dbs) works using multiple replicators for each scope
    Topology:
        CBServer 3 buckets - B1,B2 with 1 scope and 1 collection; B3 1 scope with 2 collections
        SGs 3 - SG1 on B1, SG2 on B2, SG3 on B3
    ISGR from SG1 and SG2 to collections on SG3
    1. Configure SGs according to above topology
    2. Upload docs to SG1 and SG2
    3. Start one-shot push replication SG1->SG3
    4. Start one-shot pull replication SG2->SG3
    5. Assert that SG3 contains docs
    """
    sg1 = sgs["sg1"]
    sg2 = sgs["sg2"]
    sg3 = sgs["sg3"]
    admin_client_1 = Admin(sg1["sg_obj"])
    admin_client_2 = Admin(sg2["sg_obj"])
    admin_client_3 = Admin(sg3["sg_obj"])
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    sg_client, scope, collection, collection2 = scopes_collections_tests_fixture

    # check sync gateway version
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with Sync Gateway version below 3.0')

    # create users, user sessions
    password = "password"
    user1_auth = sgs["sg1"]["user"], password
    user2_auth = sgs["sg2"]["user"], password
    user3_auth = sgs["sg3"]["user"], password

    # 1. Configure SGs according to above topology
    config_1 = {"bucket": bucket, "scopes": {scope: {"collections": {collection: {"sync": sync_function}}}}, "num_index_replicas": 0, "import_docs": True, "enable_shared_bucket_access": True}
    config_2 = {"bucket": bucket2, "scopes": {scope: {"collections": {collection2: {"sync": sync_function}}}}, "num_index_replicas": 0, "import_docs": True, "enable_shared_bucket_access": True}
    config_3 = {"bucket": bucket3, "scopes": {scope: {"collections": {collection: {"sync": sync_function}, collection2: {"sync": sync_function}}}}, "num_index_replicas": 0, "import_docs": True, "enable_shared_bucket_access": True}
    admin_client_1.post_db_config(sg1["db"], config_1)
    admin_client_2.post_db_config(sg2["db"], config_2)
    admin_client_3.post_db_config(sg3["db"], config_3)

    # update user configs for channel access
    user1_collection_access = {scope: {collection: {"admin_channels": channels}}}
    user2_collection_access = {scope: {collection2: {"admin_channels": channels}}}
    user3_collection_access = {scope: {collection: {"admin_channels": channels}, collection2: {"admin_channels": channels}}}

    sg_client.update_user(sg1_admin_url, sg1["db"], sgs["sg1"]["user"], password=password, channels=channels, auth=admin_auth, collection_access=user1_collection_access)
    sg_client.update_user(sg2_admin_url, sg2["db"], sgs["sg2"]["user"], password=password, channels=channels, auth=admin_auth, collection_access=user2_collection_access)
    sg_client.update_user(sg3_admin_url, sg3["db"], sgs["sg3"]["user"], password=password, channels=channels, auth=admin_auth, collection_access=user3_collection_access)

    # maybe add code to delete collections from bucket1 and bucket2 that are not relevant

    # 2. Upload docs to SG1 and SG2
    sg1_collection_docs = sg_client.add_docs(url=sg1_url, db=sg1["db"], number=3, id_prefix="collection_1_doc", auth=user1_auth, scope=scope, collection=collection, channels=["A"])
    sg2_collection_2_docs = sg_client.add_docs(url=sg2_url, db=sg2["db"], number=3, id_prefix="collection_2_doc", auth=user2_auth, scope=scope, collection=collection2, channels=["A"])

    # 3. Start one-shot push replication SG1->SG3
    replicator_1_id = sg1["sg_obj"].start_replication2(
        local_db=sg1["db"],
        remote_url=sg3["sg_obj"].url,
        remote_db=sg3["db"],
        remote_user=sg3["user"],
        remote_password=password,
        direction="push",
        continuous=False,
        collections_enabled=True
    )

    # 4. Start one-shot pull replication SG2->SG3, with filter for implicit mapping
    replicator_2_id = sg3["sg_obj"].start_replication2(
        local_db=sg3["db"],
        remote_url=sg2["sg_obj"].url,
        remote_db=sg2["db"],
        remote_user=sg2["user"],
        remote_password=password,
        direction="pull",
        continuous=False,
        collections_enabled=True,
        collections_local=[collection2]
    )

    admin_client_1.wait_until_sgw_replication_done(sg1["db"], replicator_1_id, read_flag=True, max_times=3000)
    admin_client_3.wait_until_sgw_replication_done(sg3["db"], replicator_2_id, read_flag=True, max_times=3000)
    
    # 5. Assert that SG3 contains docs
    sg3_collection_docs = sg_client.get_all_docs(url=sg3_url, db=sg3["db"], auth=user3_auth, scope=scope, collection=collection)
    sg3_collection_2_docs = sg_client.get_all_docs(url=sg3_url, db=sg3["db"], auth=user3_auth, scope=scope, collection=collection2)
    collection_2_ids = [doc["id"] for doc in sg2_collection_2_docs]

    print(sg3_collection_docs)
    print(sg3_collection_2_docs)
    
    #this gives 404 error, doc not found, so pull replication is not working?
    for id in collection_2_ids:
        print(sg_client.get_doc(sg3_url, sg3["db"], id, auth=user3_auth, scope=scope, collection=collection2))


@pytest.mark.syncgateway
@pytest.mark.collections
def test_replication_explicit_mapping(scopes_collections_tests_fixture, params_from_base_test_setup):
    """
    Test that users can remap collections when performing ISGR
    Topology:
        CBServer 3 buckets - B1 with scope1 collections 1,2,3; B2 with scope1 collections 4,5; B3 with scope2 collections 6,7,8,9
        SGs 3 - SG(1,2,3) to B(1,2,3) respectively
    1. Create new scopes and collections to adhere to above topology
    2. Configure SGs to topology
    3. Upload docs to SG1
    4. Start one-shot push replication from SG1 to SG2, with remapping:
        scope1.collection1:scope1.collection4
        scope1.collection2:scope1.collection5
    5. Start one-shot pull replication from SG1 to SG3, with remapping:
        scope1.collection1:scope2.collection6
        scope1.collection2:scope2.collection7
        scope1.collection3:scope2.collection8
    6. Assertions that docs are replicated

    Does there need to be test that starting a new replication that remaps an already remapped collection cause an error? 
    i.e. new replicator with scope1.collection3:scope2.collection9 should error if created after above replicators?
    """
    sg1 = sgs["sg1"]
    sg2 = sgs["sg2"]
    sg3 = sgs["sg3"]
    admin_client_1 = Admin(sg1["sg_obj"])
    admin_client_2 = Admin(sg2["sg_obj"])
    admin_client_3 = Admin(sg3["sg_obj"])
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    sg_client, scope, collection, collection2 = scopes_collections_tests_fixture
    scope2 = "scope_2" + random_suffix
    bucket1Collections = [collection, collection2]
    bucket2Collections = []
    bucket3Collections = []

    # check sync gateway version
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with Sync Gateway version below 3.0')

    # create users, user sessions
    password = "password"
    user1_auth = sgs["sg1"]["user"], password
    user2_auth = sgs["sg2"]["user"], password
    user3_auth = sgs["sg3"]["user"], password

    # 1. Create new scopes and collections
    # add one collection to B1, two to B2, four to B3
    for i in range(3,10):
        newCollection = "collection_" + str(i) + "_" + random_suffix
        if i == 3:
            serverBucket = bucket
            bucket1Collections.append(newCollection)
        elif i <= 5:
            serverBucket = bucket2
            bucket2Collections.append(newCollection)
        else:
            newScope = scope2
            serverBucket = bucket3
            bucket3Collections.append(newCollection)
        
        if i == 6:
            # first time a collection is created for B3, add the new scope first
            cb_server.create_scope(serverBucket, newScope)
        
        if i >= 6:
            # adding collections to newScope under B3
            cb_server.create_collection(serverBucket, newScope, newCollection)
        else:
            cb_server.create_collection(serverBucket, scope, newCollection)
    
    # 2. Configure SGs
    config_1 = {"bucket": bucket, "scopes": {scope: {"collections": {bucket1Collections[0]: {"sync": sync_function}, bucket1Collections[1]: {"sync": sync_function}, bucket1Collections[2]: {"sync": sync_function}}}}, "num_index_replicas": 0, "import_docs": True, "enable_shared_bucket_access": True}
    config_2 = {"bucket": bucket2, "scopes": {scope: {"collections": {bucket2Collections[0]: {"sync": sync_function}, bucket2Collections[1]: {"sync": sync_function}}}}, "num_index_replicas": 0, "import_docs": True, "enable_shared_bucket_access": True}
    config_3 = {"bucket": bucket3, "scopes": {scope2: {"collections": {bucket3Collections[0]: {"sync": sync_function}, bucket3Collections[1]: {"sync": sync_function}, bucket3Collections[2]: {"sync": sync_function}, bucket3Collections[3]: {"sync": sync_function}}}}, "num_index_replicas": 0, "import_docs": True, "enable_shared_bucket_access": True}
    admin_client_1.post_db_config(sg1["db"], config_1)
    admin_client_2.post_db_config(sg2["db"], config_2)

    # for SG3 delete old db and user and create new db mapped to scope2 as multiple scopes is not yet supported
    db = sgs["sg3"]["db"]
    admin_client_3.delete_user_if_exists(db, sgs["sg3"]["user"])
    admin_client_3.delete_db(sg3["db"])
    admin_client_3.create_db(db, config_3)
    admin_client_3.wait_for_db_online(db)

    # update user configs for channel access
    user1_collection_access = {scope: {bucket1Collections[0]: {"admin_channels": channels}, bucket1Collections[1]: {"admin_channels": channels}, bucket1Collections[2]: {"admin_channels": channels}}}
    user2_collection_access = {scope: {bucket2Collections[0]: {"admin_channels": channels}, bucket2Collections[1]: {"admin_channels": channels}}}
    user3_collection_access = {scope: {bucket3Collections[0]: {"admin_channels": channels}, bucket3Collections[1]: {"admin_channels": channels}, bucket3Collections[2]: {"admin_channels": channels}, bucket3Collections[3]: {"admin_channels": channels}}}

    sg_client.update_user(sg1_admin_url, sg1["db"], sgs["sg1"]["user"], password=password, channels=channels, auth=admin_auth, collection_access=user1_collection_access)
    sg_client.update_user(sg2_admin_url, sg2["db"], sgs["sg2"]["user"], password=password, channels=channels, auth=admin_auth, collection_access=user2_collection_access)
    #sg_client.update_user(sg3_admin_url, sg3["db"], sgs["sg3"]["user"], password=password, channels=channels, auth=admin_auth, collection_access=user3_collection_access)

    # for SG3 new db create new user
    sg_client.create_user(sg3_admin_url, db, sgs["sg3"]["user"], password, channels=channels, auth=admin_auth, collection_access=user3_collection_access)
    #user3_auth = "test_user", password

    # 3. Upload docs to SG1
    sg1_collection_docs = sg_client.add_docs(url=sg1_url, db=sg1["db"], number=3, id_prefix="collection_1_doc", auth=user1_auth, scope=scope, collection=bucket1Collections[0], channels=["A"])
    sg1_collection2_docs = sg_client.add_docs(url=sg1_url, db=sg1["db"], number=3, id_prefix="collection_2_doc", auth=user1_auth, scope=scope, collection=bucket1Collections[1], channels=["A"])
    sg1_collection3_docs = sg_client.add_docs(url=sg1_url, db=sg1["db"], number=3, id_prefix="collection_3_doc", auth=user1_auth, scope=scope, collection=bucket1Collections[2], channels=["A"])

    # 4. Start one-shot push replication SG1->SG2
    replicator_1_id = sg1["sg_obj"].start_replication2(
        local_db=sg1["db"],
        remote_url=sg2["sg_obj"].url,
        remote_db=sg2["db"],
        remote_user=sg2["user"],
        remote_password=password,
        direction="push",
        continuous=False,
        collections_enabled=True,
        collections_local=[collection, collection2],
        collections_remote=[bucket2Collections[0], bucket2Collections[1]]
    )

    # 5. Start one-shot pull replication SG1->SG3
    replicator_2_id = sg3["sg_obj"].start_replication2(
        local_db=sg3["db"],
        remote_url=sg1["sg_obj"].url,
        remote_db=sg1["db"],
        remote_user=sg1["user"],
        remote_password=password,
        direction="pull",
        continuous=False,
        collections_enabled=True,
        collections_local=[collection, collection2, bucket1Collections[2]],
        collections_remote=[bucket3Collections[0], bucket3Collections[1], bucket3Collections[2]]
    )

    admin_client_1.wait_until_sgw_replication_done(sg1["db"], replicator_1_id, read_flag=True, max_times=3000)
    admin_client_3.wait_until_sgw_replication_done(sg3["db"], replicator_2_id, read_flag=True, max_times=3000)

    # 6. Assert that docs are replicated
    sg2_docs = []
    sg3_docs = []
    for c in bucket2Collections:
        collection_docs = sg_client.get_all_docs(url=sg2_url, db=sg2["db"], auth=user2_auth, scope=scope, collection=c)
        sg2_docs.extend([row for row in collection_docs["rows"]])
    for c in bucket3Collections:
        collection_docs = sg_client.get_all_docs(url=sg3_url, db=sg3["db"], auth=user3_auth, scope=scope2, collection=c)
        sg3_docs.extend([row for row in collection_docs["rows"]])

    print(sg2_docs)
    print(sg3_docs)

