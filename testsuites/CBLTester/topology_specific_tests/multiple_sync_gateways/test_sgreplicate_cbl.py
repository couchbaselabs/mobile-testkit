import pytest
import time
import random
import json

from keywords.MobileRestClient import MobileRestClient
from CBLClient.Database import Database
from CBLClient.Replication import Replication
from CBLClient.Authenticator import Authenticator
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from libraries.testkit.syncgateway import wait_until_active_tasks_empty
from libraries.testkit import cluster
from libraries.testkit.admin import Admin
from keywords.constants import CLUSTER_CONFIGS_DIR
from requests import HTTPError
from keywords.utils import log_info, random_string
from keywords import attachment, document
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ProcessPoolExecutor
from CBLClient.Dictionary import Dictionary
from CBLClient.Blob import Blob
from utilities.cluster_config_utils import copy_sgconf_to_temp, load_cluster_config_json, replace_string_on_sgw_config


# def setup_syncGateways_with_cbl(cluster_config, base_url, sync_gateway_version, sg_ssl, sg_mode):
def setup_syncGateways_with_cbl(params_from_base_test_setup, cbl_replication_type, cbl_continuous, cbl_db1, sg_conf_name='listener_tests/four_sync_gateways', num_of_docs=10, channels1=None):

    cluster_config = params_from_base_test_setup["cluster_config"]
    base_url = params_from_base_test_setup["base_url"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    sg_ssl = params_from_base_test_setup["sg_ssl"]
    sg_mode = params_from_base_test_setup["mode"]
    sg_db1 = "sg_db1"
    sg_db2 = "sg_db2"
    protocol = "ws"
    
    print("entering into setup insdie test file ")
    channels2 = ["Replication2"]
    name1 = "autotest1"
    name2 = "autotest2"
    password = "password"
    if channels1 is None:
        channels1 = ["Replication1"]

    sg_client = MobileRestClient()
    if sync_gateway_version < "2.8.0":
        pytest.skip('It does not work with sg < 2.8.0 and cannot work with self signed, so skipping the test')

    print("cluster config dir - ", cluster_config)
    # cluster_config = "{}/{}".format(CLUSTER_CONFIGS_DIR, cluster_config)
    c_cluster = cluster.Cluster(config=cluster_config)
    
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)
    
    c_cluster.reset(sg_config_path=sg_config)
    db = Database(base_url)

    sg1 = c_cluster.sync_gateways[0]
    sg2 = c_cluster.sync_gateways[1]

    admin = Admin(sg1)
    admin.admin_url = sg1.url

    sg1_ip = sg1.ip
    sg2_ip = sg2.ip
    sg1_admin_url = sg1.admin.admin_url
    sg2_admin_url = sg2.admin.admin_url
    if sg_ssl:
        protocol = "wss"
    sg1_blip_url = "{}://{}:4984/{}".format(protocol, sg1_ip, sg_db1)
    sg2_blip_url = "{}://{}:4984/{}".format(protocol, sg2_ip, sg_db2)

    sg_client.create_user(sg1_admin_url, sg_db1, name1, password=password, channels=channels1)
    sg_client.create_user(sg2_admin_url, sg_db2, name2, password=password, channels=channels1)
    # Create bulk doc json

    # 2. Create replication authenticator
    replicator = Replication(base_url)
    cookie, session_id = sg_client.create_session(sg1_admin_url, sg_db1, name1)
    authenticator = Authenticator(base_url)
    replicator_authenticator1 = authenticator.authentication(session_id, cookie, authentication_type="session")

    cookie2, session_id2 = sg_client.create_session(sg2_admin_url, sg_db2, name2)
    replicator_authenticator2 = authenticator.authentication(session_id2, cookie2, authentication_type="session")

    # Do push replication to from cbl1 to sg1 cbl -> sg1
    repl1 = replicator.configure_and_replicate(
        source_db=cbl_db1, replicator_authenticator=replicator_authenticator1, target_url=sg1_blip_url, 
        replication_type=cbl_replication_type, continuous=cbl_continuous)
    return db, num_of_docs, sg_db1, sg_db2, name1, name2, password, channels1, channels2, replicator, replicator_authenticator1, replicator_authenticator2, sg1_blip_url, sg2_blip_url, sg1, sg2, repl1, c_cluster


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
@pytest.mark.parametrize("continuous, direction", [
    (True, "push"),
    (False, "pull"),
    # (True, "push_and_pull")
])
def test_sg_replicate_pull_replication(params_from_base_test_setup, setup_customized_teardown_test, continuous, direction):
    '''
       @summary
       1.Have 2 sgw nodes , have cbl on each SGW
       2. Add docs in cbl1
       3. Do push replication to from cbl1 to sg1 cbl -> sg1
       4. pull/push/push_pull replication from sg1 -> sg2 
       5. Do pull replication from sg2 -> cbl2
       6. Verify docs created in cbl1 
           For push : sg replicate happens from sg1 -> sg2
           For pull : sg replicate happens from sg2 <- sg1
           For push_pull : sg replicaate happens sg1<-> sg2
       7. Verify the status of replication - it should have 'running' at the begining and should go to stop
    '''

    # 1.Have 2 sgw nodes , have cbl on each SGW
    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db2 = setup_customized_teardown_test["cbl_db2"]

    db, num_of_docs, sg_db1, sg_db2, name1, name2, password, channels1, _, replicator, replicator_authenticator1, replicator_authenticator2, sg1_blip_url, sg2_blip_url, sg1, sg2, repl1, _ = setup_syncGateways_with_cbl(params_from_base_test_setup, cbl_replication_type="push", cbl_continuous=False, cbl_db1=cbl_db1)
    # 2. Add docs in cbl1
    db.create_bulk_docs(num_of_docs, "Replication1", db=cbl_db1, channels=channels1)

    # 3. Do push replication to from cbl1 to sg1 cbl -> sg1
    # replicator.configure_and_replicate(
    #     source_db=cbl_db1, replicator_authenticator=replicator_authenticator1, target_url=sg1_blip_url, 
    #    replication_type="push", continuous=False)

    # 4. pull replication from sg1 -> sg2
    # TODO: change the api to new api
    if direction == "pull":
        sg2.start_replication(
            remote_url=sg1.url,
            current_db=sg_db2,
            remote_db=sg_db1,
            direction=direction,
            continuous=continuous,
            target_user_name=name1,
            target_password=password
        )
        active_tasks = sg2.admin.get_active_tasks()
    else:
        sg1.start_replication(
            remote_url=sg2.url,
            current_db=sg_db1,
            remote_db=sg_db2,
            direction=direction,
            continuous=continuous,
            target_user_name=name2,
            target_password=password
        )
        active_tasks = sg1.admin.get_active_tasks()
    if continuous:
        assert len(active_tasks) == 1
        active_task = active_tasks[0]
        time.sleep(10)  # TODO : replace with wait for replication idle after we get new API
        # get the replication id from the active tasks
        created_replication_id = active_task["replication_id"]
        if direction == "pull":
            sg2.stop_replication_by_id(created_replication_id, use_admin_url=True)
        else:
            sg1.stop_replication_by_id(created_replication_id, use_admin_url=True)
    # TODO: wait_until_replication_idle - todo : implement after dev completes
    # 5. Do pull replication from sg2 -> cbl2
    replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url,
        replication_type="pull", continuous=False
    )

    # 6. Verify docs created in cbl2
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    count1 = sum('Replication1_' in s for s in cbl_doc_ids2)
    assert count1 == num_of_docs, "all docs do not replicate to cbl db2"


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
@pytest.mark.parametrize("invalid_password, invalid_db", [
    # (True, False),
    (False, True)
])
def test_sg_replicate_invalid_auth(params_from_base_test_setup, setup_customized_teardown_test, invalid_password, invalid_db):
    '''
       @summary
       1.Have 2 sgw nodes , have cbl on each SGW
       2. Add docs in cbl1
       3. Do push replication to from cbl1 to sg1 cbl -> sg1
       4. pull replication from sg1 -> sg2 with invalid password
       5. Verify replication api throws unauthorized error
    '''

    # 1.Have 2 sgw nodes , have cbl on each SGW
    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    wrong_password = "invalid_password"
    wrong_db = "wrong_db"

    db, num_of_docs, sg_db1, sg_db2, name1, _, password, channels1, _, replicator, replicator_authenticator1, _, sg1_blip_url, _, sg1, sg2, _, _ = setup_syncGateways_with_cbl(params_from_base_test_setup, cbl_replication_type="push", cbl_continuous=False, cbl_db1=cbl_db1)
    # 2. Add docs in cbl1
    db.create_bulk_docs(num_of_docs, "Replication1", db=cbl_db1, channels=channels1)

    # 3. pull replication from sg1 -> sg2
    # TODO: change the api to new api
    try:
        if invalid_password:
            sg2.start_replication(
                remote_url=sg1.url,
                current_db=sg_db2,
                remote_db=sg_db1,
                direction="push",
                continuous=True,
                target_user_name=name1,
                target_password=wrong_password
            )
        if invalid_db:
            sg2.start_replication(
                remote_url=sg1.url,
                current_db=sg_db2,
                remote_db=wrong_db,
                direction="push",
                continuous=True,
                target_user_name=name1,
                target_password=password
            )
        assert False, "Did not throw error for invalid password"
    except HTTPError as he:
        if invalid_password:
            assert "401 Client Error: Unauthorized for url: " in str(he), "did not throw right message for invalid password"
        else:
            assert "404 Client Error: Not Found for url:" in str(he), "did not throw right message for invalid db"


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
def test_sg_replicate_withReplicationId_cancel(params_from_base_test_setup, setup_customized_teardown_test):
    '''
       @summary
       1.Have 2 sgw nodes , have cbl on each SGW
       2. Add docs in cbl1
       3. Do push replication to from cbl1 to sg1 cbl -> sg1
       4. push replication with customized replication id from sg1 -> sg2 
       5. Verify replication id is created
       6. Stop the replication
       7. Do pull replication from sg2 -> cbl2
       8. Verify docs replicated to cbl2
       9. Create more docs and verify replication does not happen to cbl2
    '''

    # 1.Have 2 sgw nodes , have cbl on each SGW
    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db2 = setup_customized_teardown_test["cbl_db2"]
    replication_id = "repl_id"

    db, num_of_docs, sg_db1, sg_db2, _, name2, password, channels1, _, replicator, replicator_authenticator1, replicator_authenticator2, sg1_blip_url, sg2_blip_url, sg1, sg2, _ = setup_syncGateways_with_cbl(params_from_base_test_setup, cbl_replication_type="push", cbl_continuous=False, cbl_db1=cbl_db1)
    # 2. Add docs in cbl1
    db.create_bulk_docs(num_of_docs, "Replication1", db=cbl_db1, channels=channels1)


    # 4. push replication with customized replication id from sg1 -> sg2 
    # TODO: change the api to new api
    sg1.start_replication(
        remote_url=sg2.url,
        current_db=sg_db1,
        remote_db=sg_db2,
        direction="push",
        continuous=True,
        target_user_name=name2,
        target_password=password,
        replication_id=replication_id
    )
    active_tasks = sg1.admin.get_active_tasks()
    time.sleep(10)  # TODO: replace with wait until replication completed
    created_replication_id = active_tasks[0]["replication_id"]
    print("created replication id ", created_replication_id)
    # 5. Verify replication id is created
    assert replication_id == created_replication_id, "custom replication id not created"
    sg1.stop_replication_by_id(replication_id, use_admin_url=True)
    # TODO: wait_until_replication_idle - todo : implement after dev completes
    # 5. Do pull replication from sg2 -> cbl2
    repl2 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url,
        replication_type="pull", continuous=True)

    # 6. Verify docs created in cbl2
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    count = sum('Replication1_' in s for s in cbl_doc_ids2)
    assert count == num_of_docs, "all docs do not replicate to cbl db2"

    # 9. Create more docs and verify replication does not happen to cbl2
    db.create_bulk_docs(num_of_docs, "Replication2", db=cbl_db1, channels=channels1)
    time.sleep(10) # TODO to replace with replication idle with new API
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    print("lenght of cbld docs ids2 after recreating docs are ", len(cbl_doc_ids2))
    count = sum('Replication2_' in s for s in cbl_doc_ids2)
    assert count == 0, "docs replicated to cbl2 though replication is cancelled"
    replicator.stop(repl1)
    replicator.stop(repl2)


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
def test_sg_replicate_oneactive_2passive(params_from_base_test_setup, setup_customized_teardown_test):
    '''
       @summary
       1. Have 3 sgw nodes :
       2. Create docs in cbl and have push_pull replication to sg1
       3. start replication on sg1 push_pull from sg1<->sg2 with db1 pointing to bucket1
       4. start replication on sg1 push_pull from sg1<->sg3 with db2 pointing to bucket2
       5. Verify docs created sg1 gets replicated to sg2 and sg3
       6. Created docs in sg3
       7. Verify New docs created in sg3 shoulid get replicated to sg1 and sg2 as it is push_pull
    '''
    sg_ssl = params_from_base_test_setup["sg_ssl"]
    base_url = params_from_base_test_setup["base_url"]
    # 1.Have 2 sgw nodes , have cbl on each SGW
    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db2 = setup_customized_teardown_test["cbl_db2"]
    cbl_db3 = setup_customized_teardown_test["cbl_db3"]
    continuous = True
    direction = "push_and_pull"
    sg_conf_name = 'listener_tests/three_sync_gateways'
    sg_client = MobileRestClient()
    
    db, num_of_docs, sg_db1, sg_db2, _, name2, password, channels1, _, replicator, _, replicator_authenticator2, _, sg2_blip_url, sg1, sg2, repl1, c_cluster = setup_syncGateways_with_cbl(params_from_base_test_setup, cbl_replication_type="push_pull", cbl_continuous=True, cbl_db1=cbl_db1, sg_conf_name=sg_conf_name)
    db.create_bulk_docs(num_of_docs, "Replication1", db=cbl_db1, channels=channels1)
    authenticator = Authenticator(base_url)
    sg3 = c_cluster.sync_gateways[2]
    sg3_ip = sg3.ip
    sg_db3 = "sg_db3"
    # channels3 = ["Replication3"]
    name3 = "autotest3"
    sg3_admin_url = sg3.admin.admin_url
    sg3_blip_url = "ws://{}:4984/{}".format(sg3_ip, sg_db3)
    if sg_ssl:
        sg3_blip_url = "wss://{}:4984/{}".format(sg3_ip, sg_db3)
    sg_client.create_user(sg3_admin_url, sg_db3, name3, password=password, channels=channels1)
    cookie, session_id = sg_client.create_session(sg3_admin_url, sg_db3, name3)
    replicator_authenticator3 = authenticator.authentication(session_id, cookie, authentication_type="session")

    repl2 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url,
        replication_type="push_pull", continuous=True)

    repl3 = replicator.configure_and_replicate(
        source_db=cbl_db3, replicator_authenticator=replicator_authenticator3, target_url=sg3_blip_url,
        replication_type="push_pull", continuous=True)

    print("sg1, sg2, sg3 urls are {}-{}-{}".format(sg1.url, sg2.url, sg3.url))
    # 3. start replication on sg1 push_pull from sg1<->sg2 with db1 pointing to bucket1
    sg1.start_replication(
        remote_url=sg2.url,
        current_db=sg_db1,
        remote_db=sg_db2,
        direction="push",
        continuous=continuous,
        target_user_name=name2,
        target_password=password
    )
    sg1.start_replication(
        remote_url=sg2.url,
        current_db=sg_db1,
        remote_db=sg_db2,
        direction="pull",
        continuous=continuous,
        target_user_name=name2,
        target_password=password
    )
    active_tasks = sg1.admin.get_active_tasks()
    print("active tasks for sg<-> replication ", active_tasks)
    # TODO : Add wait for replication for SGW too
    replicator.wait_until_replicator_idle(repl2)

    # 4. start replication on sg1 push_pull from sg1<->sg3 with db2 pointing to bucket2
    sg2.start_replication(
        remote_url=sg3.url,
        current_db=sg_db2,
        remote_db=sg_db3,
        direction="push",
        continuous=continuous,
        target_user_name=name3,
        target_password=password
    )
    sg2.start_replication(
        remote_url=sg3.url,
        current_db=sg_db2,
        remote_db=sg_db3,
        direction="pull",
        continuous=continuous,
        target_user_name=name3,
        target_password=password
    )
    active_tasks = sg2.admin.get_active_tasks()
    print("active tasks for sg<-> replication ", active_tasks)
    # 5. Verify docs created sg1 gets replicated to sg2 and sg3
    # TODO : Add wait for replication for SGW too
    # 6. Verify docs created in cbl2 and cbl3
    replicator.wait_until_replicator_idle(repl3)
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    count1 = sum('Replication1_' in s for s in cbl_doc_ids2)
    assert count1 == num_of_docs, "all docs do not replicate to cbl db2"

    cbl_doc_ids3 = db.getDocIds(cbl_db3)
    count2 = sum('Replication1_' in s for s in cbl_doc_ids3)
    assert count2 == num_of_docs, "all docs do not replicate to cbl db3"

    replicator.stop(repl1)
    replicator.stop(repl2)
    replicator.stop(repl3)

    # 6. Created docs in cbl3
    db.create_bulk_docs(num_of_docs, "Replication3", db=cbl_db1, channels=channels1)

    # 7. Verify New docs created in sg3 shoulid get replicated to sg1 and sg2 as it is push_pull
    replicator.wait_until_replicator_idle(repl3)
    replicator.wait_until_replicator_idle(repl2)
    replicator.wait_until_replicator_idle(repl1)
    cbl_doc_ids1 = db.getDocIds(cbl_db1)
    count1 = sum('Replication3_' in s for s in cbl_doc_ids1)
    assert count1 == num_of_docs, "all docs created in cbl db3 did not replicate to cbl db1"


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
def test_sg_replicate_2active_1passive(params_from_base_test_setup, setup_customized_teardown_test):
    '''
       @summary
       1. Have 3 sgw nodes and have 3 cbl db:
       2. Create docs in cbd db2 and cbl db3. 
       3. Start push_pull, continuous replicaation cbl_db2 <-> sg2, cbl_db3 <-> sg3 
       4. start replication on sg2 push_pull from sg1<->sg2 with db1 pointing to bucket1
       5. start replication on sg3 push_pull from sg1<->sg3 with db2 pointing to bucket2
       6. Wait until replication completed on sg1, cbl_db2, cbl_db3 and cbl_db1
       7. Verify all docs replicated to sg1 and cbl_db1


    '''
    sg_ssl = params_from_base_test_setup["sg_ssl"]
    base_url = params_from_base_test_setup["base_url"]
    # 1.Have 2 sgw nodes , have cbl on each SGW
    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db2 = setup_customized_teardown_test["cbl_db2"]
    cbl_db3 = setup_customized_teardown_test["cbl_db3"]
    continuous = True
    direction = "push_and_pull"
    sg_conf_name = 'listener_tests/three_sync_gateways'
    sg_client = MobileRestClient()
    # 1. Have 3 sgw nodes and have 3 cbl db:
    db, num_of_docs, sg_db1, sg_db2, name1, name2, password, channels1, _, replicator, _, replicator_authenticator2, _, sg2_blip_url, sg1, sg2, repl1, c_cluster = setup_syncGateways_with_cbl(params_from_base_test_setup, cbl_replication_type="push_pull", cbl_continuous=True, cbl_db1=cbl_db1, sg_conf_name=sg_conf_name)
    authenticator = Authenticator(base_url)
    sg3 = c_cluster.sync_gateways[2]
    sg3_ip = sg3.ip
    sg_db3 = "sg_db3"
    # channels3 = ["Replication3"]
    name3 = "autotest3"
    sg3_admin_url = sg3.admin.admin_url
    sg3_blip_url = "ws://{}:4984/{}".format(sg3_ip, sg_db3)
    if sg_ssl:
        sg3_blip_url = "wss://{}:4984/{}".format(sg3_ip, sg_db3)
    sg_client.create_user(sg3_admin_url, sg_db3, name3, password=password, channels=channels1)
    cookie, session_id = sg_client.create_session(sg3_admin_url, sg_db3, name3)
    replicator_authenticator3 = authenticator.authentication(session_id, cookie, authentication_type="session")
    
    # 2. Create docs in cbd db2 and cbl db3. 
    db.create_bulk_docs(num_of_docs, "Replication2", db=cbl_db2, channels=channels1)
    db.create_bulk_docs(num_of_docs, "Replication3", db=cbl_db2, channels=channels1)
    # 3. Start push_pull, continuous replicaation cbl_db2 <-> sg2, cbl_db3 <-> sg3 
    repl2 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url,
        replication_type="push_pull", continuous=True)

    repl3 = replicator.configure_and_replicate(
        source_db=cbl_db3, replicator_authenticator=replicator_authenticator3, target_url=sg3_blip_url,
        replication_type="push_pull", continuous=True)

    # 4. start replication on sg2 push_pull from sg1<->sg2 with db1 pointing to bucket1
    sg2.start_replication(
        remote_url=sg1.url,
        current_db=sg_db2,
        remote_db=sg_db1,
        direction="push",
        continuous=continuous,
        target_user_name=name1,
        target_password=password
    )
    sg2.start_replication(
        remote_url=sg1.url,
        current_db=sg_db2,
        remote_db=sg_db1,
        direction="pull",
        continuous=continuous,
        target_user_name=name1,
        target_password=password
    )
    print("active tasks for sg1<-> replication ", sg2.admin.get_active_tasks())

    # 4. start replication on sg1 push_pull from sg1<->sg3 with db2 pointing to bucket2
    sg3.start_replication(
        remote_url=sg1.url,
        current_db=sg_db3,
        remote_db=sg_db1,
        direction="push",
        continuous=continuous,
        target_user_name=name1,
        target_password=password
    )
    sg3.start_replication(
        remote_url=sg1.url,
        current_db=sg_db3,
        remote_db=sg_db1,
        direction="pull",
        continuous=continuous,
        target_user_name=name1,
        target_password=password
    )
    print("active tasks for sg2<-> replication ", sg2.admin.get_active_tasks())
    
    # 6. Wait until replication completed on sg1, cbl_db2, cbl_db3 and cbl_db1
    # TODO : add wait for replication for SGW
    replicator.wait_until_replicator_idle(repl1)
    replicator.wait_until_replicator_idle(repl2)
    replicator.wait_until_replicator_idle(repl3)
    cbl_doc_ids1 = db.getDocIds(cbl_db1)
    count1 = sum('Replication2_' in s for s in cbl_doc_ids1)
    assert count1 == num_of_docs, "all docs do not replicate to cbl db1 from cbl db2"

    # cbl_doc_ids3 = db.getDocIds(cbl_db3)
    count2 = sum('Replication3_' in s for s in cbl_doc_ids1)
    assert count2 == num_of_docs, "all docs do not replicate to cbl db1 from cbl db3"

    replicator.stop(repl1)
    replicator.stop(repl2)
    replicator.stop(repl3)


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
def test_sg_replicate_channel_filtering_with_attachments(params_from_base_test_setup, setup_customized_teardown_test):
    '''
       @summary
       Covered #38, #52
       1. Set up 2 sgw nodes and have two cbl dbs
       2. Create docs with attachments on cbl-db1 and have push_pull, continous replication with sg1
            each with 2 differrent channel, few docs on both channels
       3 . Start sg-replicate from sg1 to sg2 with channel1 with one shot 
       4. verify docs with channel which is filtered in replication shpuld get replicated
       5. Verify docs with channel2 is not accessed by user 2 i.e cbl db2 
    '''

    # 1.Have 2 sgw nodes , have cbl on each SGW
    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db2 = setup_customized_teardown_test["cbl_db2"]
    base_url = params_from_base_test_setup["base_url"]
    liteserv_platform = params_from_base_test_setup["liteserv_platform"]
    continuous = True
    channel1_docs = 5
    channel2_docs = 7
    channel3_docs = 8
    name3 = "autotest3"
    name4 = "autotest4"
    blob = Blob(base_url)
    dictionary = Dictionary(base_url)
    # num_of_docs = 10
    sg_client = MobileRestClient()
    authenticator = Authenticator(base_url)

    # 1. Set up 2 sgw nodes and have two cbl dbs
    db, num_of_docs, sg_db1, sg_db2, name1, name2, password, channels1, channels2, replicator, replicator_authenticator1, replicator_authenticator2, sg1_blip_url, sg2_blip_url, sg1, sg2, repl1, _ = setup_syncGateways_with_cbl(params_from_base_test_setup, cbl_replication_type="push", cbl_continuous=True, cbl_db1=cbl_db1)
    # 2. Create docs on cbl-db1 and have push_pull, continous replication with sg1
    #        each with 2 differrent channel, few docs on both channels
    
    channels3 = channels1 + channels2
    sg_client.create_user(sg1.admin.admin_url, sg_db1, name3, password=password, channels=channels3)
    sg_client.create_user(sg2.admin.admin_url, sg_db2, name4, password=password, channels=channels3)
    
    cookie, session_id = sg_client.create_session(sg1.admin.admin_url, sg_db1, name3)
    replicator_authenticator3 = authenticator.authentication(session_id, cookie, authentication_type="session")
    cookie, session_id = sg_client.create_session(sg2.admin.admin_url, sg_db2, name4)
    replicator_authenticator4 = authenticator.authentication(session_id, cookie, authentication_type="session")

    # Create docs with attachments
    channel1_doc_ids = db.create_bulk_docs(channel1_docs, "Replication1_channel1", db=cbl_db1, channels=channels1)
    db.create_bulk_docs(channel2_docs, "Replication1_channel2", db=cbl_db1, channels=channels2, attachments_generator=attachment.generate_png_100_100)
    channel3_doc_ids = db.create_bulk_docs(channel3_docs, "Replication1_channel3", db=cbl_db1, channels=channels3, attachments_generator=attachment.generate_png_100_100)

    repl3 = replicator.configure_and_replicate(
        source_db=cbl_db1, replicator_authenticator=replicator_authenticator3, target_url=sg1_blip_url, 
        replication_type="push", continuous=True)
    # 4. pull replication from sg1 -> sg2
    # TODO: change the api to new api
    sg1.start_replication(
        remote_url=sg2.url,
        current_db=sg_db1,
        remote_db=sg_db2,
        direction="push",
        continuous=continuous,
        channels=channels1,
        target_user_name=name4,
        target_password=password
    )

    # 4. verify docs with channel1 which is filtered in replication shpuld get replicated to cbl_db2
    # TODO: wait_until_replication_idle - todo : implement after dev completes
    # Do pull replication from sg2 -> cbl2
    repl2 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator4, target_url=sg2_blip_url,
        replication_type="pull", continuous=True
    )

    # update docs by adding attachments
    print("channel 1 docs ids are ", channel1_doc_ids)
    db.update_bulk_docs_with_blob(cbl_db1, dictionary, blob, liteserv_platform, doc_ids=channel1_doc_ids)
    # update docs by deleting attachments
    db.update_bulk_docs_by_deleting_blobs(cbl_db1, doc_ids=channel3_doc_ids)

    # wait until replication completed
    replicator.wait_until_replicator_idle(repl1)
    replicator.wait_until_replicator_idle(repl2)
    # Verify docs created in cbl2
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    count = sum('Replication1_channel1_' in s for s in cbl_doc_ids2)
    assert count == channel1_docs, "all docs with channel1 did not replicate to cbl db2"
    count = sum('Replication1_channel3_' in s for s in cbl_doc_ids2)
    assert count == channel3_docs, "all docs with channel1 and channel2 did not replicate to cbl db2"

    # 5. Verify docs with channel2 is not accessed by user 2 i.e cbl db2
    count = sum('Replication1_channel2_' in s for s in cbl_doc_ids2)
    assert count == 0, "all docs with channel2 replicated to cbl db2"

    # 6. Verify all docs updated with attachments
    cbl_db_docs = db.getDocuments(cbl_db2, cbl_doc_ids2)
    for doc_id in cbl_doc_ids2:
        if 'Replication1_channel1_' in doc_id:
            assert "_attachments" in cbl_db_docs[doc_id], "attachment did not updated on cbl_db2"
            assert "updates-cbl" in cbl_db_docs[doc_id],  "docs updated in cbl-db1 with new property did not replicated to cbl-db2"
        if 'Replication1_channel3_' in doc_id:
            assert "_attachments" not in cbl_db_docs[doc_id], "attachment which deleted on doc in cbl_db1 did not replicate to cbl-db2"

    replicator.stop(repl1)
    replicator.stop(repl2)
    replicator.stop(repl3)


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
@pytest.mark.parametrize("direction", [
    # ("push"),
    # ("pull"),
    ("push_and_pull")
])
def test_sg_replicate_pull_pushPull_channel_filtering(params_from_base_test_setup, setup_customized_teardown_test, direction):
    '''
       @summary
       Covered #53, #54
       1. Set up 2 sgw nodes and have two cbl dbs
       2. Create docs cbl-db1 and cbl-db2 and have push_pull, continous replication
            sg1 <-> cbl-db1, sg2 <-> cbl-db2
            each with 2 differrent channel, few docs on both channels
       3 . Start sg-replicate pull/push_pull replicaation from sg1 <-> sg2 with channel1 with one shot 
       4. verify docs with channel1 is  pulled from sg2 to sg1 for pull case
            docs with channel1 is pushed and pulled sg <-> sg2 for push pull case
       5. Verify docs with filtered channel is replicated on both cbl-db1 and cbl-db2
    '''

    # 1.Have 2 sgw nodes , have cbl on each SGW
    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db2 = setup_customized_teardown_test["cbl_db2"]
    base_url = params_from_base_test_setup["base_url"]
    # liteserv_platform = params_from_base_test_setup["liteserv_platform"]
    continuous = True
    channel1_docs = 5
    channel2_docs = 7
    channel3_docs = 8
    name3 = "autotest3"
    name4 = "autotest4"
    # blob = Blob(base_url)
    # dictionary = Dictionary(base_url)
    # num_of_docs = 10
    sg_client = MobileRestClient()
    authenticator = Authenticator(base_url)

    # 1. Set up 2 sgw nodes and have two cbl dbs
    db, num_of_docs, sg_db1, sg_db2, name1, name2, password, channels1, channels2, replicator, replicator_authenticator1, replicator_authenticator2, sg1_blip_url, sg2_blip_url, sg1, sg2, repl1, _ = setup_syncGateways_with_cbl(params_from_base_test_setup, cbl_replication_type="push_pull", cbl_continuous=continuous, cbl_db1=cbl_db1)
    
    # Need to create these users to have users access to both channel1 and channel2 access
    channels3 = channels1 + channels2
    sg_client.create_user(sg1.admin.admin_url, sg_db1, name3, password=password, channels=channels3)
    sg_client.create_user(sg2.admin.admin_url, sg_db2, name4, password=password, channels=channels3)
    
    cookie, session_id = sg_client.create_session(sg1.admin.admin_url, sg_db1, name3)
    replicator_authenticator3 = authenticator.authentication(session_id, cookie, authentication_type="session")
    cookie, session_id = sg_client.create_session(sg2.admin.admin_url, sg_db2, name4)
    replicator_authenticator4 = authenticator.authentication(session_id, cookie, authentication_type="session")

    # Create docs with attachments on cbl_db1 for pull
    db.create_bulk_docs(channel1_docs, "Replication1_channel1", db=cbl_db2, channels=channels1)
    db.create_bulk_docs(channel2_docs, "Replication1_channel2", db=cbl_db2, channels=channels2, attachments_generator=attachment.generate_png_100_100)
    db.create_bulk_docs(channel3_docs, "Replication1_channel3", db=cbl_db2, channels=channels3, attachments_generator=attachment.generate_png_100_100)
    
    # Create docs with attachments on cbl_db1 for push_pull 
    db.create_bulk_docs(channel1_docs, "Replication2_channel1", db=cbl_db1, channels=channels1)

    repl3 = replicator.configure_and_replicate(
        source_db=cbl_db1, replicator_authenticator=replicator_authenticator3, target_url=sg1_blip_url, 
        replication_type="push_pull", continuous=True)
    # 4. pull replication from sg1 -> sg2
    # TODO: change the api to new api
    if direction == "push_and_pull":
        sg1.start_replication(
            remote_url=sg2.url,
            current_db=sg_db1,
            remote_db=sg_db2,
            direction="push",
            continuous=continuous,
            channels=channels1,
            target_user_name=name4,
            target_password=password
        )
    sg1.start_replication(
        remote_url=sg2.url,
        current_db=sg_db1,
        remote_db=sg_db2,
        direction="pull",
        continuous=continuous,
        channels=channels1,
        target_user_name=name4,
        target_password=password
    )

    # 4. verify docs with channel1 which is filtered in replication shpuld get replicated to cbl_db2
    # TODO: wait_until_replication_idle - todo : implement after dev completes
    # Do pull replication from sg2 -> cbl2
    repl2 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator4, target_url=sg2_blip_url,
        replication_type="push_pull", continuous=True
    )


    """# wait until replication completed
    replicator.wait_until_replicator_idle(repl1)
    replicator.wait_until_replicator_idle(repl2)"""
    # Verify docs replicated to cbl_db1
    cbl_doc_ids1 = db.getDocIds(cbl_db1)
    count = sum('Replication1_channel1_' in s for s in cbl_doc_ids1)
    assert count == channel1_docs, "all docs with channel1 did not replicate to cbl db1"
    count = sum('Replication1_channel3_' in s for s in cbl_doc_ids1)
    assert count == channel3_docs, "all docs with channel3 did not replicated to cbl db1"

    # 5. Verify docs with channel2 is not accessed by user 3 i.e cbl db1
    count = sum('Replication1_channel2_' in s for s in cbl_doc_ids1)
    assert count == 0, "all docs with channel2 replicated to cbl db1"

    # 6. Verify all docs replicated to cbl_db2 with push_pull
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    count = sum('Replication2_channel1_' in s for s in cbl_doc_ids2)
    assert count == channel1_docs, "all docs with channel1 did not replicate to cbl db2"

    replicator.stop(repl1)
    replicator.stop(repl2)
    replicator.stop(repl3)


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
@pytest.mark.parametrize("reconnect_interval", [
    # (True),
    (False)
])
def test_sg_replicate_with_sg_restart(params_from_base_test_setup, setup_customized_teardown_test, reconnect_interval):
    '''
       @summary
       1. Set up 2 sgw nodes and have two cbl dbs
          Test with sgw config with reconnect-interval and without reconnect-interval
       2. Create docs on cbl-db1 and have push_pull, continous replication with sg1
       3. Start replication with continuous true sg1<->sg2
       4. Update docs on sg1   -> Thread1 
       5. restart sg2 While replication is happening -> thead 2
           stop the node for a minute and restart when reconnect_interval is true
          Parallel execution step 4 and step 5
       7. verify all docs got replicated on sg2
    '''

    # 1.Have 2 sgw nodes , have cbl on each SGW
    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db2 = setup_customized_teardown_test["cbl_db2"]
    # base_url = params_from_base_test_setup["base_url"]
    sg_mode = params_from_base_test_setup["mode"]
    continuous = True
    if reconnect_interval:
        sg_conf_name = 'listener_tests/multiple_sync_gateways' # TODO: updaate with sgw config with reconnect interval
    else:
        sg_conf_name = 'listener_tests/multiple_sync_gateways'
    # sg_client = MobileRestClient()
    # authenticator = Authenticator(base_url)
    cluster_config = "{}/three_sync_gateways_{}".format(CLUSTER_CONFIGS_DIR, sg_mode)
    sg_conf_name = 'listener_tests/multiple_sync_gateways'
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)

    # 1. Set up 2 sgw nodes and have two cbl dbs
    db, num_of_docs, sg_db1, sg_db2, name1, name2, password, channels1, channels2, replicator, replicator_authenticator1, replicator_authenticator2, sg1_blip_url, sg2_blip_url, sg1, sg2, repl1, c_cluster = setup_syncGateways_with_cbl(params_from_base_test_setup, cbl_replication_type="push", cbl_continuous=True, cbl_db1=cbl_db1)

    # 2. Create docs on cbl-db1 and have push_pull, continous replication with sg1
    db.create_bulk_docs(num_of_docs, "Replication1_", db=cbl_db1, channels=channels1, attachments_generator=attachment.generate_png_100_100)

    # 3. Start replication with continuous true sg1<->sg2
    # TODO: change the api to new api
    sg1.start_replication(
        remote_url=sg2.url,
        current_db=sg_db1,
        remote_db=sg_db2,
        direction="push",
        continuous=continuous,
        channels=channels1,
        target_user_name=name2,
        target_password=password
    )
    sg1.start_replication(
        remote_url=sg2.url,
        current_db=sg_db1,
        remote_db=sg_db2,
        direction="pull",
        continuous=continuous,
        channels=channels1,
        target_user_name=name2,
        target_password=password
    )
    with ThreadPoolExecutor(max_workers=4) as tpe:
        # 4. Update docs on sg1
        cbl_db1_docs = tpe.submit(db.create_bulk_docs, num_of_docs, "Replication2_", db=cbl_db1, channels=channels1)

        # 5. restart sg2 While replication is happening
        if reconnect_interval:
            c_cluster.sync_gateways[1].stop()
            time.sleep(60) # Need to wait for a minute to restart
        restart_sg = tpe.submit(c_cluster.sync_gateways[1].restart, config=sg_conf, cluster_config=cluster_config)
        cbl_db1_docs.result()
        restart_sg.result()

    # 7. verify all docs got replicated on sg2
    repl2 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url, 
        replication_type="pull", continuous=continuous)
    replicator.wait_until_replicator_idle(repl2)
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    count = sum('Replication2_' in s for s in cbl_doc_ids2)
    assert count == num_of_docs, "all docs with channel1 did not replicate to cbl db2"
    replicator.stop(repl1)
    replicator.stop(repl2)


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
def test_sg_replicate_multiple_replications_with_filters(params_from_base_test_setup, setup_customized_teardown_test):
    '''
       @summary
       Covered #55
       "1.create docs with mutlple  channels, channel1, channel2, channel3..
        2. start replication for each channel with push_pull
        3. verfiy docs get replicated to sg2"
    '''

    # Have 2 sgw nodes , have cbl on each SGW
    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db2 = setup_customized_teardown_test["cbl_db2"]
    base_url = params_from_base_test_setup["base_url"]
    # direction = "push_pull"
    continuous = True
    channel1_docs = 5
    channel2_docs = 7
    channel3_docs = 8
    name3 = "autotest3"
    name4 = "autotest4"
    channels3 = ["Replication3"]
    sg_client = MobileRestClient()
    authenticator = Authenticator(base_url)

    # Set up 2 sgw nodes and have two cbl dbs
    db, num_of_docs, sg_db1, sg_db2, name1, name2, password, channels1, channels2, replicator, replicator_authenticator1, replicator_authenticator2, sg1_blip_url, sg2_blip_url, sg1, sg2, repl1, _ = setup_syncGateways_with_cbl(params_from_base_test_setup, cbl_replication_type="push_pull", cbl_continuous=continuous, cbl_db1=cbl_db1)
    channels = channels1 + channels2 + channels3
    channels_list = [channels1, channels2, channels3]
    # channels.append(channels1)
    # channels.append(channels2)
    # channels.append(channels3)
    # Need to create these users to have users access to both channel1 and channel2 access
    # channels_3 = channels1 + channels2 + channels3
    sg_client.create_user(sg1.admin.admin_url, sg_db1, name3, password=password, channels=channels)
    sg_client.create_user(sg2.admin.admin_url, sg_db2, name4, password=password, channels=channels)

    cookie, session_id = sg_client.create_session(sg1.admin.admin_url, sg_db1, name3)
    replicator_authenticator3 = authenticator.authentication(session_id, cookie, authentication_type="session")
    cookie, session_id = sg_client.create_session(sg2.admin.admin_url, sg_db2, name4)
    replicator_authenticator4 = authenticator.authentication(session_id, cookie, authentication_type="session")

    # 1.create docs with mutlple  channels, channel1, channel2, channel3..
    db.create_bulk_docs(channel1_docs, "Replication1_channel1", db=cbl_db1, channels=channels1)
    db.create_bulk_docs(channel2_docs, "Replication1_channel2", db=cbl_db1, channels=channels2)
    db.create_bulk_docs(channel3_docs, "Replication1_channel3", db=cbl_db1, channels=channels3)

    repl3 = replicator.configure_and_replicate(
        source_db=cbl_db1, replicator_authenticator=replicator_authenticator3, target_url=sg1_blip_url, 
        replication_type="push_pull", continuous=True)
    # 4. pull replication from sg1 -> sg2
    # TODO: change the api to new api
    # 2. start replication for each channel with push_pull

    for channel in channels_list:
        sg1.start_replication(
            remote_url=sg2.url,
            current_db=sg_db1,
            remote_db=sg_db2,
            direction="push",
            continuous=continuous,
            channels=channel,
            target_user_name=name4,
            target_password=password
        )
        sg1.start_replication(
            remote_url=sg2.url,
            current_db=sg_db1,
            remote_db=sg_db2,
            direction="pull",
            continuous=continuous,
            channels=channel,
            target_user_name=name4,
            target_password=password
        )
    # TODO : To modify active tasks
    active_tasks = sg1.admin.get_active_tasks()
    assert len(active_tasks) == 6

    # Do pull replication from sg2 -> cbl2
    repl4 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator4, target_url=sg2_blip_url,
        replication_type="push_pull", continuous=True
    )

    # 3. Verify docs created in sg2 and eventually replicated to cbl2
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    count = sum('Replication1_channel1' in s for s in cbl_doc_ids2)
    assert count == channel1_docs, "docs with  Replication1_channel1 did not replicate to cbl db2"
    count = sum('Replication1_channel2' in s for s in cbl_doc_ids2)
    assert count == channel2_docs, "docs with  Replication1_channel2 did not replicate to cbl db2"
    count = sum('Replication1_channel3' in s for s in cbl_doc_ids2)
    assert count == channel3_docs, "docs with  Replication1_channel3 did not replicate to cbl db2"

    # update docs by deleting/replace  channel
    cbl_db_docs = db.getDocuments(cbl_db2, cbl_doc_ids2)
    for doc in cbl_db_docs:
        if cbl_db_docs[doc]["channels"] == ["Replication3"]:
            print("yes it i has replication channel3")
            cbl_db_docs[doc]["channels"] = ["Replication4"]
    db.updateDocuments(cbl_db2, cbl_db_docs)
    
    time.sleep(10) ## replace with wait_until_replication idel for SGW
    # 3. Verify docs update in sg2/cbl_db2 are replicated and updated on sg_db1/cbl_db1
    cbl_doc_ids1 = db.getDocIds(cbl_db1)

    count1 = sum('Replication1_channel3' in s for s in cbl_doc_ids1)
    assert count1 == 0, "docs with  Replication1_channel3 did not get updated  to cbl db1"

    replicator.stop(repl1)
    # replicator.stop(repl2)
    replicator.stop(repl3)
    replicator.stop(repl4)


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
def test_sg_replicate_replications_with_drop_out_one_node(params_from_base_test_setup, setup_customized_teardown_test):
    '''
       @summary
       Covered for #64
       have 3 sgw nodes. 
       1. Have 2 nodes on one cluster which are active nodes
       2. Start 2 replications
       3. verify only one replication runs only one node. 
       4. Drop one active sgw node 
       5. Verify both the replications runs on one sgw node of active cluster
       6. Verify replication completes all docs replicated to destination node
       7. verify rest api active tasks
       9. Verify rest api _replicationstatus
    '''
    sg_ssl = params_from_base_test_setup["sg_ssl"]
    base_url = params_from_base_test_setup["base_url"]
    sg_mode = params_from_base_test_setup["mode"]
    sg_ce = params_from_base_test_setup["sg_ce"]
    # 1.Have 2 sgw nodes , have cbl on each SGW
    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db2 = setup_customized_teardown_test["cbl_db2"]
    cbl_db3 = setup_customized_teardown_test["cbl_db3"]
    sg_conf_name = 'listener_tests/three_sync_gateways'
    sg_db3 = "sg_db3"
    name3 = "autotest3"
    channels1 = ["Replication1"]
    channels2 = ["Replication2"]
    channels3 = channels1 + channels2

    # set up 2 sgw nodes in one cluster by pointing sg_db1 and sg_db2 to same data-bucket
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)
    temp_sg_config, temp_sg_conf_name = copy_sgconf_to_temp(sg_config, sg_mode)
    with open(temp_sg_config, 'r') as file:
        filedata = file.read()
    filedata = filedata.replace('data-bucket-2', "{}".format("data-bucket-1"))
    with open(temp_sg_config, 'w') as file:
        file.write(filedata)

    sg_client = MobileRestClient()
    db, num_of_docs, sg_db1, sg_db2, name1, name2, password, _, _, replicator, _, replicator_authenticator2, _, sg2_blip_url, sg1, sg2, repl1, c_cluster = setup_syncGateways_with_cbl(params_from_base_test_setup, cbl_replication_type="push_pull", cbl_continuous=True, cbl_db1=cbl_db1, sg_conf_name=temp_sg_conf_name, channels1=channels3)
    authenticator = Authenticator(base_url)
    sg3 = c_cluster.sync_gateways[2]
    sg3_ip = sg3.ip
    channels3 = channels1 + channels2
    sg3_admin_url = sg3.admin.admin_url
    sg3_blip_url = "ws://{}:4984/{}".format(sg3_ip, sg_db3)
    if sg_ssl:
        sg3_blip_url = "wss://{}:4984/{}".format(sg3_ip, sg_db3)
    sg_client.create_user(sg3_admin_url, sg_db3, name3, password=password, channels=channels3)
    cookie, session_id = sg_client.create_session(sg3_admin_url, sg_db3, name3)
    replicator_authenticator3 = authenticator.authentication(session_id, cookie, authentication_type="session")
    
    db.create_bulk_docs(num_of_docs, "Replication1", db=cbl_db1, channels=channels1)
    db.create_bulk_docs(num_of_docs, "Replication2", db=cbl_db2, channels=channels2)
    repl2 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url,
        replication_type="push_pull", continuous=True)

    repl3 = replicator.configure_and_replicate(
        source_db=cbl_db3, replicator_authenticator=replicator_authenticator3, target_url=sg3_blip_url,
        replication_type="push_pull", continuous=True)

    replicator.wait_until_replicator_idle(repl1)
    replicator.wait_until_replicator_idle(repl2)
    # 2. Start 2 replications on cluster 1
    sgw_repl1 = sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg3.url,
        remote_db=sg_db3,
        remote_user=name3,
        remote_password=password,
        direction="push",
        channels=channels1
    )
    sgw_repl2 = sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg3.url,
        remote_db=sg_db3,
        remote_user=name3,
        remote_password=password,
        direction="push",
        channels=channels2
    )
    print("sgw replications 1 , ", sgw_repl1)
    print("sgw replications 2 , ", sgw_repl2)
    print("active tasks for sg1<-> replication ", sg1.admin.get_sgreplicate2_active_tasks(sg_db1))
    active_tasks = sg1.admin.get_sgreplicate2_active_tasks(sg_db1)
    assert len(active_tasks) == 2, "did not show right number of tasks "

    # 3. verify only one replication runs only one node.
    # TODO:
    if sg_ce:
        print("TODO")
        # TODO: 2 replications should run on each node
    else:
        print("TODO")
        # TODO: 1 replication should run on each node

    # 4. Drop one active sgw node
    sg2.stop()
    
    # 5. Verify both the replications runs on one sgw node of active cluster
    active_tasks = sg1.admin.get_sgreplicate2_active_tasks(sg_db1)
    # TODO: Add verification that 2 replications run on sg1

    # 6. Verify replication completes all docs replicated to destination node
    db.create_bulk_docs(num_of_docs, "Replication3", db=cbl_db1, channels=channels1)

    sg1.admin.wait_untl_sgw_replication_done(sg_db1, sgw_repl1)
    replicator.wait_until_replicator_idle(repl3)
    cbl_doc_ids3 = db.getDocIds(cbl_db3)
    count = sum('Replication1_' in s for s in cbl_doc_ids3)
    assert count == num_of_docs, "all docs do not replicate from cbl_db1 to cbl_db3"
    count2 = sum('Replication2_' in s for s in cbl_doc_ids3)
    assert count2 == num_of_docs, "all docs do not replicate from cbl_db2 to cbl_db3"
    count3 = sum('Replication3_' in s for s in cbl_doc_ids3)
    assert count3 == num_of_docs, "all docs do not replicate from cbl_db1 to cbl_db3"

    replicator.stop(repl1)
    replicator.stop(repl2)
    replicator.stop(repl3)


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
def test_sg_replicate_config_replications_with_opt_out(params_from_base_test_setup, setup_customized_teardown_test):
    '''
       @summary
       Covered #62
       1. start 3 replications for 3 nodes
       2. Have 3rd node with opt out on sgw-config
       3. Verify 3 replications are distributed to first 2 nodes
    '''

    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_ssl = params_from_base_test_setup["sg_ssl"]
    base_url = params_from_base_test_setup["base_url"]
    sg_conf_name = 'listener_tests/four_sync_gateways'
    sg_conf_name2 = 'listener_tests/listener_tests_with_replications'
    sg_conf_name3 = 'listener_tests/listener_tests_with_static_bucket'
    # cluster_config1 = 'four_sync_gateways_'
    channels3 = ['Replication3']
    sg_client = MobileRestClient()
    authenticator = Authenticator(base_url)
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name2, sg_mode)
    sg_config3 = sync_gateway_config_path_for_mode(sg_conf_name3, sg_mode)
    # Have 2 sgw nodes , have cbl on each SGW
    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db2 = setup_customized_teardown_test["cbl_db2"]
    cbl_db3 = setup_customized_teardown_test["cbl_db3"]

    db, num_of_docs, sg_db1, sg_db2, name1, name2, password, channels1, channels2, replicator, replicator_authenticator1, replicator_authenticator2, sg1_blip_url, sg2_blip_url, sg1, sg2, repl1, c_cluster = setup_syncGateways_with_cbl(params_from_base_test_setup, cbl_replication_type="push", cbl_continuous=False, cbl_db1=cbl_db1, sg_conf_name=sg_conf_name)

    name3 = "autotest3"
    name4 = "autotest4"
    sg_db4 = "sg_db4"
    sg_db3 = "sg_db3"
    sg_db = "db"
    sg3 = c_cluster.sync_gateways[2]
    sg4 = c_cluster.sync_gateways[3]
    sg4_ip = sg4.ip
    sg3_admin_url = sg3.admin.admin_url
    sg4_admin_url = sg4.admin.admin_url
    sg4_blip_url = "ws://{}:4984/{}".format(sg4_ip, sg_db4)
    if sg_ssl:
        sg4_blip_url = "wss://{}:4984/{}".format(sg4_ip, sg_db4)
    sg_client.create_user(sg3_admin_url, sg_db3, name3, password=password, channels=channels3)
    cookie, session_id = sg_client.create_session(sg3_admin_url, sg_db3, name3)
    user3_session = cookie, session_id
    sg_client.create_user(sg4_admin_url, sg_db4, name4, password=password, channels=channels1)
    cookie, session_id = sg_client.create_session(sg4_admin_url, sg_db4, name4)
    replicator_authenticator4 = authenticator.authentication(session_id, cookie, authentication_type="session")
    
    db.create_bulk_docs(num_of_docs, "Replication1_channel1", db=cbl_db1, channels=channels1)
    db.create_bulk_docs(num_of_docs, "Replication1_channel2", db=cbl_db2, channels=channels2)
    sg_docs = document.create_docs("Replication1_channel3", number=num_of_docs, channels=channels3)
    sg_client.add_bulk_docs(url=sg3.url, db=sg_db3, docs=sg_docs, auth=user3_session)
    # 1. start 3 replications for 3 nodes
    temp_sg_config, _ = copy_sgconf_to_temp(sg_config, sg_mode)
    replication_1, sgw_repl1 = setup_replications_on_sgconfig(sg4_blip_url, name4, password, channels=channels1, continuous=True)
    replication_2, _ = setup_replications_on_sgconfig(sg4_blip_url, name4, password, channels=channels2, continuous=True)
    replication_3, _ = setup_replications_on_sgconfig(sg4_blip_url, name4, password, channels=channels3, continuous=True)

    print("replications 1 -", replication_1)
    print("replications 2 - ", replication_2)
    print("replications 3 - ", replication_3)

    replications_ids = "{},{},{}".format(replication_1, replication_2, replication_3)
    replications_key = "replications"
    replace_string = "\"{}\": {}{}{},".format(replications_key, "{", replications_ids, "}")

    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ replace_with_replications }}", replace_string)
    sg1.restart(config=temp_sg_config, cluster_config=cluster_config)
    temp_sg_config, _ = copy_sgconf_to_temp(sg_config3, sg_mode)
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "\"db\"", "sg_db2")
    sg2.restart(config=temp_sg_config, cluster_config=cluster_config)

    # 2. Have 3rd node with opt out on sgw-config
    temp_sg_config, _ = copy_sgconf_to_temp(sg_config, sg_mode)
    replace_string3 = "\"sgreplicate_enabled\": False,"
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ replace_with_replications }}", replace_string3)
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "\"db\"", "\"sg_db3\"")
    sg3.restart(config=temp_sg_config, cluster_config=cluster_config)
    # sg2_blip_url = sg2_blip_url.replace("sg_db2", "db")
    repl2 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url, 
        replication_type="push", continuous=True)
    repl4 = replicator.configure_and_replicate(
        source_db=cbl_db3, replicator_authenticator=replicator_authenticator4, target_url=sg4_blip_url, 
        replication_type="pull", continuous=True)
    active_tasks = sg1.admin.get_sgreplicate2_active_tasks(sg_db)
    # 3. Verify 3 replications are distributed to first 2 nodes
    # TODO : Verify only one replication run on each sgw node
    # TODO : verify replication_status that replications distributed on 2 nodes
    replicator.wait_until_replicator_idle(repl1)
    replicator.wait_until_replicator_idle(repl2)
    sg1.admin.wait_untl_sgw_replication_done(sg_db1, sgw_repl1)
    replicator.wait_until_replicator_idle(repl4)
    cbl_doc_ids3 = db.getDocIds(cbl_db3)
    count = sum('Replication1_' in s for s in cbl_doc_ids3)
    assert count == num_of_docs, "all docs do not replicate from cbl_db1 to cbl_db3"
    count2 = sum('Replication2_' in s for s in cbl_doc_ids3)
    assert count2 == num_of_docs, "all docs do not replicate from cbl_db2 to cbl_db3"
    count3 = sum('Replication3_' in s for s in cbl_doc_ids3)
    assert count3 == num_of_docs, "all docs do not replicate from cbl_db1 to cbl_db3"

    replicator.stop(repl1)
    replicator.stop(repl2)
    replicator.stop(repl4)


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
@pytest.mark.parametrize("number_of_replications", [
    (1),
    (3),
    (4),
    (6)
])
def test_sg_replicate_distributions_replications(params_from_base_test_setup, setup_customized_teardown_test, number_of_replications):
    '''
       @summary
       Covered for #67
       "Have multiple replications
       1. Set up 4 nodes - 3 active and 1 passive
        Test with following params for replications:
        1, 3, 4, 6 
        Verify rest api to check replications on each node
        Verify replications run accordingly
        1. 1 replication - one of the SGW node
        2. 3 - one on each SGW node 
        3. 4 - one sgw node should run 2 replications and other sgw nodes should run one on each
        4. 6 - 2 on each sgw node
    '''

    sg_ssl = params_from_base_test_setup["sg_ssl"]
    base_url = params_from_base_test_setup["base_url"]
    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db3 = setup_customized_teardown_test["cbl_db3"]
    # sg_conf_name = 'listener_tests/four_sync_gateways'
    replicator = Replication(base_url)
    sg_db4 = "sg_db4"
    name4 = "autotest4"
    channels1 = ["Replication1"]
    channels2 = ["Replication2"]
    channels3 = ["Replication3"]
    channels4 = ["Replication4"]
    channels5 = ["Replication5"]
    channels6 = ["Replication6"]

    channels_6 = channels1 + channels2 + channels3 + channels4 + channels5 + channels6
    # sg_client = MobileRestClient()
    db, num_of_docs, sg_db1, sg_db2, name1, name2, password, _, _, replicator, _, replicator_authenticator2, _, sg2_blip_url, sg1, sg2, repl1, c_cluster = setup_syncGateways_with_cbl(params_from_base_test_setup, cbl_replication_type="push_pull", cbl_continuous=True, cbl_db1=cbl_db1, channels1=channels_6)
    # authenticator = Authenticator(base_url)
    sg4, sg_db4, sg4_admin_url, sg4_blip_url = get_sg4(params_from_base_test_setup, c_cluster)
    replicator_authenticator4 = create_sguser_cbl_authenticator(base_url, sg4_admin_url, sg_db4, name4, password, channels1)

    # Create replications and docs based on parameters passed
    for x in range(number_of_replications):
        channel_name = "Replication-{}".format(x)
        db.create_bulk_docs(num_of_docs, channel_name, db=cbl_db1, channels=[channels_6[x]])

    sgw_repl_id = []
    for x in range(number_of_replications):
        replication_channel = []
        replication_channel.append(channels_6[x])
        # for channel in channels_6:
        repl_id_x = sg1.start_replication2(
            local_db=sg_db1,
            remote_url=sg4.url,
            remote_db=sg_db4,
            remote_user=name4,
            remote_password=password,
            direction="push",
            channels=[channels_6[x]]
        )
        sgw_repl_id.append(repl_id_x)

    repl4 = replicator.configure_and_replicate(
        source_db=cbl_db3, replicator_authenticator=replicator_authenticator4, target_url=sg4_blip_url,
        replication_type="push_pull", continuous=True)
    replicator.wait_until_replicator_idle(repl1)

    print("active tasks for sg1<-> replication ", sg1.admin.get_sgreplicate2_active_tasks(sg_db1))
    active_tasks = sg1.admin.get_sgreplicate2_active_tasks(sg_db1)
    assert len(active_tasks) == 2, "did not show right number of tasks "

    # 3. verify only one replication runs only one node.
    print("TODO")
    # TODO: 1 replication should run on each node

    # 5. Verify both the replications runs on one sgw node of active cluster
    active_tasks = sg1.admin.get_sgreplicate2_active_tasks(sg_db1)
    # TODO: Verify replications distributed evenly to all 3 nodes based on parameter

    for x in range(number_of_replications):
        sg1.admin.wait_untl_sgw_replication_done(sg_db1, sgw_repl_id[x])
    replicator.wait_until_replicator_idle(repl4)
    cbl_doc_ids3 = db.getDocIds(cbl_db3)
    for x in range(number_of_replications):
        replication_name = "Replication-{}".format(x)
        count = sum(replication_name in s for s in cbl_doc_ids3)
        assert_msg = "all docs of replication - {} did not replicate from cbl_db1 to cbl_db3".format(replication_name)
        assert count == num_of_docs, assert_msg

    replicator.stop(repl1)
    replicator.stop(repl4)


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
def test_sg_replicate_update_sgw_nodes_in_cluster(params_from_base_test_setup, setup_customized_teardown_test):
    '''
       @summary
       Covered for #68
       "can have 4 nodes(3 active and 1 passive) first.
        1. create docs on sg1 and sg2.
        2. start 3 replications
        3. update docs - Thread 1
        4. Remove 3rd active node  - Thread2
            Verify 2 replications run on 1st node and 1 replication on 2nd node
        5. Add 3rd node back - Thread2
            Verify 1 replications run on each node
        6. Verify all replications completed on passive node(sg4)
    '''

    base_url = params_from_base_test_setup["base_url"]
    sg_mode = params_from_base_test_setup["mode"]
    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db2 = setup_customized_teardown_test["cbl_db2"]
    cbl_db3 = setup_customized_teardown_test["cbl_db3"]
    sg_conf_name = 'listener_tests/four_sync_gateways'
    replicator = Replication(base_url)
    name4 = "autotest4"
    channels3 = ["Replication3"]
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)

    db, num_of_docs, sg_db1, sg_db2, name1, name2, password, channels1, channels2, replicator, _, replicator_authenticator2, _, sg2_blip_url, sg1, sg2, repl1, c_cluster = setup_syncGateways_with_cbl(params_from_base_test_setup, cbl_replication_type="push_pull", cbl_continuous=True, cbl_db1=cbl_db1)
    all_channels = channels1 + channels2 + channels3
    sg3 = c_cluster.sync_gateways[2]

    sg4, sg_db4, sg4_admin_url, sg4_blip_url = get_sg4(params_from_base_test_setup, c_cluster)
    replicator_authenticator4 = create_sguser_cbl_authenticator(base_url, sg4_admin_url, sg_db4, name4, password, channels1)

    #1. create docs on sg1 and sg2 using cbl_db1 and cbl_db2
    db.create_bulk_docs(num_of_docs, "Replication1", db=cbl_db1, channels=channels1)
    db.create_bulk_docs(num_of_docs, "Replication2", db=cbl_db2, channels=channels1)

    # Have replication from cbl_db2 to sg2
    repl2 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url, 
        replication_type="push_pull", continuous=True)

    repl4 = replicator.configure_and_replicate(
        source_db=cbl_db3, replicator_authenticator=replicator_authenticator4, target_url=sg4_blip_url, 
        replication_type="push_pull", continuous=True)

    # 2. start 3 replications
    sgw_repl_id = []
    #for x in range(number_of_replications):
    for channel in all_channels:
        repl_id_x = sg1.start_replication2(
            local_db=sg_db1,
            remote_url=sg4.url,
            remote_db=sg_db4,
            remote_user=name4,
            remote_password=password,
            direction="push",
            continuous=True,
            channels=[channel]
        )
        sgw_repl_id.append(repl_id_x)

    # 3. update docs - Thread 1
    # 4. Remove 3rd active node  - Thread2
    #    Verify 2 replications run on 1st node and 1 replication on 2nd node
    # 5. Add 3rd node back - Thread2
    #    Verify 1 replications run on each node
    with ThreadPoolExecutor(max_workers=4) as tpe:
        update_from_cbl_task = tpe.submit(
            update_docs_until_sgwnode_update, db, cbl_db1
        )
        sg2.stop()
        sg1.admin.get_sgreplicate2_active_tasks(sg_db1)
        # TODO: Verify 2 replications run on 1st node and 1 replication on 2nd  node
        sg2.start(sg_config)
        sg1.admin.get_sgreplicate2_active_tasks(sg_db1)
        # TODO: Verify 3 replications run on each node
    
        db.create_bulk_docs(num_of_docs, "threadStop", db=cbl_db1, channels=channels1)
        num_iters = update_from_cbl_task.result()
        # drop_add_sgw_node_task.result()

    # 6. Verify all replications completed on passive node(sg4)
    cbl_doc_ids = db.getDocIds(cbl_db3)
    count1 = sum('Replication1_' in s for s in cbl_doc_ids)
    assert count1 == num_of_docs, "all docs created in cbl db1 did not replicate to cbl db3"
    cbl_docs = db.getDoucments(cbl_db3, cbl_doc_ids)
    for doc in cbl_docs:
        assert doc["updates-cbl"] == num_iters, "docs did not update successfully"
    replicator.wait_until_replicator_idle(repl1)
    replicator.wait_until_replicator_idle(repl2)
    replicator.wait_until_replicator_idle(repl4)
    replicator.stop(repl1)
    replicator.stop(repl2)
    replicator.stop(repl4)


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
@pytest.mark.parametrize("restart_nodes", [
    ("active"),
    ("passive")
])
def test_sg_replicate_restart_active_passive_nodes(params_from_base_test_setup, setup_customized_teardown_test, restart_nodes):
    '''
       @summary
       Covered for #69 and #70
       ""1. Have 4 sg nodes(2 active and 2 passive)
        2. Create docs in sg1(100 docs ?)
        3. Start 3 to 4 replications with push_pull and continuous
        4. updating docs while replication is happening 
        4. Restart active nodes/passive nodes
 "
    '''

    base_url = params_from_base_test_setup["base_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_mode = params_from_base_test_setup["mode"]
    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db2 = setup_customized_teardown_test["cbl_db2"]
    cbl_db3 = setup_customized_teardown_test["cbl_db3"]
    sg_conf_name = 'listener_tests/four_sync_gateways_with_2active_2passive'
    replicator = Replication(base_url)
    name4 = "autotest4"
    channels3 = ["Replication3"]
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)

    db, num_of_docs, sg_db1, sg_db2, name1, name2, password, channels1, channels2, replicator, _, replicator_authenticator2, _, sg2_blip_url, sg1, sg2, repl1, c_cluster = setup_syncGateways_with_cbl(params_from_base_test_setup, cbl_replication_type="push_pull", cbl_continuous=True, cbl_db1=cbl_db1)
    all_channels = channels1 + channels2 + channels3
    sg3 = c_cluster.sync_gateways[2]

    sg4, sg_db4, sg4_admin_url, sg4_blip_url = get_sg4(params_from_base_test_setup, c_cluster)
    replicator_authenticator4 = create_sguser_cbl_authenticator(base_url, sg4_admin_url, sg_db4, name4, password, channels1)

    #1. create docs on sg1 and sg2 using cbl_db1 and cbl_db2
    db.create_bulk_docs(num_of_docs, "Replication1", db=cbl_db1, channels=channels1)
    db.create_bulk_docs(num_of_docs, "Replication2", db=cbl_db2, channels=channels1)

    # Have replication from cbl_db2 to sg2
    repl2 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url, 
        replication_type="push_pull", continuous=True)

    repl4 = replicator.configure_and_replicate(
        source_db=cbl_db3, replicator_authenticator=replicator_authenticator4, target_url=sg4_blip_url, 
        replication_type="push_pull", continuous=True)

    # 2. start 3 replications
    sgw_repl_id = []
    repl_id_1 = sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg4.url,
        remote_db=sg_db4,
        remote_user=name4,
        remote_password=password,
        direction="push",
        channels=[channels1]
    )
    repl_id_2 = sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg4.url,
        remote_db=sg_db4,
        remote_user=name4,
        remote_password=password,
        direction="pull",
        continuous=True,
        channels=[channels1]
    )
    repl_id_3 = sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg4.url,
        remote_db=sg_db4,
        remote_user=name4,
        remote_password=password,
        direction="push",
        continuous=True,
        channels=[channels1]
    )

    # 3. update docs - Thread 1
    # 4. Remove 3rd active node  - Thread2
    #    Verify 2 replications run on 1st node and 1 replication on 2nd node
    # 5. Add 3rd node back - Thread2
    #    Verify 1 replications run on each node
    with ThreadPoolExecutor(max_workers=4) as tpe:
        update_from_cbl_task = tpe.submit(
            update_docs_until_sgwnode_update, db, cbl_db1
        )
        if restart_nodes == "active":
            restart_sg_nodes(sg1, sg2, sg_config, cluster_config)
        else:
            restart_sg_nodes(sg3, sg4, sg_config, cluster_config)
        db.create_bulk_docs(num_of_docs, "threadStop", db=cbl_db1, channels=channels1)
        num_iters = update_from_cbl_task.result()
        # drop_add_sgw_node_task.result()

    replicator.wait_until_replicator_idle(repl1)
    replicator.wait_until_replicator_idle(repl2)
    replicator.wait_until_replicator_idle(repl4)
    sg1.admin.wait_untl_sgw_replication_done(sg_db1, repl_id_1)
    sg1.admin.wait_untl_sgw_replication_done(sg_db1, repl_id_2)
    sg1.admin.wait_untl_sgw_replication_done(sg_db1, repl_id_3)
    # 6. Verify all replications completed on passive node(sg4)
    cbl_doc_ids = db.getDocIds(cbl_db3)
    count1 = sum('Replication1_' in s for s in cbl_doc_ids)
    assert count1 == num_of_docs, "all docs created in cbl db1 did not replicate to cbl db3"
    cbl_docs = db.getDoucments(cbl_db3, cbl_doc_ids)
    for doc in cbl_docs:
        assert doc["updates-cbl"] == num_iters, "docs did not update successfully"

    replicator.stop(repl1)
    replicator.stop(repl2)
    replicator.stop(repl4)


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
@pytest.mark.parametrize("conflict_resolver_type", [
    ("localWins"),
    ("remoteWins")
])
def test_sg_replicate_non_default_conflict_resolver(params_from_base_test_setup, setup_customized_teardown_test, conflict_resolver_type):
    '''
       @summary
       Covered for #67
       "Have multiple replications
        1. set up 2 sgw nodes
        2. Create docs on sg1 
        3. Start push_pull replication with  one shot with default conflict resolver
        4. update docs on sg2. 
        5. Then update docs on sg1 
        6. start push_pull replication with one shot with conflict resolution type = local_wins/remote_wins/lastWriteWins
        7. if  local_wins : docs updated on sg1 gets replicated to sg2
           if  remote_wins : docs updated on sg2 gets replicated to sg1
    '''

    # 1.set up 2 sgw nodes
    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db2 = setup_customized_teardown_test["cbl_db2"]

    db, num_of_docs, sg_db1, sg_db2, name1, name2, password, channels1, _, replicator, replicator_authenticator1, replicator_authenticator2, sg1_blip_url, sg2_blip_url, sg1, sg2, repl1, _ = setup_syncGateways_with_cbl(params_from_base_test_setup, cbl_replication_type="push", cbl_continuous=False, cbl_db1=cbl_db1)
    # 2. Create docs on sg1 
    db.create_bulk_docs(num_of_docs, "Replication1", db=cbl_db1, channels=channels1)

    # 3. Start push_pull replication with  one shot with default conflict resolver
    repl_id_1 = sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg2.url,
        remote_db=sg_db2,
        remote_user=name1,
        remote_password=password
    )
    sg1.wait_until_sgw_replication_done(db=sg_db1, repl_id=repl_id_1)
    replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url
    )
    # 4. update docs on sg2 via cbl_db2
    db.update_bulk_docs(cbl_db2, number_of_updates=3)
    
    # 5. Then update docs on sg1  via cbl_db1
    db.update_bulk_docs(cbl_db1)

    # 6. start push_pull replication with one shot with custom conflict resovler
    sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg2.url,
        remote_db=sg_db2,
        remote_user=name1,
        remote_password=password,
        conflict_resolution_type=conflict_resolver_type
    )
    
    #7. if  local_wins : docs updated on sg1 gets replicated to sg2
    # if  remote_wins : docs updated on sg2 gets replicated to sg1

    # 6. Verify docs created in cbl2
    cbl_doc_ids1 = db.getDocIds(cbl_db1)
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    if conflict_resolver_type == "localWins" or conflict_resolver_type == "lastWriteWins":
        for doc_id in cbl_doc_ids2:
            doc = db.getDocument(cbl_db2, doc_id)
            assert doc["updates-cbl"] == 1, "local_win replication did not happen"
    else:
        for doc_id in cbl_doc_ids1:
            doc = db.getDocument(cbl_db1, doc_id)
            assert doc["updates-cbl"] == 3, "remote_win replication did not happen"

@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
@pytest.mark.parametrize("custom_conflict_type", [
    ("merge"),
    # ("delaylocal")
])
def test_sg_replicate_custom_conflict_resolve(params_from_base_test_setup, setup_customized_teardown_test, custom_conflict_type):
    '''
       @summary
       Covered for #45
       "Have multiple replications
        1. "1. have js function in sgw config to merge local and remote changes on sg1 - on sg2?
        2. set up 2 sgw nodes
        3. Create docs on sg1 
        4. Start push_pull replication with one shot
        5. update docs on sg2.
        6. Then update docs on sg1
        7. Start push_pull replication with one shot
        8. verify that docs on sg1 and sg2 gets merged into one doc

        See PRD and specs for js function"
    '''

    # 1.set up 2 sgw nodes
    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db2 = setup_customized_teardown_test["cbl_db2"]
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_conf_name = 'listener_tests/sg_replicate_custom_conflict'

    db, num_of_docs, sg_db1, sg_db2, name1, name2, password, channels1, _, replicator, replicator_authenticator1, replicator_authenticator2, sg1_blip_url, sg2_blip_url, sg1, sg2, repl1, _ = setup_syncGateways_with_cbl(params_from_base_test_setup, cbl_replication_type="push", cbl_continuous=False, cbl_db1=cbl_db1)
    # 2. Create docs on sg1 
    db.create_bulk_docs(num_of_docs, "Replication1", db=cbl_db1, channels=channels1)

    # 3. Start push_pull replication with  one shot with default conflict resolver
    repl_id_1 = sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg2.url,
        remote_db=sg_db2,
        remote_user=name1,
        remote_password=password
    )
    sg1.admin.wait_until_sgw_replication_done(db=sg_db1, repl_id=repl_id_1)
    replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url
    )
    # 4. update docs on sg2 via cbl_db2
    # db.update_bulk_docs(cbl_db2, key="cbl2-update")
    
    # 5. Then update docs on sg1  via cbl_db1
    db.update_bulk_docs(cbl_db1, key="cbl1-update")

    # Add merge js function to sgw config
    repl_id = "replication1"
    custom_conflict_js_function = """function(local, remote) {
    if (local.body.priority > remote.body.priority) {
        return {
            body: local.body,
            meta: local.meta
        };
    } else if (local.body.priority < remote.body.priority) {
        return {
            body: remote.body,
            meta: remote.meta
        };
    }
    return defaultPolicy(local, remote);
}"""
    temp_sg_config = update_replication_in_sgw_config(sg_conf_name, sg_mode, repl_remote=sg2.url, repl_remote_db=sg_db2, repl_remote_user=name1, repl_remote_password=password, repl_repl_id=repl_id,
                                                      repl_direction="push_and_pull", repl_conflict_resolution_type="custom", repl_continuous=None, repl_filter_query_params=None, custom_conflict_js_function=custom_conflict_js_function)
    sg1.restart(config=temp_sg_config, cluster_config=cluster_config)
    # 6. start push_pull replication with one shot with custom conflict resovler
    """sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg2.url,
        remote_db=sg_db2,
        remote_user=name1,
        remote_password=password,
        conflict_resolution_type="custom"
    )"""
    sg1.admin.wait_until_sgw_replication_done(sg_db1, repl_id)
    #7. if  local_wins : docs updated on sg1 gets replicated to sg2
    # if  remote_wins : docs updated on sg2 gets replicated to sg1
    
    # 6. Verify docs created in cbl2
    # cbl_doc_ids1 = db.getDocIds(cbl_db1)
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    if custom_conflict_type == "merge":
        for doc_id in cbl_doc_ids2:
            doc1 = db.getDocument(cbl_db1, doc_id)
            doc2 = db.getDocument(cbl_db2, doc_id)
            assert doc1["cbl1-update"] == 1, "merge of local and remote doc did not replicated on cbl db1"
            assert doc1["cbl2-update"] == 1, "merge of local and remote doc did not replicated on cbl db1"
            assert doc2["cbl1-update"] == 1, "merge of local and remote doc did not replicated on cbl db2"
            assert doc2["cbl2-update"] == 1, "merge of local and remote doc did not replicated on cbl db2"
    elif custom_conflict_type == "local_delay":
        for doc_id in cbl_doc_ids2:
            doc = db.getDocument(cbl_db2, doc_id)
            count = 0
            while count < 5:
                try:
                    doc["cbl1-update"]
                    assert False, "there is no local win delay happened"
                except KeyError as ke:
                    log_info("get the local delay")
                time.sleep(1)
            assert doc["cbl1-update"] == 1, "local win doc did not replicate after the delay"


def update_replication_in_sgw_config(sg_conf_name, sg_mode, repl_remote, repl_remote_db, repl_remote_user, repl_remote_password, repl_repl_id, repl_direction="push_and_pull", repl_conflict_resolution_type="default", repl_continuous=None, repl_filter_query_params=None, custom_conflict_js_function=None):
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)
    temp_sg_config, _ = copy_sgconf_to_temp(sg_config, sg_mode)
    if "4984" in repl_remote:
        if repl_remote_user and repl_remote_password:
            print("adding some value")
            remote_url = repl_remote.replace("://", "://{}:{}@".format(repl_remote_user, repl_remote_password))
            remote_url = "{}/{}".format(remote_url, repl_remote_db)
        else:
            raise Exception("No remote node's username and password provided ")
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ repl_remote }}", "\"{}\"".format(remote_url))
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ repl_direction }}", "\"{}\"".format(repl_direction))
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ repl_conflict_resolution_type }}", "\"{}\"".format(repl_conflict_resolution_type))
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ repl_repl_id }}", "\"{}\"".format(repl_repl_id))
    if repl_continuous is not None:
        cont = "True"
        temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ repl_continuous }}", "{},".format(cont))
    else:
        temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ repl_continuous }}", "")
    if repl_filter_query_params is not None:
        temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ repl_filter_query_params }}", "\"{}\",".format(repl_filter_query_params))
    else:
        temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ repl_filter_query_params }}", "")
    if repl_conflict_resolution_type == "custom":
        custom_conflict_key = "custom_conflict_resolver"
        custom_conflict_key_value = "\"{}\":`{}`".format(custom_conflict_key, custom_conflict_js_function)
        temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ custom_conflict_js_function }}", "{},".format(custom_conflict_key_value))
    return temp_sg_config


def restart_sg_nodes(sg1, sg2, sg_config, cluster_config):
    sg1.restart(sg_config, cluster_config)
    sg2.restart(sg_config, cluster_config)


def update_docs_until_sgwnode_update(db, cbl_db):
    num_iters = 0
    count = 0
    max_count = 25
    db.update_all_docs_individually(database=cbl_db)
    while True and count < max_count:
        db.update_all_docs_individually(database=cbl_db)
        num_iters += 1
        cbl_doc_ids = db.getDocIds(cbl_db)
        if "threadStop" in cbl_doc_ids:
            break
        count += 1
    return num_iters


def setup_replications_on_sgconfig(remote_sg_url, remote_user, remote_password, direction="push_and_pull", channels=None, continuous=None):

    # replication = {}
    repl1 = {}
    replication_id = "sgw_repl_{}".format(random_string(length=10, digit=True))
    remote_sg_url = remote_sg_url.replace("://", "://{}:{}@".format(remote_user, remote_password))
    # remote_sg_url = "{}/{}".format(remote_sg_url)
    repl1["remote"] = "{}".format(remote_sg_url)
    repl1["direction"] = "pull"
    if continuous:
        repl1["continuous"] = "True"
    if channels is not None:
        repl1["filter"] = "sync_gateway/bychannel"
        repl1["query_params"] = channels
    # replication[replication_id] = repl1
    repl1_string = json.dumps(repl1)
    repl1_string = repl1_string.replace("\"True\"", "true")
    print("repl1_string is ", repl1_string)
    replication_string = "\"{}\": {}".format(replication_id, repl1_string)
    print("replication_string is ", replication_string)
    return replication_string, replication_id


def get_sg4(params_from_base_test_setup, c_cluster):
    sg_ssl = params_from_base_test_setup["sg_ssl"]
    sg_db4 = "sg_db4"
    sg4 = c_cluster.sync_gateways[3]
    sg4_ip = sg4.ip
    # channels3 = channels1 + channels2
    sg4_admin_url = sg4.admin.admin_url
    sg4_blip_url = "ws://{}:4984/{}".format(sg4_ip, sg_db4)
    if sg_ssl:
        sg4_blip_url = "wss://{}:4984/{}".format(sg4_ip, sg_db4)

    return sg4, sg_db4, sg4_admin_url, sg4_blip_url


def create_sguser_cbl_authenticator(base_url, sg_admin_url, sg_db, name, password, channels):
    sg_client = MobileRestClient()
    authenticator = Authenticator(base_url)
    sg_client.create_user(sg_admin_url, sg_db, name, password=password, channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, name)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    return replicator_authenticator
