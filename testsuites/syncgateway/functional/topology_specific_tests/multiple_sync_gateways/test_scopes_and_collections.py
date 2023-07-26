from time import sleep
import shutil
import os
import pytest
import uuid
from keywords.MobileRestClient import MobileRestClient
from keywords.constants import RBAC_FULL_ADMIN, SYNC_GATEWAY_CONFIGS_CPC
from requests.auth import HTTPBasicAuth
from keywords.ClusterKeywords import ClusterKeywords
from libraries.testkit.cluster import Cluster
from libraries.testkit.admin import Admin
from keywords import couchbaseserver
from utilities.cluster_config_utils import is_magma_enabled, replace_string_on_sgw_config, copy_sgconf_to_temp
from keywords.SyncGateway import sync_gateway_config_path_for_mode, SyncGateway

# test file shared variables
bucket = "data-bucket-1"
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
rest_to_3sgws_done = False


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
    global rest_to_3sgws_done

    cluster_config = params_from_base_test_setup["cluster_config"]
    if is_magma_enabled(cluster_config):
        pytest.skip("It is not necessary to test ISGR with scopes and collections and MAGMA")
    if params_from_base_test_setup["sync_gateway_version"] < "3.1.0":
        pytest.skip('This test cannot run with Sync Gateway version below 3.1.0')

    if (not rest_to_3sgws_done):
        reset_cluster_configuration(params_from_base_test_setup)
        rest_to_3sgws_done = True

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

        # pre_test_is_bucket_exist = bucket in cb_server.get_bucket_names()
        #  if pre_test_is_bucket_exist:
        #      cb_server.delete_bucket(bucket)

        #  cb_server.create_bucket(cluster_config, bucket, 100)
        #  cb_server.create_bucket(cluster_config, bucket2, 100)
        #  cb_server.create_bucket(cluster_config, bucket3, 100)
        sgs["sg1"] = {"sg_obj": cbs_cluster.sync_gateways[0], "bucket": bucket, "db": "sg_db1" + random_suffix, "user": "sg1_user" + random_suffix}
        sgs["sg2"] = {"sg_obj": cbs_cluster.sync_gateways[1], "bucket": bucket2, "db": "sg_db2" + random_suffix, "user": "sg2_user" + random_suffix}
        sgs["sg3"] = {"sg_obj": cbs_cluster.sync_gateways[2], "bucket": bucket3, "db": "sg_db3" + random_suffix, "user": "sg3_user" + random_suffix}

        for key in sgs:
            server_bucket = sgs[key]["bucket"]
            user = sgs[key]["user"]
            db = sgs[key]["db"]
            # data = {"bucket": server_bucket, "scopes": {scope: {"collections": {collection: {"sync": sync_function}, collection2: {"sync": sync_function}}}}, "num_index_replicas": 0}
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
            # collection_access = {scope: {collection: {"admin_channels": channels}, collection2: {"admin_channels": channels}}}
            collection_access = {scope: {collection: {"admin_channels": channels}}}
            # Create a user
            pre_test_user_exists = admin_client.does_user_exist(db, user)
            if pre_test_user_exists is False:
                sg_client.create_user(admin_client.admin_url, db, user, sg_password, channels=channels, auth=admin_auth, collection_access=collection_access)

        yield sg_client, scope, collection, collection2
    except Exception as e:
        raise e
    finally:
        # potential error here, as we overwrite pre_test variables in the fixture for each db created
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
        cb_server.delete_scope_if_exists(bucket3, scope)
        cb_server.delete_buckets()
        # if pre_test_is_bucket_exist:
        #    cb_server.create_bucket(cluster_config, bucket)


@pytest.mark.syncgateway
@pytest.mark.collections
def test_scopes_and_collections_replication(scopes_collections_tests_fixture, params_from_base_test_setup):
    """
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
    num_of_docs = 3
    pull_replication_prefix = "should_be_in_sg2_after_pull"
    push_replication_prefix = "should_be_in_sg2_after_push"
    sg_client, scope, collection, collection2 = scopes_collections_tests_fixture
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

    # 3. start a pull replication sg2 <- sg1
    replicator1_id = sg2["sg_obj"].start_replication2(
        local_db=sg2["db"],
        remote_url=sg1["sg_obj"].url,
        remote_db=sg1["db"],
        remote_user=sg1["user"],
        remote_password=password,
        direction="pull",
        continuous=False,
        collections_enabled=True
    )
    admin_client_2.replication_status_poll(sg2["db"], replicator1_id, timeout=180)

    # 3. Check that the documents were replicated to sgw2
    sg2_collection_docs_ids = [row["id"] for row in sg_client.get_all_docs(url=sg2_admin_url, db=sg2["db"], auth=user2_auth, scope=scope, collection=collection)["rows"]]
    assert_docs_replicated(uploaded_for_pull, sg2_collection_docs_ids, "sg2", sg2["db"], replicator1_id, "pull")

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

    admin_client_2.replication_status_poll(sg1["db"], replicator2_id, timeout=180)

    # 7. Check that the new documents were replicated to sgw2
    sg2_collection_docs_ids = [row["id"] for row in sg_client.get_all_docs(url=sg2_admin_url, db=sg2["db"], auth=user2_auth, scope=scope, collection=collection)["rows"]]
    sg2_collection_2_docs_ids = [row["id"] for row in sg_client.get_all_docs(url=sg2_admin_url, db=sg2["db"], auth=user2_auth, scope=scope, collection=collection2)["rows"]]
    assert_docs_replicated(uploaded_for_push, sg2_collection_docs_ids, "sg2", sg2["db"], replicator2_id, "push")
    assert_docs_replicated(uploaded_for_push_c2, sg2_collection_2_docs_ids, "sg2", sg2["db"], replicator2_id, "push")

    # 8. Assert that stats are reported correctly on a per replication status
    # WIP - stats are reported on a per replication basis sometimes instantly, but sometimes do not appear for push replication after ~4 mins
    # could be an issue with testkit vms and setup
    # simple exponential backoff doubling wait time between api calls
    timeout = 240
    wait = 0.5
    total = 0
    while total < timeout:
        sleep(wait)
        total += wait
        stats_1 = sg_client.get_expvars(sg1_admin_url, admin_auth)
        stats_2 = sg_client.get_expvars(sg2_admin_url, admin_auth)
        try:
            print(stats_2["syncgateway"]["per_db"][sg2["db"]]["replications"][replicator1_id])
            print(stats_1["syncgateway"]["per_db"][sg1["db"]]["replications"][replicator2_id])
            break
        except KeyError:
            print(f"Did not find replication stats after {total} seconds")
            wait *= 2


@pytest.mark.syncgateway
@pytest.mark.collections
def test_replication_implicit_mapping_filtered_collection(scopes_collections_tests_fixture, params_from_base_test_setup):
    """
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

    sg_client, scope, collection, collection2 = scopes_collections_tests_fixture

    # create users, user sessions
    password = "password"
    user1_auth = sgs["sg1"]["user"], password
    user2_auth = sgs["sg2"]["user"], password

    # 1. Update configs to have identical keyspaces on both SG1 and SG2
    config_1 = {"bucket": bucket, "scopes": {scope: {"collections": {collection: {"sync": sync_function}, collection2: {"sync": sync_function}}}}, "num_index_replicas": 0, "import_docs": True, "enable_shared_bucket_access": True}
    config_2 = {"bucket": bucket2, "scopes": {scope: {"collections": {collection: {"sync": sync_function}, collection2: {"sync": sync_function}}}}, "num_index_replicas": 0, "import_docs": True, "enable_shared_bucket_access": True}
    admin_client_1.post_db_config(sg1["db"], config_1)
    admin_client_2.post_db_config(sg2["db"], config_2)
    # update user configs
    collection_access = {scope: {collection: {"admin_channels": channels}, collection2: {"admin_channels": channels}}}
    sg_client.update_user(sg1_admin_url, sg1["db"], sgs["sg1"]["user"], password=password, channels=channels, auth=admin_auth, collection_access=collection_access)
    sg_client.update_user(sg2_admin_url, sg2["db"], sgs["sg2"]["user"], password=password, channels=channels, auth=admin_auth, collection_access=collection_access)

    # 2. Upload docs to SG1 collections
    sg1_collection_docs = sg_client.add_docs(url=sg1_url, db=sg1["db"], number=3, id_prefix="collection_1_doc", auth=user1_auth, scope=scope, collection=collection, channels=["A"])
    sg_client.add_docs(url=sg1_url, db=sg1["db"], number=3, id_prefix="collection_2_doc", auth=user1_auth, scope=scope, collection=collection2, channels=["A"])

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
        collections_local=[keyspace(scope, collection)]
    )
    admin_client_2.replication_status_poll(sg2["db"], replicator_id, timeout=180)

    # 4.Assert that docs in non-filtered collection are pulled, but filtered is not
    sg2_collection_docs_ids = [row["id"] for row in sg_client.get_all_docs(url=sg2_admin_url, db=sg2["db"], auth=user2_auth, scope=scope, collection=collection)["rows"]]
    sg2_collection_2_docs = sg_client.get_all_docs(url=sg2_admin_url, db=sg2["db"], auth=user2_auth, scope=scope, collection=collection2)
    assert sg2_collection_2_docs["total_rows"] == 0, f"Filtered collection {scope + '.' + collection2} contains {sg2_collection_2_docs['total_rows']} docs when it should contain 0 after replication"
    assert_docs_replicated(sg1_collection_docs, sg2_collection_docs_ids, "sg2", sg2['db'], replicator_id, "pull")


@pytest.mark.syncgateway
@pytest.mark.collections
def test_multiple_replicators_multiple_scopes(scopes_collections_tests_fixture, params_from_base_test_setup):
    """
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

    sg_client, scope, collection, collection2 = scopes_collections_tests_fixture

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
        collections_local=[keyspace(scope, collection2)]
    )

    admin_client_1.replication_status_poll(sg1["db"], replicator_1_id, timeout=180)
    admin_client_3.replication_status_poll(sg3["db"], replicator_2_id, timeout=180)

    # 5. Assert that SG3 contains docs
    sg3_collection_doc_ids = [row["id"] for row in sg_client.get_all_docs(url=sg3_url, db=sg3["db"], auth=user3_auth, scope=scope, collection=collection)["rows"]]
    sg3_collection_2_doc_ids = [row["id"] for row in sg_client.get_all_docs(url=sg3_url, db=sg3["db"], auth=user3_auth, scope=scope, collection=collection2)["rows"]]

    assert_docs_replicated(sg1_collection_docs, sg3_collection_doc_ids, "sg3", sg3['db'], replicator_1_id, "push")
    assert_docs_replicated(sg2_collection_2_docs, sg3_collection_2_doc_ids, "sg3", sg3['db'], replicator_2_id, "pull")


@pytest.mark.syncgateway
@pytest.mark.collections
# skip test currently as testkit setup is causing test to fail due to SG node bootstrap group_ids being the same
@pytest.mark.skip
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

    sg_client, scope, collection, collection2 = scopes_collections_tests_fixture
    scope2 = "scope_2" + random_suffix
    bucket1Collections = [collection, collection2]
    bucket2Collections = []
    bucket3Collections = []

    # create users, user sessions
    password = "password"
    user1_auth = sgs["sg1"]["user"], password
    user2_auth = sgs["sg2"]["user"], password
    user3_auth = sgs["sg3"]["user"], password

    # 1. Create new scopes and collections
    # add one collection to B1, two to B2, four to B3
    for i in range(3, 10):
        newCollection = "collection_" + str(i) + "_" + random_suffix
        if i == 3:
            cb_server.create_collection(bucket, scope, newCollection)
            bucket1Collections.append(newCollection)
        elif i <= 5:
            cb_server.create_collection(bucket2, scope, newCollection)
            bucket2Collections.append(newCollection)
        elif i == 6:
            cb_server.create_scope(bucket3, scope2)
            cb_server.create_collection(bucket3, scope2, newCollection)
            bucket3Collections.append(newCollection)
        else:
            cb_server.create_collection(bucket3, scope2, newCollection)
            bucket3Collections.append(newCollection)

    # 2. Configure SGs
    config_1 = {"bucket": bucket, "scopes": {scope: {"collections": {bucket1Collections[0]: {"sync": sync_function}, bucket1Collections[1]: {"sync": sync_function}, bucket1Collections[2]: {"sync": sync_function}}}}, "num_index_replicas": 0, "import_docs": True, "enable_shared_bucket_access": True}
    config_2 = {"bucket": bucket2, "scopes": {scope: {"collections": {bucket2Collections[0]: {"sync": sync_function}, bucket2Collections[1]: {"sync": sync_function}}}}, "num_index_replicas": 0, "import_docs": True, "enable_shared_bucket_access": True}
    config_3 = {"bucket": bucket3, "scopes": {scope2: {"collections": {bucket3Collections[0]: {"sync": sync_function}, bucket3Collections[1]: {"sync": sync_function}, bucket3Collections[2]: {"sync": sync_function}, bucket3Collections[3]: {"sync": sync_function}}}}, "num_index_replicas": 0, "import_docs": True, "enable_shared_bucket_access": True}
    admin_client_1.post_db_config(sg1["db"], config_1)
    admin_client_2.post_db_config(sg2["db"], config_2)

    # for SG3 delete old db and user and create new db mapped to scope2 as multiple scopes is not yet supported
    db = sgs["sg3"]["db"]
    admin_client_3.delete_user_if_exists(db, sgs["sg3"]["user"])
    admin_client_3.delete_db(db)
    admin_client_3.create_db(db, config_3)
    admin_client_3.wait_for_db_online(db)

    # update user configs for channel access
    user1_collection_access = {scope: {bucket1Collections[0]: {"admin_channels": channels}, bucket1Collections[1]: {"admin_channels": channels}, bucket1Collections[2]: {"admin_channels": channels}}}
    user2_collection_access = {scope: {bucket2Collections[0]: {"admin_channels": channels}, bucket2Collections[1]: {"admin_channels": channels}}}
    user3_collection_access = {scope2: {bucket3Collections[0]: {"admin_channels": channels}, bucket3Collections[1]: {"admin_channels": channels}, bucket3Collections[2]: {"admin_channels": channels}, bucket3Collections[3]: {"admin_channels": channels}}}

    sg_client.update_user(sg1_admin_url, sg1["db"], sgs["sg1"]["user"], password=password, channels=channels, auth=admin_auth, collection_access=user1_collection_access)
    sg_client.update_user(sg2_admin_url, sg2["db"], sgs["sg2"]["user"], password=password, channels=channels, auth=admin_auth, collection_access=user2_collection_access)

    # for SG3 new db create new user
    sg_client.create_user(sg3_admin_url, db, sgs["sg3"]["user"], password, channels=channels, auth=admin_auth, collection_access=user3_collection_access)

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
        collections_local=[keyspace(scope, collection), keyspace(scope, collection2)],
        collections_remote=[keyspace(scope, bucket2Collections[0]), keyspace(scope, bucket2Collections[1])]
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
        collections_local=[keyspace(scope, collection), keyspace(scope, collection2), keyspace(scope, bucket1Collections[2])],
        collections_remote=[keyspace(scope2, bucket3Collections[0]), keyspace(scope2, bucket3Collections[1]), keyspace(scope2, bucket3Collections[2])]
    )

    admin_client_1.replication_status_poll(sg1["db"], replicator_1_id, timeout=180)
    admin_client_3.replication_status_poll(sg3["db"], replicator_2_id, timeout=180)

    # 6. Assert that docs are replicated
    sg2_docs = []
    sg3_docs = []
    for c in bucket2Collections:
        sg2_docs.extend([row["id"] for row in sg_client.get_all_docs(url=sg2_url, db=sg2["db"], auth=user2_auth, scope=scope, collection=c)["rows"]])
    for c in bucket3Collections:
        sg3_docs.extend([row["id"] for row in sg_client.get_all_docs(url=sg3_url, db=sg3["db"], auth=user3_auth, scope=scope2, collection=c)["rows"]])

    should_be_in_sg2 = sg1_collection_docs + sg1_collection2_docs
    should_be_in_sg3 = sg1_collection_docs + sg1_collection2_docs + sg1_collection3_docs

    assert_docs_replicated(should_be_in_sg2, sg2_docs, "sg2", sg2["db"], replicator_1_id, "push")
    assert_docs_replicated(should_be_in_sg3, sg3_docs, "sg3", sg3["db"], replicator_2_id, "pull")


@pytest.mark.syncgateway
@pytest.mark.collections
def test_multiple_dbs_same_bucket(scopes_collections_tests_fixture, params_from_base_test_setup):
    """
    Topology:
        CBServer with 1 bucket, 1 scope, 4 collections
        SG nodes 2, 1 db on each node mapped to the same scope but disjoint set of collections (1,2 on one, 3,4 on other)
    Plan:
        1. Add 2 more collections to bucket1 on CBServer
        2. Update db config on SG1 to include collection 2
        3. Create new db on SG2 mapped to bucket1, scope, with collections 3 and 4
        4. Upload docs to SG1 collections
        5. Initiate replication from SG1->SG2
        6. Assert docs replicated
    """

    sg1 = sgs["sg1"]
    sg2 = sgs["sg2"]
    admin_client_1 = Admin(sg1["sg_obj"])
    admin_client_2 = Admin(sg2["sg_obj"])

    sg_client, scope, collection, collection2 = scopes_collections_tests_fixture

    # create users, user sessions
    password = "password"
    user1_auth = sgs["sg1"]["user"], password
    user2_auth = sgs["sg2"]["user"], password

    collection3 = "collection_3_" + random_suffix
    collection4 = "collection_4_" + random_suffix
    cb_server.create_collection(bucket, scope, collection3)
    cb_server.create_collection(bucket, scope, collection4)

    config_1 = {"bucket": bucket, "scopes": {scope: {"collections": {collection: {"sync": sync_function}, collection2: {"sync": sync_function}}}}, "num_index_replicas": 0, "import_docs": True, "enable_shared_bucket_access": True}
    config_2 = {"bucket": bucket, "scopes": {scope: {"collections": {collection3: {"sync": sync_function}, collection4: {"sync": sync_function}}}}, "num_index_replicas": 0, "import_docs": True, "enable_shared_bucket_access": True}

    collection_access_1 = {scope: {collection: {"admin_channels": channels}, collection2: {"admin_channels": channels}}}
    collection_access_2 = {scope: {collection3: {"admin_channels": channels}, collection4: {"admin_channels": channels}}}

    admin_client_1.post_db_config(sg1["db"], config_1)
    sg_client.update_user(sg1_admin_url, sg1["db"], sgs["sg1"]["user"], password=password, channels=channels, auth=admin_auth, collection_access=collection_access_1)

    # need to delete new db at end of test for teardown
    sgs["sg2"]["bucket"] = bucket
    sgs["sg2"]["db"] = "test_db" + random_suffix
    db2 = sgs["sg2"]["db"]
    admin_client_2.create_db(db2, config_2)
    sg_client.create_user(sg2_admin_url, db2, sgs["sg2"]["user"], sg_password, channels=channels, auth=admin_auth, collection_access=collection_access_2)

    sg1_collection_docs = sg_client.add_docs(url=sg1_url, db=sg1["db"], number=3, id_prefix="collection_1_doc", auth=user1_auth, scope=scope, collection=collection, channels=["A"])
    sg1_collection2_docs = sg_client.add_docs(url=sg1_url, db=sg1["db"], number=4, id_prefix="collection_2_doc", auth=user1_auth, scope=scope, collection=collection2, channels=["A"])

    # 5. Start one-shot pull replication SG1->SG2
    replicator_id = sg2["sg_obj"].start_replication2(
        local_db=sg2["db"],
        remote_url=sg1["sg_obj"].url,
        remote_db=sg1["db"],
        remote_user=sg1["user"],
        remote_password=password,
        direction="pull",
        continuous=False,
        collections_enabled=True,
        collections_local=[keyspace(scope, collection3), keyspace(scope, collection4)],
        collections_remote=[keyspace(scope, collection), keyspace(scope, collection2)]
    )

    admin_client_2.replication_status_poll(sg2["db"], replicator_id, timeout=180)

    should_be_in_sg2 = sg1_collection_docs + sg1_collection2_docs
    sg2_docs = []
    sg2_docs.extend([row["id"] for row in sg_client.get_all_docs(url=sg2_url, db=sg2["db"], auth=user2_auth, scope=scope, collection=collection3)["rows"]])
    sg2_docs.extend([row["id"] for row in sg_client.get_all_docs(url=sg2_url, db=sg2["db"], auth=user2_auth, scope=scope, collection=collection4)["rows"]])
    assert_docs_replicated(should_be_in_sg2, sg2_docs, "sg2", sg2["db"], replicator_id, "pull")


@pytest.mark.syncgateway
@pytest.mark.collections
# skip test currently as testkit setup is causing test to fail due to SG node bootstrap group_ids being the same
@pytest.mark.skip
def test_missing_collection_error(scopes_collections_tests_fixture, params_from_base_test_setup):
    """
    Topology:
        CBServer 2 buckets, 1 scope each, both containing two collections.
        SGs 2, one mapped to each bucket, identical keyspaces for implicit mapping
    Setup:
        1. Update configs so SG1 has both collections, SG2 only has one
        2. Add docs to SG1
        3. Start push replication
        4. Assert that error is encountered because collection is missing
    """

    sg1 = sgs["sg1"]
    sg2 = sgs["sg2"]
    admin_client_1 = Admin(sg1["sg_obj"])
    admin_client_2 = Admin(sg2["sg_obj"])

    sg_client, scope, collection, collection2 = scopes_collections_tests_fixture

    # create users, user sessions
    password = "password"
    user1_auth = sgs["sg1"]["user"], password

    config_1 = {"bucket": bucket, "scopes": {scope: {"collections": {collection: {"sync": sync_function}, collection2: {"sync": sync_function}}}}, "num_index_replicas": 0, "import_docs": True, "enable_shared_bucket_access": True}
    collection_access_1 = {scope: {collection: {"admin_channels": channels}, collection2: {"admin_channels": channels}}}

    admin_client_1.post_db_config(sg1["db"], config_1)
    sg_client.update_user(sg1_admin_url, sg1["db"], sgs["sg1"]["user"], password=password, channels=channels, auth=admin_auth, collection_access=collection_access_1)

    sg_client.add_docs(url=sg1_url, db=sg1["db"], number=3, id_prefix="collection_1_doc", auth=user1_auth, scope=scope, collection=collection, channels=["A"])
    sg_client.add_docs(url=sg1_url, db=sg1["db"], number=4, id_prefix="collection_2_doc", auth=user1_auth, scope=scope, collection=collection2, channels=["A"])

    # 6. Start a push replication
    # this should raise an error for missing collection on passive SG2 but does not currently?
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

    admin_client_2.replication_status_poll(sg1["db"], replicator2_id, timeout=180)


def assert_docs_replicated(docs, sg_docs_ids, sg, db, replicator_id, replicator_type):
    """
    Helper function to check docs are replicated and format error message if not
    """
    for doc in docs:
        assert doc["id"] in sg_docs_ids, f"Doc {doc['id']} not in {sg} database {db} after {replicator_type} replication {replicator_id}"


def keyspace(scope, collection):
    """Construct keyspace for collection mapping"""
    return (scope + '.' + collection)


def reset_cluster_configuration(params_from_base_test_setup):
   # cluster_config = params_from_base_test_setup["cluster_config"]
   # sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
   # sgwgateway = SyncGateway()
   
    for i in range(1, 3):
        sg_config_name = "sync_gateway_cpc_custom_group"
        sg_conf1 = sync_gateway_config_path_for_mode(sg_config_name, "cc", cpc=True)
        #sg_config = sync_gateway_config_path_for_mode(sg_config_name, "cc", cpc=True)
        groupid_str = '"group_id": "group' + str(i) + '"'
        print("££££££££££££££££££££££££££££££££££££££££££££££££" + groupid_str)
        cpc_temp_sg_config = "{}/temp_sg_config_{}".format(SYNC_GATEWAY_CONFIGS_CPC, "cc")
        shutil.copyfile(sg_conf1, cpc_temp_sg_config)
        cpc_temp_sg_config = replace_string_on_sgw_config(cpc_temp_sg_config, '{{ groupid }}', groupid_str)
        with open(cpc_temp_sg_config, 'r') as file:
            filedata = file.read()
            print("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^" + filedata)
        c_cluster = Cluster(config=cpc_temp_sg_config)
        c_cluster.reset(sg_config_path=cpc_temp_sg_config)
        os.remove(cpc_temp_sg_config)

    # sg_config_path = "{}/{}".format(os.getcwd(), sg_config_name)
    #sg1 = c_cluster.sync_gateways[0]
    #sg2 = c_cluster.sync_gateways[1]
    #sg3 = c_cluster.sync_gateways[2]

    #sgwgateway.redeploy_sync_gateway_config(cluster_config=cluster_config, sg_conf=sg_config, url=sg1.ip,
     #                                       sync_gateway_version=sync_gateway_version, enable_import=True)

    #sgwgateway.redeploy_sync_gateway_config(cluster_config=cluster_config, sg_conf=sg_config, url=sg2.ip,
      #                                      sync_gateway_version=sync_gateway_version, enable_import=True)

    #sgwgateway.redeploy_sync_gateway_config(cluster_config=cluster_config, sg_conf=sg_config, url=sg3.ip,
       #                                     sync_gateway_version=sync_gateway_version, enable_import=True)

