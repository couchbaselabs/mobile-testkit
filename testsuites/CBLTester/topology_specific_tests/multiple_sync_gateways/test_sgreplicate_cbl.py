
import pytest
import time
import os
import random
import subprocess


from keywords.MobileRestClient import MobileRestClient
from CBLClient.Database import Database
from CBLClient.Document import Document
from CBLClient.Replication import Replication
from CBLClient.Authenticator import Authenticator
from keywords.SyncGateway import sync_gateway_config_path_for_mode, SyncGateway, setup_replications_on_sgconfig, update_replication_in_sgw_config
from libraries.testkit import cluster
from libraries.testkit.admin import Admin
from requests.exceptions import HTTPError
from keywords.utils import host_for_url, log_info, compare_cbl_docs
from keywords import attachment, document
from concurrent.futures import ThreadPoolExecutor
from utilities.cluster_config_utils import copy_sgconf_to_temp, replace_string_on_sgw_config
from keywords.ClusterKeywords import ClusterKeywords
from keywords.couchbaseserver import get_sdk_client_with_bucket
from libraries.testkit.prometheus import verify_stat_on_prometheus


def setup_syncGateways_with_cbl(params_from_base_test_setup, setup_customized_teardown_test, cbl_replication_type, sg_conf_name='listener_tests/multiple_sync_gateways', num_of_docs=10, channels1=None, sgw_cluster1_sg_config_name=None, sgw_cluster2_sg_config_name=None, name1=None, name2=None, password1=None, password2=None):

    cluster_config = params_from_base_test_setup["cluster_config"]
    base_url = params_from_base_test_setup["base_url"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    sg_ssl = params_from_base_test_setup["sg_ssl"]
    sg_mode = params_from_base_test_setup["mode"]
    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db2 = setup_customized_teardown_test["cbl_db2"]
    sg_db1 = "sg_db1"
    sg_db2 = "sg_db2"
    protocol = "ws"
    sgwgateway = SyncGateway()

    channels2 = ["Replication2"]
    if name1 is None:
        name1 = "autotest1"
    if name2 is None:
        name2 = "auto_test@"
    if password1 is None:
        password1 = "password"
    if password2 is None:
        password2 = "password"
    if channels1 is None:
        channels1 = ["Replication1"]

    sg_client = MobileRestClient()
    if sync_gateway_version < "2.8.0":
        pytest.skip('It does not work with sg < 2.8.0 and cannot work with self signed, so skipping the test')

    c_cluster = cluster.Cluster(config=cluster_config)
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)
    c_cluster.reset(sg_config_path=sg_config)
    db = Database(base_url)

    sg1 = c_cluster.sync_gateways[0]
    sg2 = c_cluster.sync_gateways[1]
    sg3 = c_cluster.sync_gateways[2]
    sg4 = c_cluster.sync_gateways[3]

    sg3.stop()
    sg4.stop()
    if sgw_cluster1_sg_config_name:
        sgw_cluster1_sg_config = sync_gateway_config_path_for_mode(sgw_cluster1_sg_config_name, sg_mode)
        sgw_cluster1_config_path = "{}/{}".format(os.getcwd(), sgw_cluster1_sg_config)

        sgwgateway.redeploy_sync_gateway_config(cluster_config=cluster_config, sg_conf=sgw_cluster1_config_path, url=sg1.ip,
                                                sync_gateway_version=sync_gateway_version, enable_import=True)

    if sgw_cluster2_sg_config_name:
        sgw_cluster2_sg_config = sync_gateway_config_path_for_mode(sgw_cluster2_sg_config_name, sg_mode)
        sgw_cluster2_config_path = "{}/{}".format(os.getcwd(), sgw_cluster2_sg_config)
        sgwgateway.redeploy_sync_gateway_config(cluster_config=cluster_config, sg_conf=sgw_cluster2_config_path, url=sg2.ip,
                                                sync_gateway_version=sync_gateway_version, enable_import=True)

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

    sg_client.create_user(sg1_admin_url, sg_db1, name1, password=password1, channels=channels1)
    sg_client.create_user(sg2_admin_url, sg_db2, name2, password=password2, channels=channels1)
    # Create bulk doc json

    # 2. Create replication authenticator
    replicator = Replication(base_url)
    cookie, session_id = sg_client.create_session(sg1_admin_url, sg_db1, name1)
    session1 = cookie, session_id
    authenticator = Authenticator(base_url)
    replicator_authenticator1 = authenticator.authentication(session_id, cookie, authentication_type="session")

    cookie2, session_id2 = sg_client.create_session(sg2_admin_url, sg_db2, name2)
    replicator_authenticator2 = authenticator.authentication(session_id2, cookie2, authentication_type="session")

    # Do push replication to from cbl1 to sg1 cbl -> sg1
    repl1 = replicator.configure_and_replicate(
        source_db=cbl_db1, replicator_authenticator=replicator_authenticator1, target_url=sg1_blip_url, replication_type="push_pull", continuous=True)
    return db, num_of_docs, sg_db1, sg_db2, name1, name2, password1, password2, channels1, channels2, replicator, replicator_authenticator1, replicator_authenticator2, sg1_blip_url, sg2_blip_url, sg1, sg2, repl1, c_cluster, cbl_db1, cbl_db2, session1


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
@pytest.mark.parametrize("continuous, direction, attachments", [
    (True, "push", False),
    (False, "pull", False),
    (False, "pushAndPull", False),
    (True, "push", True),
    (False, "pull", True),
    pytest.param(True, "pushAndPull", True, marks=pytest.mark.sanity),
])
def test_sg_replicate_push_pull_replication(params_from_base_test_setup, setup_customized_teardown_test, continuous, direction, attachments):
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
    sgw_cluster1_conf_name = 'listener_tests/sg_replicate_sgw_cluster1'
    sgw_cluster2_conf_name = 'listener_tests/sg_replicate_sgw_cluster2'
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    write_flag = False
    read_flag = False
    sg_client = MobileRestClient()
    prometheus_enable = params_from_base_test_setup["prometheus_enable"]

    db, num_of_docs, sg_db1, sg_db2, name1, name2, _, password, channels1, _, replicator, replicator_authenticator1, replicator_authenticator2, sg1_blip_url, sg2_blip_url, sg1, sg2, repl1, _, cbl_db1, cbl_db2, _ = setup_syncGateways_with_cbl(params_from_base_test_setup, setup_customized_teardown_test,
                                                                                                                                                                                                                                                  cbl_replication_type="push", sgw_cluster1_sg_config_name=sgw_cluster1_conf_name,
                                                                                                                                                                                                                                                  sgw_cluster2_sg_config_name=sgw_cluster2_conf_name)

    # Get expvars before test starts
    expvars = sg_client.get_expvars(url=sg1.admin.admin_url)
    # 2. Add docs in cbl1
    if attachments:
        db.create_bulk_docs(num_of_docs, "sgw1_docs", db=cbl_db1, channels=channels1, attachments_generator=attachment.generate_png_100_100)
        db.create_bulk_docs(num_of_docs, "sgw2_docs", db=cbl_db2, channels=channels1, attachments_generator=attachment.generate_png_100_100)
    else:
        db.create_bulk_docs(num_of_docs, "sgw1_docs", db=cbl_db1, channels=channels1)
        db.create_bulk_docs(num_of_docs, "sgw2_docs", db=cbl_db2, channels=channels1)
    repl2 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url)

    replicator.wait_until_replicator_idle(repl1)
    replicator.wait_until_replicator_idle(repl2)

    if "push" in direction:
        write_flag = True
    if "pull" in direction:
        read_flag = True

    repl_id_1 = sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg2.url,
        remote_db=sg_db2,
        remote_user=name2,
        remote_password=password,
        direction=direction,
        continuous=continuous
    )
    expected_tasks = 1
    if not continuous:
        expected_tasks = 0
    active_tasks = sg1.admin.get_sgreplicate2_active_tasks(sg_db1, expected_tasks=expected_tasks)
    sg1.admin.wait_until_sgw_replication_done(sg_db1, repl_id_1, read_flag=read_flag, write_flag=write_flag)
    assert len(active_tasks) == expected_tasks, "number of active tasks is not 1"
    if continuous:
        active_task = active_tasks[0]
        created_replication_id = active_task["replication_id"]
        sg1.stop_replication2_by_id(created_replication_id, sg_db1)

    expected_tasks = 0
    active_tasks = sg1.admin.get_sgreplicate2_active_tasks(sg_db1, expected_tasks=expected_tasks)
    assert len(active_tasks) == expected_tasks, "replication with continous or one shot is not stopped"
    replicator.wait_until_replicator_idle(repl1)
    replicator.wait_until_replicator_idle(repl2)
    # 6. Verify docs created in cbl2
    if "push" in direction:
        cbl_doc_ids2 = db.getDocIds(cbl_db2)
        cbl_db_docs = db.getDocuments(cbl_db2, cbl_doc_ids2)
        count1 = sum('sgw1_docs_' in s for s in cbl_doc_ids2)
        assert count1 == num_of_docs, "all docs do not replicate to cbl db2"
        if attachments:
            for doc_id in cbl_doc_ids2:
                if 'sgw1_docs_' in doc_id:
                    assert "_attachments" in cbl_db_docs[doc_id], "attachment did not updated on cbl_db2"
    if "pull" in direction:
        cbl_doc_ids1 = db.getDocIds(cbl_db1)
        cbl_db_docs = db.getDocuments(cbl_db1, cbl_doc_ids1)
        count2 = sum('sgw2_docs_' in s for s in cbl_doc_ids1)
        assert count2 == num_of_docs, "all docs do not replicate to cbl db1"
        if attachments:
            for doc_id in cbl_doc_ids1:
                if 'sgw2_docs_' in doc_id:
                    assert "_attachments" in cbl_db_docs[doc_id], "attachment did not updated on cbl_db1"

    # Get expvars after test completed
    expvars = sg_client.get_expvars(url=sg1.admin.admin_url)
    if attachments:
        if "push" in direction:
            assert expvars['syncgateway']['per_db'][sg_db1]['replications'][repl_id_1]['sgr_num_attachment_bytes_pushed'] > 0, "push replication bytes is not incrementedd"
            assert expvars['syncgateway']['per_db'][sg_db1]['replications'][repl_id_1]['sgr_num_attachments_pushed'] == num_of_docs, "push replication count is  not  equal to number of docs pushed"
        if "pull" in direction:
            assert expvars['syncgateway']['per_db'][sg_db1]['replications'][repl_id_1]['sgr_num_attachment_bytes_pulled'] > 0, "pull replication bytes is not incremented"
            assert expvars['syncgateway']['per_db'][sg_db1]['replications'][repl_id_1]['sgr_num_attachments_pulled'] == num_of_docs, "pull replication count is  not  equal to number of docs pulled"
    if "push" in direction:
        assert expvars['syncgateway']['per_db'][sg_db1]['replications'][repl_id_1]['sgr_num_docs_pushed'] == num_of_docs, "push replication count is  not  equal to number of docs pushed"
        if prometheus_enable and sync_gateway_version >= "2.8.0":
            assert verify_stat_on_prometheus("sgw_replication_sgr_num_docs_pushed"), expvars['syncgateway']['per_db'][sg_db1]['replications'][repl_id_1]['sgr_num_docs_pushed']
    if "pull" in direction:
        assert expvars['syncgateway']['per_db'][sg_db1]['replications'][repl_id_1]['sgr_num_docs_pulled'] == num_of_docs, "pull replication count is  not  equal to number of docs pulled"
        if prometheus_enable and sync_gateway_version >= "2.8.0":
            assert verify_stat_on_prometheus("sgw_replication_sgr_num_docs_pulled"), expvars['syncgateway']['per_db'][sg_db1]['replications'][repl_id_1]['sgr_num_docs_pulled']


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
def test_sg_replicate_replication_with_deltasync(params_from_base_test_setup, setup_customized_teardown_test):
    '''
       @summary
       1.Have 2 sgw nodes , have cbl on each SGW
       2. Add docs in cbl1
       3. Do push replication to from cbl1 to sg1 cbl -> sg1
       4. push_pull replication from sg1 -> sg2
       5. Do pull replication from sg2 -> cbl2
       6. Create more docs in cbl1(sg1)
       7. Verify only delta of the docs replicated to sg2(cbl2)
       8. Verify expvars to make sure only delta of docs is replicated
    '''

    # 1.Have 2 sgw nodes , have cbl on each SGW
    sgw_cluster1_conf_name = 'listener_tests/sg_replicate_sgw_cluster1'
    sgw_cluster2_conf_name = 'listener_tests/sg_replicate_sgw_cluster2'
    replication1 = "SGW1_docs"
    continuous = True
    delta_sync = True
    direction = "pushAndPull"

    db, num_of_docs, sg_db1, sg_db2, _, name2, _, password, channels1, _, replicator, _, replicator_authenticator2, sg1_blip_url, sg2_blip_url, sg1, sg2, repl1, _, cbl_db1, cbl_db2, _ = setup_syncGateways_with_cbl(params_from_base_test_setup, setup_customized_teardown_test,
                                                                                                                                                                                                                      cbl_replication_type="push", sgw_cluster1_sg_config_name=sgw_cluster1_conf_name,
                                                                                                                                                                                                                      sgw_cluster2_sg_config_name=sgw_cluster2_conf_name)

    # 2. Add docs in cbl1
    db.create_bulk_docs(num_of_docs, replication1, db=cbl_db1, channels=channels1)
    repl2 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url)

    replicator.wait_until_replicator_idle(repl1)

    repl_id_1 = sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg2.url,
        remote_db=sg_db2,
        remote_user=name2,
        remote_password=password,
        direction=direction,
        continuous=continuous,
        delta_sync=delta_sync
    )
    sg1.admin.wait_until_sgw_replication_done(sg_db1, repl_id_1, write_flag=True)
    replicator.wait_until_replicator_idle(repl2)
    # 6. update docs on sg1 via cbl_db1
    db.update_bulk_docs(cbl_db1)
    replicator.wait_until_replicator_idle(repl2)
    #  7. Verify only delta of the docs replicated to sg2(cbl2)
    sg1.admin.wait_until_sgw_replication_done(sg_db1, repl_id_1, write_flag=True)
    replicator.wait_until_replicator_idle(repl2)
    # 8. Verify docs created in cbl2
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    count = sum(replication1 in s for s in cbl_doc_ids2)
    assert count == num_of_docs, "docs did not replicated to cbl2 "

    replicator.stop(repl1)
    replicator.stop(repl2)


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
@pytest.mark.parametrize("invalid_password, invalid_db", [
    (True, False),
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
    sgw_cluster1_conf_name = 'listener_tests/sg_replicate_sgw_cluster1'
    sgw_cluster2_conf_name = 'listener_tests/sg_replicate_sgw_cluster2'
    wrong_password = "invalid_password"
    wrong_db = "wrong_db"

    db, num_of_docs, sg_db1, sg_db2, _, name2, _, password, channels1, _, _, _, _, _, _, sg1, sg2, _, _, cbl_db1, _, _ = setup_syncGateways_with_cbl(params_from_base_test_setup, setup_customized_teardown_test, cbl_replication_type="push",
                                                                                                                                                     sgw_cluster1_sg_config_name=sgw_cluster1_conf_name,
                                                                                                                                                     sgw_cluster2_sg_config_name=sgw_cluster2_conf_name)
    # 2. Add docs in cbl1
    db.create_bulk_docs(num_of_docs, "Replication1", db=cbl_db1, channels=channels1)

    # 3. pull replication from sg1 -> sg2
    try:
        if invalid_password:
            sg1.start_replication2(
                local_db=sg_db1,
                remote_url=sg2.url,
                remote_db=sg_db2,
                remote_user=name2,
                remote_password=wrong_password,
                direction="push",
                continuous=True
            )
        if invalid_db:
            sg1.start_replication2(
                local_db=sg_db1,
                remote_url=sg2.url,
                remote_db=wrong_db,
                remote_user=name2,
                remote_password=password,
                direction="push",
                continuous=True
            )
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
    sgw_cluster1_conf_name = 'listener_tests/sg_replicate_sgw_cluster1'
    sgw_cluster2_conf_name = 'listener_tests/sg_replicate_sgw_cluster2'
    password2 = "p@ss:ord2"

    db, num_of_docs, sg_db1, sg_db2, _, name2, _, password, channels1, _, replicator, replicator_authenticator1, replicator_authenticator2, sg1_blip_url, sg2_blip_url, sg1, sg2, repl1, _, cbl_db1, cbl_db2, _ = setup_syncGateways_with_cbl(params_from_base_test_setup,
                                                                                                                                                                                                                                              setup_customized_teardown_test, cbl_replication_type="push", sgw_cluster1_sg_config_name=sgw_cluster1_conf_name,
                                                                                                                                                                                                                                              sgw_cluster2_sg_config_name=sgw_cluster2_conf_name, password2=password2)
    # 2. Add docs in cbl1
    db.create_bulk_docs(num_of_docs, "Replication1", db=cbl_db1, channels=channels1)

    # 4. push replication with customized replication id from sg1 -> sg2
    repl_id = sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg2.url,
        remote_db=sg_db2,
        remote_user=name2,
        remote_password=password,
        direction="push",
        continuous=True
    )
    active_tasks = sg1.admin.get_sgreplicate2_active_tasks(sg_db1)
    sg1.admin.wait_until_sgw_replication_done(sg_db1, repl_id, write_flag=True)
    created_replication_id = active_tasks[0]["replication_id"]
    # 5. Verify replication id is created
    assert repl_id == created_replication_id, "custom replication id not created"
    sg1.stop_replication2_by_id(repl_id, sg_db1)
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
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    count = sum('Replication2_' in s for s in cbl_doc_ids2)
    assert count == 0, "docs replicated to cbl2 though replication is cancelled"
    replicator.stop(repl1)
    replicator.stop(repl2)


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
def test_sg_replicate_upsert_replication(params_from_base_test_setup, setup_customized_teardown_test):
    '''
       @summary
       1.Have 2 sgw nodes , have cbl on each SGW
       2. Add docs in cbl1 and cbl2
       3. Do push replication to from cbl1 to sg1 cbl -> sg1
       4. push and Pull replication with customized replication id from sg1 -> sg2
       5. Verify docs pushed to  cbl2 , but docs created on cbl1 not pulled to cbl1
       6. update the replication from push to pushAndPulll
       7. Create docs on CBL DB1 and CBL DB2
       8. Verify docs replicated to CBL1 which created on CBL2
           Verify docs replicated  to  CBL2 which created on CBL1
    '''

    # 1.Have 2 sgw nodes , have cbl on each SGW
    sgw_cluster1_conf_name = 'listener_tests/sg_replicate_sgw_cluster1'
    sgw_cluster2_conf_name = 'listener_tests/sg_replicate_sgw_cluster2'
    replication1 = "Replication1"
    replication2 = "Replication2"
    replication3 = "Replication3"
    replication4 = "Replication4"
    password2 = "pass /word"

    db, num_of_docs, sg_db1, sg_db2, _, name2, _, password, channels1, _, replicator, replicator_authenticator1, replicator_authenticator2, sg1_blip_url, sg2_blip_url, sg1, sg2, repl1, _, cbl_db1, cbl_db2, _ = setup_syncGateways_with_cbl(params_from_base_test_setup,
                                                                                                                                                                                                                                              setup_customized_teardown_test, cbl_replication_type="push", sgw_cluster1_sg_config_name=sgw_cluster1_conf_name, sgw_cluster2_sg_config_name=sgw_cluster2_conf_name, password2=password2)
    # 2. Add docs in cbl1 and cbl2
    db.create_bulk_docs(num_of_docs, replication1, db=cbl_db1, channels=channels1)
    db.create_bulk_docs(num_of_docs, replication2, db=cbl_db2, channels=channels1)
    # 3. Do push pull replication to from cbl2 to sg2 cbl2 <-> sg1
    repl2 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url)
    replicator.wait_until_replicator_idle(repl1)
    replicator.wait_until_replicator_idle(repl2)
    # 3. push replication with customized replication id from sg1 -> sg2
    repl_id = sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg2.url,
        remote_db=sg_db2,
        remote_user=name2,
        remote_password=password,
        direction="pushAndPull",
        continuous=True,
        user_credentials_url=False
    )
    sg1.admin.wait_until_sgw_replication_done(sg_db1, repl_id, read_flag=True, write_flag=True)
    replicator.wait_until_replicator_idle(repl1)
    replicator.wait_until_replicator_idle(repl2)

    # 5. Verify docs pushed to  cbl2 , but docs created on cbl1 not pulled to cbl1
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    count = sum(replication1 in s for s in cbl_doc_ids2)
    assert count == num_of_docs, "all docs do not replicate to cbl db2"
    cbl_doc_ids1 = db.getDocIds(cbl_db1)
    count = sum(replication2 in s for s in cbl_doc_ids1)
    assert count == num_of_docs, "docs created on cbl db1 did not replicate to cbl db2"

    # 6. update/upsert the SGW replication from push to pushAndPulll
    try:
        sg1.start_replication2(
            local_db=sg_db1,
            remote_url=sg2.url,
            remote_db=sg_db2,
            remote_user=name2,
            remote_password=password,
            direction="push",
            continuous=True,
            replication_id=repl_id,
            user_credentials_url=False
        )
        assert False, "Did not get Http error while upserting the replication without stopping"
    except HTTPError:
        assert True, "Got expected Http error"

    # Stop replication and upsert the replication
    sg1.stop_replication2_by_id(repl_id, sg_db1)
    sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg2.url,
        remote_db=sg_db2,
        remote_user=name2,
        remote_password=password,
        direction="push",
        continuous=True,
        replication_id=repl_id,
        user_credentials_url=False
    )

    # 7. Create docs on CBL DB1 and CBL DB2
    db.create_bulk_docs(num_of_docs, replication3, db=cbl_db1, channels=channels1)
    db.create_bulk_docs(num_of_docs, replication4, db=cbl_db2, channels=channels1)
    sg1.admin.wait_until_sgw_replication_done(sg_db1, repl_id, write_flag=True)
    replicator.wait_until_replicator_idle(repl1)
    replicator.wait_until_replicator_idle(repl2)

    # 8. Verify docs replicated to CBL1 which created on CBL2
    #    and Verify docs replicated  to  CBL2 which created on CBL1
    cbl_doc_ids1 = db.getDocIds(cbl_db1)
    count = sum(replication4 in s for s in cbl_doc_ids1)
    assert count == 0, "upsert replication did not effect and replication still happened to cbl1"
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    count = sum(replication3 in s for s in cbl_doc_ids2)
    assert count == num_of_docs, "docs did replicated to cbl2"
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
    cluster_config = params_from_base_test_setup["cluster_config"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    sg_mode = params_from_base_test_setup["mode"]
    # 1.Have 2 sgw nodes , have cbl on each SGW
    cbl_db3 = setup_customized_teardown_test["cbl_db3"]
    continuous = True
    sg_conf_name = 'listener_tests/three_sync_gateways'
    sgw_cluster1_conf_name = 'listener_tests/sg_replicate_sgw_cluster1'
    sgw_cluster2_conf_name = 'listener_tests/sg_replicate_sgw_cluster2'
    sgw_cluster2_bucket_3 = 'listener_tests/sg_replicate_sgw_cluster_databucket_3'
    sg_db3 = "sg_db3"
    name3 = "autotest3"
    sg_client = MobileRestClient()
    sgwgateway = SyncGateway()

    db, num_of_docs, sg_db1, sg_db2, _, name2, password1, password2, channels1, _, replicator, _, replicator_authenticator2, _, sg2_blip_url, sg1, sg2, repl1, c_cluster, cbl_db1, cbl_db2, _ = setup_syncGateways_with_cbl(params_from_base_test_setup, setup_customized_teardown_test,
                                                                                                                                                                                                                            cbl_replication_type="push_pull",
                                                                                                                                                                                                                            sg_conf_name=sg_conf_name, sgw_cluster1_sg_config_name=sgw_cluster1_conf_name,
                                                                                                                                                                                                                            sgw_cluster2_sg_config_name=sgw_cluster2_conf_name)
    sg3 = c_cluster.sync_gateways[2]
    sgw_cluster1_sg_config = sync_gateway_config_path_for_mode(sgw_cluster2_bucket_3, sg_mode)
    sgw_cluster1_config_path = "{}/{}".format(os.getcwd(), sgw_cluster1_sg_config)
    sgwgateway.redeploy_sync_gateway_config(cluster_config=cluster_config, sg_conf=sgw_cluster1_config_path, url=sg3.ip,
                                            sync_gateway_version=sync_gateway_version, enable_import=True)
    db.create_bulk_docs(num_of_docs, "Replication1", db=cbl_db1, channels=channels1)
    authenticator = Authenticator(base_url)

    sg3_admin_url = sg3.admin.admin_url
    sg3_blip_url = "ws://{}:4984/{}".format(sg3.ip, sg_db3)
    if sg_ssl:
        sg3_blip_url = "wss://{}:4984/{}".format(sg3.ip, sg_db3)
    sg_client.create_user(sg3_admin_url, sg_db3, name3, password=password1, channels=channels1)
    cookie, session_id = sg_client.create_session(sg3_admin_url, sg_db3, name3)
    replicator_authenticator3 = authenticator.authentication(session_id, cookie, authentication_type="session")

    repl2 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url, continuous=True)

    repl3 = replicator.configure_and_replicate(
        source_db=cbl_db3, replicator_authenticator=replicator_authenticator3, target_url=sg3_blip_url, continuous=True)

    # 3. start replication on sg1 push_pull from sg1<->sg2 with db1 pointing to bucket1
    sgw_replid_1 = sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg2.url,
        remote_db=sg_db2,
        remote_user=name2,
        remote_password=password2,
        direction="pushAndPull",
        continuous=continuous
    )
    sg1.admin.wait_until_sgw_replication_done(sg_db1, sgw_replid_1, write_flag=True)

    # 4. start replication on sg1 push_pull from sg1<->sg3 with db2 pointing to bucket2
    sgw_replid_2 = sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg3.url,
        remote_db=sg_db3,
        remote_user=name3,
        remote_password=password2,
        direction="pushAndPull",
        continuous=continuous
    )
    # 5. Verify docs created sg1 gets replicated to sg2 and sg3
    sg1.admin.wait_until_sgw_replication_done(sg_db1, sgw_replid_2, write_flag=True)

    # 6. Verify docs created in cbl2 and cbl3
    replicator.wait_until_replicator_idle(repl3)
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    count1 = sum('Replication1_' in s for s in cbl_doc_ids2)
    assert count1 == num_of_docs, "all docs do not replicate to cbl db2"
    cbl_doc_ids3 = db.getDocIds(cbl_db3)
    count2 = sum('Replication1_' in s for s in cbl_doc_ids3)
    assert count2 == num_of_docs, "all docs do not replicate to cbl db3"

    # 6. Created docs in cbl3
    db.create_bulk_docs(num_of_docs, "Replication3", db=cbl_db3, channels=channels1)
    cbl_doc_ids3 = db.getDocIds(cbl_db3)

    # 7. Verify New docs created in sg3 shoulid get replicated to sg1 and sg2 as it is push_pull
    replicator.wait_until_replicator_idle(repl3)
    sg1.admin.wait_until_sgw_replication_done(sg_db1, sgw_replid_1, read_flag=True)
    sg1.admin.wait_until_sgw_replication_done(sg_db1, sgw_replid_2, read_flag=True)
    replicator.wait_until_replicator_idle(repl2)
    replicator.wait_until_replicator_idle(repl1)
    cbl_doc_ids1 = db.getDocIds(cbl_db1)
    count1 = sum('Replication3_' in s for s in cbl_doc_ids1)
    assert count1 == num_of_docs, "all docs created in cbl db3 did not replicate to cbl db1"

    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    count1 = sum('Replication3_' in s for s in cbl_doc_ids2)
    assert count1 == num_of_docs, "all docs created in cbl db3 did not replicate to cbl db2"

    replicator.stop(repl1)
    replicator.stop(repl2)
    replicator.stop(repl3)


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
def test_sg_replicate_2active_1passive(params_from_base_test_setup, setup_customized_teardown_test):
    '''
       @summary
       1. Have 3 sgw nodes and have 3 cbl db:
       2. Create docs in cbd db2 and cbl db3.
       3. Start push_pull, continuous replicaation cbl_db2 <-> sg2, cbl_db3 <-> sg3
          Have sg2 as passive cluster, sg1 and sg3 are active clusters
       4. start replication on sg1 push_pull from sg1<->sg2 with db1 pointing to bucket1
       5. start replication on sg3 push_pull from sg2<->sg2 with db2 pointing to bucket2
       6. Wait until replication completed on sg1, cbl_db2, cbl_db3 and cbl_db1
       7. Verify all docs replicated to sg1 and cbl_db1


    '''
    sg_ssl = params_from_base_test_setup["sg_ssl"]
    base_url = params_from_base_test_setup["base_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    sg_mode = params_from_base_test_setup["mode"]

    cbl_db3 = setup_customized_teardown_test["cbl_db3"]
    continuous = True
    sg_conf_name = 'listener_tests/three_sync_gateways'
    sgw_cluster1_conf_name = 'listener_tests/sg_replicate_sgw_cluster1'
    sgw_cluster2_conf_name = 'listener_tests/sg_replicate_sgw_cluster2'
    sgw_cluster2_bucket_3 = 'listener_tests/sg_replicate_sgw_cluster_databucket_3'
    sg_db3 = "sg_db3"
    name3 = "autotest3"
    sg_client = MobileRestClient()
    sgwgateway = SyncGateway()

    # 1. Have 3 sgw nodes and have 3 cbl db
    db, num_of_docs, sg_db1, sg_db2, name1, name2, password1, password2, channels1, _, replicator, _, replicator_authenticator2, _, sg2_blip_url, sg1, sg2, repl1, c_cluster, cbl_db1, cbl_db2, _ = setup_syncGateways_with_cbl(params_from_base_test_setup, setup_customized_teardown_test, cbl_replication_type="push_pull", sg_conf_name=sg_conf_name, sgw_cluster1_sg_config_name=sgw_cluster1_conf_name,
                                                                                                                                                                                                                                sgw_cluster2_sg_config_name=sgw_cluster2_conf_name)
    sg3 = c_cluster.sync_gateways[2]
    sgw_cluster1_sg_config = sync_gateway_config_path_for_mode(sgw_cluster2_bucket_3, sg_mode)
    sgw_cluster1_config_path = "{}/{}".format(os.getcwd(), sgw_cluster1_sg_config)
    sgwgateway.redeploy_sync_gateway_config(cluster_config=cluster_config, sg_conf=sgw_cluster1_config_path, url=sg3.ip,
                                            sync_gateway_version=sync_gateway_version, enable_import=True)
    authenticator = Authenticator(base_url)

    sg3_blip_url = "ws://{}:4984/{}".format(sg3.ip, sg_db3)
    if sg_ssl:
        sg3_blip_url = "wss://{}:4984/{}".format(sg3.ip, sg_db3)
    sg_client.create_user(sg3.admin.admin_url, sg_db3, name3, password=password1, channels=channels1)
    cookie, session_id = sg_client.create_session(sg3.admin.admin_url, sg_db3, name3)
    replicator_authenticator3 = authenticator.authentication(session_id, cookie, authentication_type="session")

    # 2. Create docs in cbd db1 and cbl db3.
    db.create_bulk_docs(num_of_docs, "Replication2", db=cbl_db1, channels=channels1)
    db.create_bulk_docs(num_of_docs, "Replication3", db=cbl_db3, channels=channels1)
    # 3. Start push_pull, continuous replicaation cbl_db2 <-> sg2, cbl_db3 <-> sg3
    repl2 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url,
        replication_type="push_pull", continuous=True)

    repl3 = replicator.configure_and_replicate(
        source_db=cbl_db3, replicator_authenticator=replicator_authenticator3, target_url=sg3_blip_url,
        replication_type="push_pull", continuous=True)

    # 4. start replication on sg1 push_pull from sg1<->sg3
    sgw_replid_1 = sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg3.url,
        remote_db=sg_db3,
        remote_user=name3,
        remote_password=password1,
        direction="pushAndPull",
        continuous=continuous
    )

    # 4. start replication on sg2 push_pull from sg2<->sg3
    sgw_replid_2 = sg2.start_replication2(
        local_db=sg_db2,
        remote_url=sg3.url,
        remote_db=sg_db3,
        remote_user=name3,
        remote_password=password1,
        direction="pushAndPull",
        continuous=continuous
    )

    # 6. Wait until replication completed on sg1, cbl_db2, cbl_db3 and cbl_db1
    sg1.admin.wait_until_sgw_replication_done(sg_db1, sgw_replid_1, write_flag=True)
    sg2.admin.wait_until_sgw_replication_done(sg_db2, sgw_replid_2, write_flag=True)
    replicator.wait_until_replicator_idle(repl1)
    replicator.wait_until_replicator_idle(repl2)
    replicator.wait_until_replicator_idle(repl3)
    cbl_doc_ids3 = db.getDocIds(cbl_db3)
    count1 = sum('Replication2_' in s for s in cbl_doc_ids3)
    assert count1 == num_of_docs, "all docs do not replicate from cbl db1 to cbl db2"

    count1 = sum('Replication3_' in s for s in cbl_doc_ids3)
    assert count1 == num_of_docs, "all docs do not replicate from cbl db1 from cbl db3"

    replicator.stop(repl1)
    replicator.stop(repl2)
    replicator.stop(repl3)


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
def test_sg_replicate_channel_filtering_with_attachments(params_from_base_test_setup, setup_customized_teardown_test):
    '''
       @summary
       Covered # 38, # 52
       1. Set up 2 sgw nodes and have two cbl dbs
       2. Create docs with attachments on cbl-db1 and have push_pull, continous replication with sg1
            each with 2 differrent channel, few docs on both channels
       3 . Start sg-replicate from sg1 to sg2 with channel1 with one shot
       4. verify docs with channel which is filtered in replication should get replicated
       5. Verify docs with channel2 is not accessed by user 2 i.e cbl db2
    '''

    # 1.Have 2 sgw nodes , have cbl on each SGW
    base_url = params_from_base_test_setup["base_url"]
    sgw_cluster1_conf_name = 'listener_tests/sg_replicate_sgw_cluster1'
    sgw_cluster2_conf_name = 'listener_tests/sg_replicate_sgw_cluster2'
    file_attachment = "sample_text.txt"
    continuous = True
    channel1_docs = 5
    channel2_docs = 7
    channel3_docs = 8
    name3 = "autotest3"
    name4 = "autotest4"
    sg_client = MobileRestClient()
    authenticator = Authenticator(base_url)
    Replication1_channel1 = "cur3_Replication1_channel1"
    Replication1_channel2 = "cur3_Replication1_channel2"
    Replication1_channel3 = "cur3_Replication1_channel3"

    # 1. Set up 2 sgw nodes and have two cbl dbs
    db, num_of_docs, sg_db1, sg_db2, name1, name2, password1, password2, channels1, channels2, replicator, replicator_authenticator1, replicator_authenticator2, sg1_blip_url, sg2_blip_url, sg1, sg2, repl1, _, cbl_db1, cbl_db2, _ = setup_syncGateways_with_cbl(params_from_base_test_setup,
                                                                                                                                                                                                                                                                   setup_customized_teardown_test, cbl_replication_type="push_pull",
                                                                                                                                                                                                                                                                   sgw_cluster1_sg_config_name=sgw_cluster1_conf_name, sgw_cluster2_sg_config_name=sgw_cluster2_conf_name)

    # 2. Create docs on cbl-db1 and have push_pull, continous replication with sg1
    #        each with 2 differrent channel, few docs on both channels
    channels3 = channels1 + channels2
    sg_client.create_user(sg1.admin.admin_url, sg_db1, name3, password=password1, channels=channels3)
    sg_client.create_user(sg2.admin.admin_url, sg_db2, name4, password=password2, channels=channels3)

    cookie, session_id = sg_client.create_session(sg1.admin.admin_url, sg_db1, name3)
    session = cookie, session_id
    replicator_authenticator3 = authenticator.authentication(session_id, cookie, authentication_type="session")
    cookie, session_id = sg_client.create_session(sg2.admin.admin_url, sg_db2, name4)
    replicator_authenticator4 = authenticator.authentication(session_id, cookie, authentication_type="session")

    repl3 = replicator.configure_and_replicate(
        source_db=cbl_db1, replicator_authenticator=replicator_authenticator3, target_url=sg1_blip_url,
        replication_type="push_pull", continuous=True)

    # Create docs with attachments
    db.create_bulk_docs(channel1_docs, Replication1_channel1, db=cbl_db1, channels=channels1)
    replicator.wait_until_replicator_idle(repl3)
    sg_docs = sg_client.get_all_docs(url=sg1.url, db=sg_db1, auth=session)["rows"]
    db.create_bulk_docs(channel2_docs, Replication1_channel2, db=cbl_db1, channels=channels2, attachments_generator=attachment.generate_png_100_100)
    channel3_doc_ids = db.create_bulk_docs(channel3_docs, Replication1_channel3, db=cbl_db1, channels=channels3, attachments_generator=attachment.generate_png_100_100)

    # 3. Start sg-replicate pull/push_pull replication from sg1 <-> sg2 with channel1 with one shot
    repl_id_1 = sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg2.url,
        remote_db=sg_db2,
        remote_user=name4,
        remote_password=password2,
        direction="pushAndPull",
        channels=channels1,
        continuous=continuous
    )
    # 4. verify docs with channel1 which is filtered in replication should get replicated to cbl_db2
    sg1.admin.wait_until_sgw_replication_done(sg_db1, repl_id_1, write_flag=True)
    # Do pull replication from sg2 -> cbl2
    repl4 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator4, target_url=sg2_blip_url,
        replication_type="push_pull", continuous=True)
    # Verify docs with attachments are replicated to sgw cluster2
    sg_docs_attachments = sg_client.get_all_docs(url=sg1.url, db=sg_db1, auth=session, include_docs=True)["rows"]
    for doc in sg_docs_attachments:
        if doc["id"] in channel3_doc_ids:
            assert "_attachments" in doc["doc"], "attachment did not replicated on sgw cluster 2"

    # update docs by adding attachments
    for doc in sg_docs:
        sg_client.update_doc(url=sg1.url, db=sg_db1, doc_id=doc["id"], number_updates=1, auth=session, attachment_name=file_attachment)
    # update docs by deleting attachments
    db.update_bulk_docs_by_deleting_blobs(cbl_db1, doc_ids=channel3_doc_ids)

    # wait until replication completed
    replicator.wait_until_replicator_idle(repl3)
    replicator.wait_until_replicator_idle(repl4)
    # Verify docs created in cbl2
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    count = sum(Replication1_channel1 in s for s in cbl_doc_ids2)
    assert count == channel1_docs, "all docs with channel1 did not replicate to cbl db2"
    count = sum(Replication1_channel3 in s for s in cbl_doc_ids2)
    assert count == channel3_docs, "all docs with channel3 did not replicate to cbl db2"

    # 5. Verify docs with channel2 is not accessed by user 2 i.e cbl db2
    count = sum(Replication1_channel2 in s for s in cbl_doc_ids2)
    assert count == 0, "all docs with channel2 replicated to cbl db2"

    # 6. Verify docs with filtered channel is replicated on both cbl-db1 and cbl-db2 with attachments
    sg_docs = sg_client.get_all_docs(url=sg1.url, db=sg_db1, auth=session, include_docs=True)["rows"]
    for doc in sg_docs:
        if Replication1_channel1 in doc["id"]:
            assert "_attachments" in doc["doc"], "attachment did not updated on sgw cluster 2"
            assert "updates" in doc["doc"], "docs updated in sgw cluster 1 with new property did not replicated to sgw cluster 1"
        if Replication1_channel3 in doc:
            assert "_attachments" not in doc["doc"], "attachment which deleted on doc in sgw cluster 1 did not replicate to sgw cluster 2"

    replicator.stop(repl1)
    replicator.stop(repl3)
    replicator.stop(repl4)


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
@pytest.mark.parametrize("direction", [
    ("pull"),
    ("pushAndPull")
])
def test_sg_replicate_pull_pushPull_channel_filtering(params_from_base_test_setup, setup_customized_teardown_test, direction):
    '''
       @summary
       Covered #53, #54
       1. Set up 2 sgw nodes and have two cbl dbs
       2. Create docs cbl-db1 and cbl-db2 and have push_pull, continous replication
            sg1 <-> cbl-db1, sg2 <-> cbl-db2
            each with 2 differrent channel, few docs on both channels
       3 . Start sg-replicate pull/push_pull replication from sg1 <-> sg2 with channel1 with one shot
       4. verify docs with channel1 is  pulled from sg2 to sg1 for pull case
            docs with channel1 is pushed and pulled sg <-> sg2 for push pull case
       5. Verify docs with channel2 is not accessed by user 2 i.e cbl db2
       6. Verify docs with filtered channel is replicated on both cbl-db1 and cbl-db2 with attachments
    '''

    # 1.Have 2 sgw nodes , have cbl on each SGW
    base_url = params_from_base_test_setup["base_url"]
    sgw_cluster1_conf_name = 'listener_tests/sg_replicate_sgw_cluster1'
    sgw_cluster2_conf_name = 'listener_tests/sg_replicate_sgw_cluster2'
    continuous = True
    channel1_docs = 5
    channel2_docs = 7
    name3 = "autotest3"
    name4 = "autotest4"
    channels4 = ["Replication4"]
    sg_client = MobileRestClient()
    authenticator = Authenticator(base_url)
    replication1_channel1 = "cur1_Replication1_channel1"
    replication2_channel1 = "cur1_Replication2_channel1"
    replication3_channel2 = "cur1_Replication3_channel2"

    # 1. Set up 2 sgw nodes and have two cbl dbs
    db, _, sg_db1, sg_db2, _, _, _, password, channels1, channels2, replicator, _, _, sg1_blip_url, sg2_blip_url, sg1, sg2, repl1, _, cbl_db1, cbl_db2, _ = setup_syncGateways_with_cbl(params_from_base_test_setup,
                                                                                                                                                                                        setup_customized_teardown_test, cbl_replication_type="push",
                                                                                                                                                                                        sgw_cluster1_sg_config_name=sgw_cluster1_conf_name, sgw_cluster2_sg_config_name=sgw_cluster2_conf_name)
    # 2. Create docs on cbl-db1 and have push_pull, continous replication with sg1
    #        each with 2 differrent channel, few docs on both channels

    channels3 = channels1 + channels2 + channels4

    sg_client.create_user(sg1.admin.admin_url, sg_db1, name3, password=password, channels=channels3)
    sg_client.create_user(sg2.admin.admin_url, sg_db2, name4, password=password, channels=channels3)

    cookie, session_id = sg_client.create_session(sg1.admin.admin_url, sg_db1, name3)
    replicator_authenticator3 = authenticator.authentication(session_id, cookie, authentication_type="session")
    cookie, session_id = sg_client.create_session(sg2.admin.admin_url, sg_db2, name4)
    replicator_authenticator4 = authenticator.authentication(session_id, cookie, authentication_type="session")

    # Create docs with channel1 on sgw cluster1 and channel on sgw cluster2.
    db.create_bulk_docs(channel1_docs, replication1_channel1, db=cbl_db1, channels=channels1)
    db.create_bulk_docs(channel1_docs, replication2_channel1, db=cbl_db2, channels=channels1)
    db.create_bulk_docs(channel2_docs, replication3_channel2, db=cbl_db2, channels=channels2)

    repl3 = replicator.configure_and_replicate(
        source_db=cbl_db1, replicator_authenticator=replicator_authenticator3, target_url=sg1_blip_url,
        replication_type="push_pull", continuous=True)
    repl4 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator4, target_url=sg2_blip_url,
        replication_type="pull", continuous=True
    )
    # 4. pull replication from sg1 -> sg2
    repl_id_1 = sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg2.url,
        remote_db=sg_db2,
        remote_user=name4,
        remote_password=password,
        direction=direction,
        channels=channels1,
        continuous=continuous
    )
    # 4. verify docs with channel1 which is filtered in replication should get replicated to cbl_db2
    read_flag = False
    write_flag = False
    if "pull" in direction:
        read_flag = True
    if "push" in direction:
        write_flag = True
    sg1.admin.wait_until_sgw_replication_done(sg_db1, repl_id_1, read_flag=read_flag, write_flag=write_flag)

    # wait until replication completed
    replicator.wait_until_replicator_idle(repl3)
    # Verify docs replicated to cbl_db1
    if "pull" in direction:
        cbl_doc_ids1 = db.getDocIds(cbl_db1)
        count = sum(replication1_channel1 in s for s in cbl_doc_ids1)
        assert count == channel1_docs, "all docs with channel1 did not replicate to cbl db1 and channel filtering did not work"
        count = sum(replication3_channel2 in s for s in cbl_doc_ids1)
        assert count == 0, "all docs with channel2 replicated to cbl db1 and channel filtering did not work"
    if "push" in direction:
        cbl_doc_ids2 = db.getDocIds(cbl_db2)
        count = sum(replication2_channel1 in s for s in cbl_doc_ids2)
        assert count == channel1_docs, "all docs with channel1 did not replicate to cbl db2 and channel filtering did not work"

    replicator.stop(repl1)
    replicator.stop(repl3)
    replicator.stop(repl4)


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
@pytest.mark.parametrize("reconnect_interval", [
    (True),
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
    cluster_config = params_from_base_test_setup["cluster_config"]
    sgw_cluster1_conf_name = 'listener_tests/sg_replicate_sgw_cluster1'
    sgw_cluster2_conf_name = 'listener_tests/sg_replicate_sgw_cluster2'
    sg_mode = params_from_base_test_setup["mode"]
    sg_mode = params_from_base_test_setup["mode"]
    continuous = True
    Replication1 = "Replication1_test2"
    Replication2 = "Replication2_test2"
    sg_conf = sync_gateway_config_path_for_mode(sgw_cluster2_conf_name, sg_mode)
    reconnect_interval_time = 0
    if reconnect_interval:
        reconnect_interval_time = 1

    # 1. Set up 2 sgw nodes and have two cbl dbs
    db, num_of_docs, sg_db1, sg_db2, name1, name2, _, password, channels1, channels2, replicator, replicator_authenticator1, replicator_authenticator2, sg1_blip_url, sg2_blip_url, sg1, sg2, repl1, c_cluster, cbl_db1, cbl_db2, _ = setup_syncGateways_with_cbl(params_from_base_test_setup, setup_customized_teardown_test, cbl_replication_type="push", sgw_cluster1_sg_config_name=sgw_cluster1_conf_name,
                                                                                                                                                                                                                                                                  sgw_cluster2_sg_config_name=sgw_cluster2_conf_name)

    # 2. Create docs on cbl-db1 and have push_pull, continous replication with sg1
    db.create_bulk_docs(num_of_docs, Replication1, db=cbl_db1, channels=channels1, attachments_generator=attachment.generate_png_100_100)

    # 3. Start replication with continuous true sg1<->sg2
    repl_id_1 = sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg2.url,
        remote_db=sg_db2,
        remote_user=name2,
        remote_password=password,
        direction="pushAndPull",
        continuous=continuous,
        max_backoff_time=reconnect_interval_time
    )
    with ThreadPoolExecutor(max_workers=4) as tpe:
        # 4. Update docs on sg1
        cbl_db1_docs = tpe.submit(db.create_bulk_docs, num_of_docs, Replication2, db=cbl_db1, channels=channels1)

        # 5. restart sg2 While replication is happening
        if reconnect_interval:
            c_cluster.sync_gateways[1].stop()
            time.sleep(60)  # Need to wait for a minute to restart It is required for the test as part of reconnect test
        restart_sg = tpe.submit(c_cluster.sync_gateways[1].restart, config=sg_conf, cluster_config=cluster_config)
        cbl_db1_docs.result()
        restart_sg.result()

    sg1.admin.wait_until_sgw_replication_done(sg_db1, repl_id_1, write_flag=True)

    # 7. verify all docs got replicated on sg2
    repl2 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url,
        replication_type="pull", continuous=continuous)
    replicator.wait_until_replicator_idle(repl2)
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    count = sum(Replication2 in s for s in cbl_doc_ids2)
    assert count == num_of_docs, "all docs with channel1 did not replicate to cbl db2"
    replicator.stop(repl1)
    replicator.stop(repl2)


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
def test_sg_replicate_multiple_replications_with_filters(params_from_base_test_setup, setup_customized_teardown_test):
    '''
       @summary
       Covered #56
       "1.create docs with mutlple  channels, channel1, channel2, channel3..
        2. start replication for each channel with push_pull
        3. verfiy docs get replicated to sg2"
    '''

    # Have 2 sgw nodes , have cbl on each SGW
    sgw_cluster1_conf_name = 'listener_tests/sg_replicate_sgw_cluster1'
    sgw_cluster2_conf_name = 'listener_tests/sg_replicate_sgw_cluster2'
    base_url = params_from_base_test_setup["base_url"]
    continuous = True
    channel1_docs = 5
    channel2_docs = 7
    channel3_docs = 8
    name3 = "autotest3"
    name4 = "autotest4"
    channels3 = ["Replication3"]
    channels4 = ["Replication4"]
    Replication1_channel1 = "Replication1_channel1_test5"
    Replication1_channel2 = "Replication1_channel2_test5"
    Replication1_channel3 = "Replication1_channel3_test5"
    Replication1_channel4 = "Replication1_channel4_test5"
    sg_client = MobileRestClient()
    authenticator = Authenticator(base_url)

    # Set up 2 sgw nodes and have two cbl dbs
    db, num_of_docs, sg_db1, sg_db2, name1, name2, _, password, channels1, channels2, replicator, replicator_authenticator1, replicator_authenticator2, sg1_blip_url, sg2_blip_url, sg1, sg2, repl1, _, cbl_db1, cbl_db2, _ = setup_syncGateways_with_cbl(params_from_base_test_setup,
                                                                                                                                                                                                                                                          setup_customized_teardown_test, cbl_replication_type="push_pull",
                                                                                                                                                                                                                                                          sgw_cluster1_sg_config_name=sgw_cluster1_conf_name, sgw_cluster2_sg_config_name=sgw_cluster2_conf_name)
    channels = channels1 + channels2 + channels3
    channels_list = [channels1, channels2, channels3, channels4]
    sg_client.create_user(sg1.admin.admin_url, sg_db1, name3, password=password, channels=channels)
    sg_client.create_user(sg2.admin.admin_url, sg_db2, name4, password=password, channels=channels)

    cookie, session_id = sg_client.create_session(sg1.admin.admin_url, sg_db1, name3)
    replicator_authenticator3 = authenticator.authentication(session_id, cookie, authentication_type="session")
    cookie, session_id = sg_client.create_session(sg2.admin.admin_url, sg_db2, name4)
    replicator_authenticator4 = authenticator.authentication(session_id, cookie, authentication_type="session")

    # 1.create docs with mutlple  channels, channel1, channel2, channel3..
    db.create_bulk_docs(channel1_docs, Replication1_channel1, db=cbl_db1, channels=channels1)
    db.create_bulk_docs(channel2_docs, Replication1_channel2, db=cbl_db1, channels=channels2)
    db.create_bulk_docs(channel3_docs, Replication1_channel3, db=cbl_db1, channels=channels3)

    repl3 = replicator.configure_and_replicate(
        source_db=cbl_db1, replicator_authenticator=replicator_authenticator3, target_url=sg1_blip_url,
        replication_type="push_pull", continuous=True)
    # 2. start replication for each channel with push_pull
    repl_id = []
    for channel in channels_list:
        replid = sg1.start_replication2(
            local_db=sg_db1,
            remote_url=sg2.url,
            remote_db=sg_db2,
            remote_user=name4,
            remote_password=password,
            direction="pushAndPull",
            continuous=continuous,
            channels=channel
        )
        repl_id.append(replid)
    expected_tasks = 4
    active_tasks = sg1.admin.get_sgreplicate2_active_tasks(sg_db1, expected_tasks=expected_tasks)
    assert len(active_tasks) == expected_tasks, "number of expected tasks is not 4"

    # wait replication to completed in SGW
    i = 0
    for replid in repl_id:
        sg1.admin.wait_until_sgw_replication_done(sg_db1, replid, write_flag=True)
        i += 1
    # Do pull replication from sg2 -> cbl2
    repl4 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator4, target_url=sg2_blip_url,
        replication_type="push_pull", continuous=True
    )

    # 3. Verify docs created in sg2 and eventually replicated to cbl2
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    count = sum(Replication1_channel1 in s for s in cbl_doc_ids2)
    assert count == channel1_docs, "docs with  Replication1_channel1 did not replicate to cbl db2"
    count = sum(Replication1_channel2 in s for s in cbl_doc_ids2)
    assert count == channel2_docs, "docs with  Replication1_channel2 did not replicate to cbl db2"
    count = sum(Replication1_channel3 in s for s in cbl_doc_ids2)
    assert count == channel3_docs, "docs with  Replication1_channel3 did not replicate to cbl db2"
    count = sum(Replication1_channel4 in s for s in cbl_doc_ids2)
    assert count == 0, "docs with  Replication1_channel4 did not replicate to cbl db2"

    replicator.stop(repl1)
    replicator.stop(repl3)
    replicator.stop(repl4)


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
@pytest.mark.parametrize("purge_on_removal", [
    (True),
    (False)
])
def test_sg_replicate_remove_channel(params_from_base_test_setup, setup_customized_teardown_test, purge_on_removal):
    '''
       @summary
       Covered #58, 59
       "1. Create user which has access to the channels: channel1, channel2, channel3
        2. create docs with 3  channels:  channel1, channel2, channel3
        3. start replication with push_pull with continuous true with no channel filtering
        4. update the docs with channel3 to channel4
        5. Wait for replication happened
        6. Verify docs which updated with channel4 cannot be accessed by user1 if purge_on_removal=true
            else docs are still accessed by user1 without new updates by user if purge on removal=false"
    '''

    # Have 2 sgw nodes , have cbl on each SGW
    sgw_cluster1_conf_name = 'listener_tests/sg_replicate_sgw_cluster1'
    sgw_cluster2_conf_name = 'listener_tests/sg_replicate_sgw_cluster2'
    base_url = params_from_base_test_setup["base_url"]
    continuous = True
    num_of_docs = 10

    name3 = "autotest3"
    name4 = "autotest4"
    channels3 = ["Replication3"]
    channels4 = ["Replication4"]
    replication1_channel1 = "Replication1_channel1"
    replication1_channel3 = "Replication1_channel3"
    sg_client = MobileRestClient()
    authenticator = Authenticator(base_url)

    # Set up 2 sgw nodes and have two cbl dbs
    db, num_of_docs, sg_db1, sg_db2, _, _, _, password, channels1, channels2, replicator, _, replicator_authenticator2, sg1_blip_url, sg2_blip_url, sg1, sg2, repl1, _, cbl_db1, cbl_db2, _ = setup_syncGateways_with_cbl(params_from_base_test_setup,
                                                                                                                                                                                                                          setup_customized_teardown_test, cbl_replication_type="push_pull",
                                                                                                                                                                                                                          sgw_cluster1_sg_config_name=sgw_cluster1_conf_name, sgw_cluster2_sg_config_name=sgw_cluster2_conf_name)
    replicator.stop(repl1)
    channels = channels1 + channels2 + channels3
    sg_client.create_user(sg1.admin.admin_url, sg_db1, name3, password=password, channels=channels)
    sg_client.create_user(sg2.admin.admin_url, sg_db2, name4, password=password, channels=channels)

    cookie, session_id = sg_client.create_session(sg1.admin.admin_url, sg_db1, name3)
    session = cookie, session_id
    replicator_authenticator3 = authenticator.authentication(session_id, cookie, authentication_type="session")
    cookie, session_id = sg_client.create_session(sg2.admin.admin_url, sg_db2, name4)
    replicator_authenticator4 = authenticator.authentication(session_id, cookie, authentication_type="session")

    # 1.create docs with mutlple  channels, channel1, channel2, channel3..
    db.create_bulk_docs(num_of_docs, replication1_channel1, db=cbl_db1, channels=channels1)
    db.create_bulk_docs(num_of_docs, replication1_channel3, db=cbl_db1, channels=channels3)

    repl3 = replicator.configure_and_replicate(
        source_db=cbl_db1, replicator_authenticator=replicator_authenticator3, target_url=sg1_blip_url,
        replication_type="push_pull", continuous=True)

    sg_docs_1 = sg_client.get_all_docs(url=sg1.url, db=sg_db1, auth=session)["rows"]
    # 2. start replication for each channel with push_pull
    replid = sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg2.url,
        remote_db=sg_db2,
        remote_user=name4,
        remote_password=password,
        direction="pushAndPull",
        continuous=continuous,
        purge_on_removal=purge_on_removal)

    # wait replication to complete in SGW
    sg1.admin.wait_until_sgw_replication_done(sg_db1, replid, write_flag=True)

    # Do replication from sg2 -> cbl2
    repl4 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator4, target_url=sg2_blip_url,
        replication_type="push_pull", continuous=True
    )

    # update docs by deleting/replace  channel
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    cbl_db_docs = db.getDocuments(cbl_db2, cbl_doc_ids2)
    for doc in cbl_db_docs:
        if cbl_db_docs[doc]["channels"] == channels3:
            cbl_db_docs[doc]["channels"] = channels4
    db.updateDocuments(cbl_db2, cbl_db_docs)

    replicator.wait_until_replicator_idle(repl4)
    if purge_on_removal:
        sg1.admin.wait_until_sgw_replication_done(sg_db1, replid, read_flag=True)
    else:
        sg1.admin.wait_until_sgw_replication_done(sg_db1, replid, read_flag=True)
    sg_docs = sg_client.get_all_docs(url=sg1.url, db=sg_db1, auth=session)["rows"]
    count1 = sum(replication1_channel3 in sg_doc["id"] for sg_doc in sg_docs)
    if purge_on_removal:
        assert count1 == 0, "docs with  Replication1_channel3 did not get updated to sg node1"
    else:
        assert count1 == num_of_docs, "docs with  Replication1_channel3 did not get updated  to sg node1"
        for doc1 in sg_docs_1:
            if replication1_channel3 in doc1:
                assert sg_docs_1[doc1]['rev'] == sg_docs[doc1]['rev'], "docs revision before sg replication is not same with purge on removal false"
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
    cluster_config = params_from_base_test_setup["cluster_config"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    cbl_db3 = setup_customized_teardown_test["cbl_db3"]
    sgw_cluster1_conf_name = 'listener_tests/sg_replicate_sgw_cluster1'
    sgw_cluster2_conf_name = 'listener_tests/sg_replicate_sgw_cluster2'
    sg_conf_name = 'listener_tests/three_sync_gateways'
    sg_db1 = "sg_db1"
    name3 = "autotest3"
    channels1 = ["Replication1"]
    channels2 = ["Replication2"]
    channels3 = channels1 + channels2
    Replication1 = "Replication1_test4"
    Replication2 = "Replication2_test4"
    Replication3 = "Replication3_test4"
    continuous = True

    # set up 2 sgw nodes in one cluster by pointing sg_db1 and sg_db2 to same data-bucket
    sg_client = MobileRestClient()
    sgwgateway = SyncGateway()
    authenticator = Authenticator(base_url)
    db, num_of_docs, sg_db1, sg_db2, name1, name2, _, password, _, _, replicator, _, replicator_authenticator2, _, sg2_blip_url, sg1, sg2, repl1, c_cluster, cbl_db1, cbl_db2, _ = setup_syncGateways_with_cbl(params_from_base_test_setup, setup_customized_teardown_test,
                                                                                                                                                                                                               cbl_replication_type="push_pull", sg_conf_name=sg_conf_name,
                                                                                                                                                                                                               channels1=channels3, sgw_cluster1_sg_config_name=sgw_cluster1_conf_name, sgw_cluster2_sg_config_name=sgw_cluster2_conf_name)
    sg3 = c_cluster.sync_gateways[2]
    sgw_cluster1_sg_config = sync_gateway_config_path_for_mode(sgw_cluster1_conf_name, sg_mode)
    sgw_cluster1_config_path = "{}/{}".format(os.getcwd(), sgw_cluster1_sg_config)
    sgwgateway.redeploy_sync_gateway_config(cluster_config=cluster_config, sg_conf=sgw_cluster1_config_path, url=sg3.ip,
                                            sync_gateway_version=sync_gateway_version, enable_import=True)

    channels3 = channels1 + channels2
    sg3_admin_url = sg3.admin.admin_url
    sg3_blip_url = "ws://{}:4984/{}".format(sg3.ip, sg_db1)
    if sg_ssl:
        sg3_blip_url = "wss://{}:4984/{}".format(sg3.ip, sg_db1)
    sg_client.create_user(sg3_admin_url, sg_db1, name3, password=password, channels=channels3)
    cookie, session_id = sg_client.create_session(sg3_admin_url, sg_db1, name3)
    replicator_authenticator3 = authenticator.authentication(session_id, cookie, authentication_type="session")

    db.create_bulk_docs(num_of_docs, Replication1, db=cbl_db1, channels=channels1)
    db.create_bulk_docs(num_of_docs, Replication2, db=cbl_db2, channels=channels1)
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
        remote_url=sg2.url,
        remote_db=sg_db2,
        remote_user=name2,
        remote_password=password,
        direction="push",
        channels=channels1,
        continuous=continuous
    )
    sgw_repl2 = sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg2.url,
        remote_db=sg_db2,
        remote_user=name2,
        remote_password=password,
        direction="pull",
        channels=channels1,
        continuous=continuous
    )
    expected_tasks = 2
    active_tasks = sg1.admin.get_sgreplicate2_active_tasks(sg_db1, expected_tasks=expected_tasks)
    assert len(active_tasks) == expected_tasks, "did not show right number of tasks "

    # 3. verify only one replication runs only one node on EE and 2 replications on each on CE
    if sg_ce:
        expected_count = 2
        repl_count = sg1.admin.get_replications_count(sg_db1, expected_count=expected_count)
        assert repl_count == expected_count, "replications count did not get the right number on sg1"
        repl_count = sg3.admin.get_replications_count(sg_db1, expected_count=expected_count)
        assert repl_count == expected_count, "replications count did not get the right number on sg3"
    else:
        expected_count = 1
        repl_count = sg1.admin.get_replications_count(sg_db1, expected_count=expected_count)
        assert repl_count == expected_count, "replications count did not get the right number on sg1"
        repl_count = sg3.admin.get_replications_count(sg_db1, expected_count=expected_count)
        assert repl_count == expected_count, "replications count did not get the right number on sg3"

    # 4. Drop one active sgw node
    sg3.stop()

    # 5. Verify both the replications runs on one sgw node of active cluster
    expected_count = 2
    local_repl_count = sg1.admin.get_replications_count(sg_db1, expected_count)
    assert local_repl_count == expected_count, "replications count did not get the right number on sg1"

    # 6. Verify replication completes all docs replicated to destination node
    db.create_bulk_docs(num_of_docs, Replication3, db=cbl_db1, channels=channels1)

    # sg1.admin.get_sgreplicate2_active_tasks(sg_db1, sgw_repl1, num_of_expected_written_docs = num_of_docs * 3)
    replicator.wait_until_replicator_idle(repl1)
    sg1.admin.wait_until_sgw_replication_done(sg_db1, sgw_repl1, write_flag=True)
    sg1.admin.wait_until_sgw_replication_done(sg_db1, sgw_repl2, read_flag=True)
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    cbl_doc_ids1 = db.getDocIds(cbl_db1)
    count = sum(Replication1 in s for s in cbl_doc_ids2)
    assert count == num_of_docs, "all docs do not replicate from cbl_db1 to cbl_db2"
    count2 = sum(Replication2 in s for s in cbl_doc_ids1)
    assert count2 == num_of_docs, "all docs do not replicate from cbl_db2 to cbl_db1"
    count3 = sum(Replication3 in s for s in cbl_doc_ids2)
    assert count3 == num_of_docs, "all docs do not replicate from cbl_db1 to cbl_db2"

    replicator.stop(repl1)
    replicator.stop(repl2)
    replicator.stop(repl3)


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
def test_sg_replicate_sgwconfig_replications_with_opt_out(params_from_base_test_setup, setup_customized_teardown_test):
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
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    sg_conf_name = 'listener_tests/four_sync_gateways'
    sg_conf_name2 = 'listener_tests/listener_tests_with_replications'
    sgw_cluster2_conf_name = 'listener_tests/sg_replicate_sgw_cluster2'
    sg_conf_name3 = 'listener_tests/sg_replicate_sgw_cluster1'
    channels1 = ['Replication1']
    channels2 = ['Replication2']
    channels3 = ['Replication3']
    channels = channels1 + channels2 + channels3
    sg_client = MobileRestClient()
    authenticator = Authenticator(base_url)
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name2, sg_mode)
    sg_config2 = sync_gateway_config_path_for_mode(sgw_cluster2_conf_name, sg_mode)
    sg_config3 = sync_gateway_config_path_for_mode(sg_conf_name3, sg_mode)
    cbl_db3 = setup_customized_teardown_test["cbl_db3"]

    db, num_of_docs, sg_db1, sg_db2, name1, name2, _, password, channels1, channels2, replicator, _, replicator_authenticator2, _, sg2_blip_url, sg1, sg2, repl1, c_cluster, cbl_db1, cbl_db2, _ = setup_syncGateways_with_cbl(params_from_base_test_setup, setup_customized_teardown_test, channels1=channels,
                                                                                                                                                                                                                               cbl_replication_type="push_pull", sg_conf_name=sg_conf_name, sgw_cluster2_sg_config_name=sgw_cluster2_conf_name)

    name3 = "autotest3"
    name4 = "autotest4"
    replication1_channel1 = "Replication1_channel1"
    replication1_channel2 = "Replication1_channel2"
    replication1_channel3 = "Replication1_channel3"
    replication1_channel4 = "Replication1_channel4"
    channels1 = ['Replication1']  # Have to reassign as it overrided by setup_syncGateways_with_cbl
    sg3 = c_cluster.sync_gateways[2]
    sg4 = c_cluster.sync_gateways[3]
    sg3_admin_url = sg3.admin.admin_url
    sg4_admin_url = sg4.admin.admin_url
    sg4_blip_url = "ws://{}:4984/{}".format(sg4.ip, sg_db1)
    if sg_ssl:
        sg4_blip_url = "wss://{}:4984/{}".format(sg4.ip, sg_db1)

    # 1. start 3 replications for 3 nodes
    temp_sg_config, _ = copy_sgconf_to_temp(sg_config, sg_mode)
    replication_1, sgw_repl1 = setup_replications_on_sgconfig(sg2.url, sg_db2, name2, password, channels=channels1, continuous=True)
    replication_2, sgw_repl2 = setup_replications_on_sgconfig(sg2.url, sg_db2, name2, password, channels=channels2, continuous=True)
    replication_3, sgw_repl3 = setup_replications_on_sgconfig(sg2.url, sg_db2, name2, password, channels=channels3, continuous=True)

    replications_ids = "{},{},{}".format(replication_1, replication_2, replication_3)
    replications_key = "replications"
    replace_string = "\"{}\": {}{}{},".format(replications_key, "{", replications_ids, "}")

    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ replace_with_replications }}", replace_string)
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "\"db\"", "\"sg_db1\"")
    sg1.restart(config=temp_sg_config, cluster_config=cluster_config)
    sg2.restart(config=sg_config2, cluster_config=cluster_config)

    # 2. Have 3rd node with opt out on sgw-config
    temp_sg_config, _ = copy_sgconf_to_temp(sg_config, sg_mode)
    replace_string3 = "\"sgreplicate_enabled\": false,"
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ replace_with_replications }}", replace_string3)
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "\"db\"", "\"sg_db1\"")
    sg3.restart(config=temp_sg_config, cluster_config=cluster_config)

    #  Have 4th node with regular config
    sg4.restart(config=sg_config3, cluster_config=cluster_config)

    # Create users with new config
    sg_client.create_user(sg3_admin_url, sg_db1, name3, password=password, channels=channels)
    cookie, session_id = sg_client.create_session(sg3_admin_url, sg_db1, name3)
    sg_client.create_user(sg4_admin_url, sg_db1, name4, password=password, channels=channels)
    cookie, session_id = sg_client.create_session(sg4_admin_url, sg_db1, name4)
    replicator_authenticator4 = authenticator.authentication(session_id, cookie, authentication_type="session")

    # Now create docs on all sg nodes
    db.create_bulk_docs(num_of_docs, replication1_channel1, db=cbl_db1, channels=channels1)
    db.create_bulk_docs(num_of_docs, replication1_channel2, db=cbl_db2, channels=channels2)
    sdk_doc_bodies = document.create_docs(replication1_channel3, number=num_of_docs, channels=channels3)
    bucket = c_cluster.servers[0].get_bucket_names()
    cbs_ip = c_cluster.servers[0].host
    sdk_client = get_sdk_client_with_bucket(ssl_enabled, c_cluster, cbs_ip, bucket[0])
    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    sdk_client.upsert_multi(sdk_docs)
    sdk_doc_bodies4 = document.create_docs(replication1_channel4, number=num_of_docs, channels=channels3)
    sdk_docs4 = {doc['_id']: doc for doc in sdk_doc_bodies4}
    sdk_client.upsert_multi(sdk_docs4)

    repl2 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url)
    repl3 = replicator.configure_and_replicate(
        source_db=cbl_db3, replicator_authenticator=replicator_authenticator4, target_url=sg4_blip_url)
    expected_tasks = 3
    active_tasks = sg1.admin.get_sgreplicate2_active_tasks(sg_db1, expected_tasks=expected_tasks)
    assert len(active_tasks) == expected_tasks, "did not show right number of tasks "
    # 3. Verify 3 replications are distributed to first 2 node
    repl_count1 = sg1.admin.get_replications_count(sg_db1)
    expected_count = 0
    repl_count2 = sg3.admin.get_replications_count(sg_db1, expected_count=expected_count)
    repl_count3 = sg4.admin.get_replications_count(sg_db1)
    assert repl_count1 == 1 or repl_count1 == 2, "replications count did not get the right number on sg1"
    assert repl_count2 == expected_count, "replications count did not get the right number on sg3"
    assert repl_count3 == 1 or repl_count3 == 2, "replications count did not get the right number on sg4"

    # Verify all replications are completed
    replicator.wait_until_replicator_idle(repl1)
    replicator.wait_until_replicator_idle(repl2)
    replicator.wait_until_replicator_idle(repl3)
    sg1.admin.wait_until_sgw_replication_done(sg_db1, sgw_repl1, read_flag=True, write_flag=True)
    sg1.admin.wait_until_sgw_replication_done(sg_db1, sgw_repl2, read_flag=True, write_flag=True)
    sg1.admin.wait_until_sgw_replication_done(sg_db1, sgw_repl3, read_flag=True, write_flag=True)
    replicator.wait_until_replicator_idle(repl1)
    replicator.wait_until_replicator_idle(repl2)
    replicator.wait_until_replicator_idle(repl3)
    cbl_doc_ids1 = db.getDocIds(cbl_db1)
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    cbl_doc_ids3 = db.getDocIds(cbl_db3)
    count = sum(replication1_channel2 in s for s in cbl_doc_ids3)
    assert count == num_of_docs, "all docs do not replicate from cbl_db2 to cbl_db3"
    count = sum(replication1_channel2 in s for s in cbl_doc_ids1)
    assert count == num_of_docs, "all docs do not replicate from cbl_db2 to cbl_db1"
    count = sum(replication1_channel1 in s for s in cbl_doc_ids2)
    assert count == num_of_docs, "all docs do not replicate from cbl_db1 to cbl_db2"
    count = sum(replication1_channel3 in s for s in cbl_doc_ids2)
    assert count == num_of_docs, "all docs do not replicate from cbl_db3 to cbl_db2"
    count = sum(replication1_channel4 in s for s in cbl_doc_ids2)
    assert count == num_of_docs, "all docs do not replicate from sg3 to cbl_db2"

    replicator.stop(repl1)
    replicator.stop(repl2)
    replicator.stop(repl3)


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
@pytest.mark.parametrize("number_of_replications, continuous", [
    (1, True),
    (3, True),
    (4, True),
    (6, True),
    (3, False),
    (6, False)
])
def test_sg_replicate_distributions_replications(params_from_base_test_setup, setup_customized_teardown_test, number_of_replications, continuous):
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

    base_url = params_from_base_test_setup["base_url"]
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sgw_cluster1_conf_name = 'listener_tests/sg_replicate_sgw_cluster1'
    sgw_cluster2_conf_name = 'listener_tests/sg_replicate_sgw_cluster2'
    sg_conf_name = 'listener_tests/four_sync_gateways'
    replicator = Replication(base_url)
    sg_db4 = "sg_db4"
    channels1 = ["Replication1"]
    channels2 = ["Replication2"]
    channels3 = ["Replication3"]
    channels4 = ["Replication4"]
    channels5 = ["Replication5"]
    channels6 = ["Replication6"]

    channels_6 = channels1 + channels2 + channels3 + channels4 + channels5 + channels6
    db, num_of_docs, sg_db1, sg_db2, name1, name2, _, password, _, _, replicator, _, replicator_authenticator2, _, sg2_blip_url, sg1, sg2, repl1, c_cluster, cbl_db1, cbl_db2, _ = setup_syncGateways_with_cbl(params_from_base_test_setup, setup_customized_teardown_test,
                                                                                                                                                                                                               cbl_replication_type="push_pull", sg_conf_name=sg_conf_name,
                                                                                                                                                                                                               sgw_cluster1_sg_config_name=sgw_cluster1_conf_name, sgw_cluster2_sg_config_name=sgw_cluster2_conf_name,
                                                                                                                                                                                                               channels1=channels_6)
    sg3 = c_cluster.sync_gateways[2]
    sg4 = c_cluster.sync_gateways[3]
    sgw_cluster1_sg_config = sync_gateway_config_path_for_mode(sgw_cluster1_conf_name, sg_mode)
    sg3.restart(config=sgw_cluster1_sg_config, cluster_config=cluster_config)
    sg4, sg_db4, sg4_admin_url, sg4_blip_url = get_sg4(params_from_base_test_setup, c_cluster, sg_db=sg_db1)
    sg4.restart(config=sgw_cluster1_sg_config, cluster_config=cluster_config)

    # Create replications and docs based on parameters passed
    for x in range(number_of_replications):
        channel_name = "Replication-test2-{}".format(x)
        db.create_bulk_docs(num_of_docs, channel_name, db=cbl_db1, channels=[channels_6[x]])
    replicator.wait_until_replicator_idle(repl1)
    sgw_repl_id = []
    for x in range(number_of_replications):
        replication_channel = []
        replication_channel.append(channels_6[x])
        repl_id_x = sg1.start_replication2(
            local_db=sg_db1,
            remote_url=sg2.url,
            remote_db=sg_db2,
            remote_user=name2,
            remote_password=password,
            direction="push",
            channels=[channels_6[x]],
            continuous=continuous
        )
        sgw_repl_id.append(repl_id_x)

    repl2 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url)
    replicator.wait_until_replicator_idle(repl1)

    active_tasks = sg1.admin.get_sgreplicate2_active_tasks(sg_db1, expected_tasks=number_of_replications)
    if continuous:
        assert len(active_tasks) == number_of_replications, "did not show right number of tasks "
    else:
        assert len(active_tasks) == 0, "did not show right number of tasks "

    # 3. verify only one replication runs only one node.
    if number_of_replications == 4 or number_of_replications == 6:
        expected_count = 2
    else:
        expected_count = 1
    repl_count1 = sg1.admin.get_replications_count(sg_db1, expected_count=expected_count)
    repl_count2 = sg3.admin.get_replications_count(sg_db1, expected_count=expected_count)
    repl_count3 = sg4.admin.get_replications_count(sg_db1, expected_count=expected_count)
    if number_of_replications == 1:
        assert repl_count1 == 0 or repl_count1 == 1, "replications count did not get the right number on sg1 with number of replications 1"
        assert repl_count2 == 0 or repl_count3 == 1, "replications count did not get the right number on sg3 with number of replications 1"
        assert repl_count3 == 0 or repl_count3 == 1, "replications count did not get the right number on sg4 with number of replications 1"
    elif number_of_replications == 3:
        assert repl_count1 == 1, "replications count did not get the right number on sg1 with number of replications 3"
        assert repl_count2 == 1, "replications count did not get the right number on sg3 with number of replications 3"
        assert repl_count3 == 1, "replications count did not get the right number on sg4 with number of replications 3"
    elif number_of_replications == 4:
        assert repl_count1 == 1 or repl_count1 == 2, "replications count did not get the right number on sg1 with number of replications 4"
        assert repl_count2 == 1 or repl_count2 == 2, "replications count did not get the right number on sg3 with number of replications 4"
        assert repl_count3 == 1 or repl_count3 == 2, "replications count did not get the right number on sg4 with number of replications 4"
    elif number_of_replications == 6:
        assert repl_count1 == 2, "replications count did not get the right number on sg1 with number of replications 6"
        assert repl_count2 == 2, "replications count did not get the right number on sg3 with number of replications 6"
        assert repl_count3 == 2, "replications count did not get the right number on sg4 with number of replications 6"

    for x in range(number_of_replications):
        sg1.admin.wait_until_sgw_replication_done(sg_db1, sgw_repl_id[x], write_flag=True)
    replicator.wait_until_replicator_idle(repl2)

    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    for x in range(number_of_replications):
        replication_name = "Replication-test2-{}".format(x)
        count = sum(replication_name in s for s in cbl_doc_ids2)
        assert_msg = "all docs of replication - {} did not replicate from cbl_db1 to cbl_db2".format(replication_name)
        assert count == num_of_docs, assert_msg

    replicator.stop(repl1)
    replicator.stop(repl2)


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
    cluster_config = params_from_base_test_setup["cluster_config"]
    cbl_db3 = setup_customized_teardown_test["cbl_db3"]
    sgw_cluster1_conf_name = 'listener_tests/sg_replicate_sgw_cluster1'
    sgw_cluster2_conf_name = 'listener_tests/sg_replicate_sgw_cluster2'
    sg_conf_name = 'listener_tests/four_sync_gateways'
    replicator = Replication(base_url)
    name4 = "autotest4"
    channels3 = ["Replication3"]
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)

    db, num_of_docs, sg_db1, sg_db2, name1, name2, _, password, channels1, channels2, replicator, _, replicator_authenticator2, _, sg2_blip_url, sg1, sg2, repl1, c_cluster, cbl_db1, cbl_db2, _ = setup_syncGateways_with_cbl(params_from_base_test_setup, setup_customized_teardown_test,
                                                                                                                                                                                                                               cbl_replication_type="push_pull", sg_conf_name=sg_conf_name,
                                                                                                                                                                                                                               sgw_cluster1_sg_config_name=sgw_cluster1_conf_name, sgw_cluster2_sg_config_name=sgw_cluster2_conf_name)
    all_channels = channels1 + channels2 + channels3
    sg3 = c_cluster.sync_gateways[2]
    sgw_cluster1_sg_config = sync_gateway_config_path_for_mode(sgw_cluster1_conf_name, sg_mode)
    sg3.restart(config=sgw_cluster1_sg_config, cluster_config=cluster_config)
    sg4, sg_db4, sg4_admin_url, sg4_blip_url = get_sg4(params_from_base_test_setup, c_cluster, sg_db=sg_db1)
    sg4.restart(config=sgw_cluster1_sg_config, cluster_config=cluster_config)

    replicator_authenticator4, _ = create_sguser_cbl_authenticator(base_url, sg4_admin_url, sg_db4, name4, password, channels1)

    # 1. create docs on sg1 and sg2 using cbl_db1 and cbl_db2
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
    for channel in all_channels:
        repl_id_x = sg1.start_replication2(
            local_db=sg_db1,
            remote_url=sg2.url,
            remote_db=sg_db2,
            remote_user=name2,
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
        tpe.submit(
            update_docs_until_sgwnode_update, db, cbl_db1
        )
        sg3.stop()
        expected_tasks = 3
        sg_active_tasks = sg1.admin.get_sgreplicate2_active_tasks(sg_db1, expected_tasks=expected_tasks)
        assert len(sg_active_tasks) == expected_tasks, "stopping one of the sg node stopped some of the active tasks"
        expected_count = 2
        sg1_repl_count = sg1.admin.get_replications_count(sg_db1, expected_count=expected_count)
        sg4_repl_count = sg4.admin.get_replications_count(sg_db1, expected_count=expected_count)
        assert sg1_repl_count == 1 or sg1_repl_count == 2, "replications count on first node should have 1 or 2"
        assert sg4_repl_count == 1 or sg4_repl_count == 2, "replications count on sg node4 should have 1 or 2"

        sg3.start(sg_config)
        sg_active_tasks = sg1.admin.get_sgreplicate2_active_tasks(sg_db1, expected_tasks=expected_tasks)
        assert len(sg_active_tasks) == expected_tasks, "Adding one of the sg node changed number of active replications"
        sg1_repl_count = sg1.admin.get_replications_count(sg_db1)
        sg3_repl_count = sg4.admin.get_replications_count(sg_db1)
        sg4_repl_count = sg4.admin.get_replications_count(sg_db1)
        assert sg1_repl_count == 1, "Adding 1 node to sgw cluster did not effected replications on sg1"
        assert sg3_repl_count == 1, "Adding 1 node to sgw cluster did not effected replications on sg3"
        assert sg4_repl_count == 1, "Adding 1 node to sgw cluster did not effected replications on sg4"

        db.create_bulk_docs(1, "threadStop", db=cbl_db1, channels=channels1)

    # 6. Verify all replications completed on passive node(sg2)
    cbl_doc_ids = db.getDocIds(cbl_db2)
    count1 = sum('Replication1_' in s for s in cbl_doc_ids)
    replication1_cbl_doc_ids = [s for s in cbl_doc_ids if 'Replication1_' in s]
    assert count1 == num_of_docs, "all docs created in cbl db1 did not replicate to cbl db3"
    cbl_docs2 = db.getDocuments(cbl_db2, replication1_cbl_doc_ids)
    cbl_docs3 = db.getDocuments(cbl_db3, replication1_cbl_doc_ids)
    for doc2 in cbl_docs2:
        assert cbl_docs2[doc2]["updates-cbl"] == cbl_docs3[doc2]["updates-cbl"], "docs did not update successfully"
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
       1. Have 4 sg nodes(2 active and 2 passive)
        2. Create docs in sg1(100 docs ?)
        3. Start 3 to 4 replications with push_pull and continuous
        4. updating docs while replication is happening
        4. Restart active nodes/passive nodes

    '''

    base_url = params_from_base_test_setup["base_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_mode = params_from_base_test_setup["mode"]
    cbl_db3 = setup_customized_teardown_test["cbl_db3"]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    sgw_cluster1_conf_name = 'listener_tests/sg_replicate_sgw_cluster1'
    sgw_cluster2_conf_name = 'listener_tests/sg_replicate_sgw_cluster2'
    sg_conf_name = 'listener_tests/four_sync_gateways'
    replicator = Replication(base_url)
    name4 = "autotest4"
    sg_client = MobileRestClient()

    db, num_of_docs, sg_db1, sg_db2, name1, name2, _, password, channels1, channels2, replicator, _, replicator_authenticator2, _, sg2_blip_url, sg1, sg2, repl1, c_cluster, cbl_db1, cbl_db2, session1 = setup_syncGateways_with_cbl(params_from_base_test_setup, setup_customized_teardown_test,
                                                                                                                                                                                                                                      cbl_replication_type="push_pull", sg_conf_name=sg_conf_name,
                                                                                                                                                                                                                                      sgw_cluster1_sg_config_name=sgw_cluster1_conf_name, sgw_cluster2_sg_config_name=sgw_cluster2_conf_name)
    sg3 = c_cluster.sync_gateways[2]

    sg4, sg_db4, sg4_admin_url, sg4_blip_url = get_sg4(params_from_base_test_setup, c_cluster, sg_db=sg_db2)
    sgw_cluster1_sg_config = sync_gateway_config_path_for_mode(sgw_cluster1_conf_name, sg_mode)
    sgw_cluster2_sg_config = sync_gateway_config_path_for_mode(sgw_cluster2_conf_name, sg_mode)
    sg3.restart(config=sgw_cluster1_sg_config, cluster_config=cluster_config)
    sg4.restart(config=sgw_cluster2_sg_config, cluster_config=cluster_config)
    replicator_authenticator4, session4 = create_sguser_cbl_authenticator(base_url, sg4_admin_url, sg_db2, name4, password, channels1)

    # 1. create docs on sg1 and sg2 using cbl_db1 and cbl_db2
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
    repl_id_1 = sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg2.url,
        remote_db=sg_db2,
        remote_user=name2,
        remote_password=password,
        direction="push",
        continuous=True,
        channels=channels1
    )
    repl_id_2 = sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg4.url,
        remote_db=sg_db4,
        remote_user=name4,
        remote_password=password,
        direction="pull",
        continuous=True,
        channels=channels1
    )
    repl_id_3 = sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg4.url,
        remote_db=sg_db4,
        remote_user=name4,
        remote_password=password,
        direction="push",
        continuous=True,
        channels=channels1
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
            restart_sg_nodes(sg1, sg3, sgw_cluster1_sg_config, cluster_config)
        else:
            restart_sg_nodes(sg2, sg4, sgw_cluster2_sg_config, cluster_config)
        db.create_bulk_docs(1, "threadStop", db=cbl_db1, channels=channels1)
        update_from_cbl_task.result()

    replicator.wait_until_replicator_idle(repl1)
    sg1.admin.wait_until_sgw_replication_done(sg_db1, repl_id_1, write_flag=True)
    sg1.admin.wait_until_sgw_replication_done(sg_db1, repl_id_3, write_flag=True)
    sg1.admin.wait_until_sgw_replication_done(sg_db1, repl_id_2, read_flag=True)
    replicator.wait_until_replicator_idle(repl2)
    replicator.wait_until_replicator_idle(repl4)

    # 6. Verify all replications completed on passive node(sg4)
    cbl_doc_ids3 = db.getDocIds(cbl_db3)
    count1 = sum('Replication1_' in s for s in cbl_doc_ids3)
    assert count1 == num_of_docs, "all docs created in cbl db1 did not replicate to cbl db3"
    max_count = 120
    count = 0
    while count < max_count:
        replication_successful_flag = True
        sg4_docs = sg_client.get_all_docs(url=sg4.url, db=sg_db2, auth=session4, include_docs=True)["rows"]
        for doc in sg4_docs:
            try:
                doc["updates-cbl"]
                sg1_doc = sg_client.get_doc(url=sg1.url, db=sg_db1, doc_id=doc["id"], auth=session1)
                if doc["updates-cbl"] != sg1_doc["updates-cbl"]:
                    replication_successful_flag = False
                    break
            except KeyError as e:
                log_info("skipping the docs which does not have new update")
        if replication_successful_flag:
            break
        time.sleep(1)
        count += 1
    assert replication_successful_flag is True, "updated docs did not replicated successfull from sgw cluster1 to sgw cluster2"
    # Verification via sdk
    sg_docs_ids_from_sg4 = [row["id"] for row in sg4_docs]
    bucket = c_cluster.servers[0].get_bucket_names()
    cbs_ip = c_cluster.servers[0].host
    sdk_client1 = get_sdk_client_with_bucket(ssl_enabled, c_cluster, cbs_ip, bucket[0])
    sdk_client2 = get_sdk_client_with_bucket(ssl_enabled, c_cluster, cbs_ip, bucket[1])
    docs_via_sdk_get = sdk_client2.get_multi(sg_docs_ids_from_sg4)
    replication_successful_flag = True
    for doc_id, val in docs_via_sdk_get.items():
        doc_body = val.value
        sdk_doc_id1 = sdk_client1.get(doc_id)
        sdk1_doc_body = sdk_doc_id1.value
        try:
            doc_body["updates-cbl"]
            if doc_body["updates-cbl"] != sdk1_doc_body["updates-cbl"]:
                replication_successful_flag = False
        except KeyError as e:
            log_info("skipping the docs which does not have new update")
        if replication_successful_flag is False:
            break
    assert replication_successful_flag is True, "updated docs did not replicated successfull from sgw cluster1 to sgw cluster2"
    replicator.stop(repl1)
    replicator.stop(repl2)
    replicator.stop(repl4)


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
def test_sg_replicate_adhoc_replication(params_from_base_test_setup, setup_customized_teardown_test):
    '''
       @summary
       Covered for #69 and #70
       1. Have 2 sg nodes(active and passive)
        2. Create 10 docs in sgw cluster1
        3. start replication with adhoc setting with continuous True
        4. Verify docs in step #2 replicated
        5. restart sgw
        6. Create few more docs in SGW cluster1
        7. Verify new docs are not replicated to sgw cluster2

    '''

    # 1.Have 2 sgw nodes , have cbl on each SGW
    sgw_cluster1_conf_name = 'listener_tests/sg_replicate_sgw_cluster1'
    sgw_cluster2_conf_name = 'listener_tests/sg_replicate_sgw_cluster2'
    direction = "pushAndPull"
    replication1_docs = "Replication1_docs"

    db, num_of_docs, sg_db1, sg_db2, name1, name2, _, password, channels1, _, replicator, replicator_authenticator1, replicator_authenticator2, sg1_blip_url, sg2_blip_url, sg1, sg2, repl1, _, cbl_db1, cbl_db2, _ = setup_syncGateways_with_cbl(params_from_base_test_setup, setup_customized_teardown_test,
                                                                                                                                                                                                                                                  cbl_replication_type="push", sgw_cluster1_sg_config_name=sgw_cluster1_conf_name,
                                                                                                                                                                                                                                                  sgw_cluster2_sg_config_name=sgw_cluster2_conf_name)

    db.create_bulk_docs(num_of_docs, replication1_docs, db=cbl_db1, channels=channels1)
    repl2 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url)

    replicator.wait_until_replicator_idle(repl1)

    sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg2.url,
        remote_db=sg_db2,
        remote_user=name2,
        remote_password=password,
        direction=direction,
        adhoc=True
    )
    replicator.wait_until_replicator_idle(repl2)
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    count1 = sum(replication1_docs in s for s in cbl_doc_ids2)
    assert count1 == num_of_docs, "all docs created in cbl db3 did not replicate to cbl db2"
    expected_tasks = 0
    active_tasks = sg1.admin.get_sgreplicate2_active_tasks(sg_db1, expected_tasks=expected_tasks)
    assert len(active_tasks) == expected_tasks, "replications did not get removed with adhoc true config with one shot replication"


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
    sgw_cluster1_conf_name = 'listener_tests/sg_replicate_sgw_cluster1'
    sgw_cluster2_conf_name = 'listener_tests/sg_replicate_sgw_cluster2'

    db, num_of_docs, sg_db1, sg_db2, name1, name2, _, password, channels1, _, replicator, replicator_authenticator1, replicator_authenticator2, sg1_blip_url, sg2_blip_url, sg1, sg2, repl1, _, cbl_db1, cbl_db2, _ = setup_syncGateways_with_cbl(params_from_base_test_setup, setup_customized_teardown_test,
                                                                                                                                                                                                                                                  cbl_replication_type="push", sgw_cluster1_sg_config_name=sgw_cluster1_conf_name,
                                                                                                                                                                                                                                                  sgw_cluster2_sg_config_name=sgw_cluster2_conf_name)
    # 2. Create docs on sg1
    db.create_bulk_docs(num_of_docs, "Replication1", db=cbl_db1, channels=channels1)

    # 3. Start push_pull replication with  one shot with default conflict resolver
    repl_id_1 = sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg2.url,
        remote_db=sg_db2,
        remote_user=name2,
        remote_password=password
    )
    sg1.admin.wait_until_sgw_replication_done(db=sg_db1, repl_id=repl_id_1, write_flag=True)
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
        remote_user=name2,
        remote_password=password,
        conflict_resolution_type=conflict_resolver_type
    )

    # 7. if  local_wins : docs updated on sg1 gets replicated to sg2
    # if  remote_wins : docs updated on sg2 gets replicated to sg1

    # 6. Verify docs created in cbl2
    cbl_doc_ids1 = db.getDocIds(cbl_db1)
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    cbl_db_docs1 = db.getDocuments(cbl_db1, cbl_doc_ids1)
    cbl_db_docs2 = db.getDocuments(cbl_db2, cbl_doc_ids2)
    if conflict_resolver_type == "localWins":
        for doc in cbl_db_docs1:
            assert cbl_db_docs1[doc]["updates-cbl"] == 1, "local_win replication did not happen"
    else:
        for doc in cbl_db_docs2:
            assert cbl_db_docs2[doc]["updates-cbl"] == 3, "remote_win replication did not happen"


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
@pytest.mark.parametrize("custom_conflict_type, external_js", [
    ("merge", False),
    ("merge", True)
])
def test_sg_replicate_custom_conflict_resolve(params_from_base_test_setup, setup_customized_teardown_test, custom_conflict_type, external_js):
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
    sgw_cluster1_conf_name = 'listener_tests/sg_replicate_sgw_cluster1'
    sgw_cluster2_conf_name = 'listener_tests/sg_replicate_sgw_cluster2'
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_conf_name = 'listener_tests/sg_replicate_custom_conflict'

    db, num_of_docs, sg_db1, sg_db2, name1, name2, _, password, channels1, _, replicator, replicator_authenticator1, replicator_authenticator2, sg1_blip_url, sg2_blip_url, sg1, sg2, repl1, _, cbl_db1, cbl_db2, _ = setup_syncGateways_with_cbl(params_from_base_test_setup, setup_customized_teardown_test,
                                                                                                                                                                                                                                                  cbl_replication_type="push_pull",
                                                                                                                                                                                                                                                  sgw_cluster1_sg_config_name=sgw_cluster1_conf_name, sgw_cluster2_sg_config_name=sgw_cluster2_conf_name)
    # 2. Create docs on sg1
    db.create_bulk_docs(num_of_docs, "Replication1", db=cbl_db1, channels=channels1)

    # 3. Start push_pull replication with  one shot with default conflict resolver
    repl_id_1 = sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg2.url,
        remote_db=sg_db2,
        remote_user=name2,
        remote_password=password,
        continuous=True
    )
    sg1.admin.wait_until_sgw_replication_done(db=sg_db1, repl_id=repl_id_1, write_flag=True, max_times=35)
    replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url
    )
    # 4. update docs on sg2 via cbl_db2
    db.update_bulk_docs(cbl_db2, key="cbl2-update")

    # 5. Then update docs on sg1  via cbl_db1
    db.update_bulk_docs(cbl_db1, key="cbl1-update")

    # Add merge js function to sgw config
    repl_id = "replication1"
    if external_js:
        # hosted js code statically as data center vms cannot reach mac machines , if these is not reachable, you need to restart js code
        jscode_external_ip = "172.23.104.165"
        custom_conflict_js_function = "http://{}:5007/conflictResolver".format(jscode_external_ip)
    else:
        custom_conflict_js_function = """function (conflict) {
        if (conflict.LocalDocument.priority > conflict.RemoteDocument.priority) {
            return conflict.LocalDocument;
        } else if (conflict.LocalDocument.priority < conflict.RemoteDocument.priority) {
            return conflict.RemoteDocument;
        }
        return defaultPolicy(conflict);
        }"""

    temp_sg_config = update_replication_in_sgw_config(sg_conf_name, sg_mode, repl_remote=sg2.url, repl_remote_db=sg_db2, repl_remote_user=name2, repl_remote_password=password, repl_repl_id=repl_id,
                                                      repl_direction="pushAndPull", repl_conflict_resolution_type="custom", repl_continuous=True, repl_filter_query_params=None, custom_conflict_js_function=custom_conflict_js_function)
    sg1.restart(config=temp_sg_config, cluster_config=cluster_config)
    # 6. start push_pull replication with one shot with custom conflict resovler
    sg1.admin.wait_until_sgw_replication_done(sg_db1, repl_id, read_flag=True, write_flag=True)
    time.sleep(30)  # To avoid inconsistent failure when replication did not complete
    # 7. if  local_wins : docs updated on sg1 gets replicated to sg2
    # if  remote_wins : docs updated on sg2 gets replicated to sg1
    # Verify docs created in cbl2
    cbl_doc_ids1 = db.getDocIds(cbl_db1)
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    cbl_db_docs1 = db.getDocuments(cbl_db1, cbl_doc_ids1)
    cbl_db_docs2 = db.getDocuments(cbl_db2, cbl_doc_ids2)
    for doc in cbl_db_docs1:
        try:
            cbl_db_docs1[doc]["cbl1-update"]
            assert cbl_db_docs2[doc]["cbl1-update"] == 1, "merge of local and remote doc did not replicated on cbl db2"
        except KeyError:
            assert cbl_db_docs1[doc]["cbl2-update"] == 1, "merge of local and remote doc did not replicated on cbl db1"
            assert cbl_db_docs2[doc]["cbl2-update"] == 1, "merge of local and remote doc did not replicated on cbl db2"


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.sgreplicate
@pytest.mark.parametrize("continuous, direction, attachments, doc_delete_source, delete_sgw_cluster", [
    (False, "pushAndPull", False, "cbl", "sgw1"),
    (False, "pushAndPull", False, "sdk", "sgw1"),
    (False, "pushAndPull", False, "cbl", "sgw2"),
    (False, "pushAndPull", False, "sdk", "sgw2")
])
def test_sg_replicate_doc_resurrection(params_from_base_test_setup, setup_customized_teardown_test, continuous, direction, attachments, doc_delete_source, delete_sgw_cluster):
    '''
       @summary
       1.Have 2 sgw nodes , have cbl on each SGW
       2. Add docs in cbl1
       3. Do push replication to from cbl1 to sg1 cbl -> sg1
       4. pull/push/push_pull replication from sg1 -> sg2 with continuous replication
       5. Do push-pull replication from sg2 -> cbl2
       6. Delete the doc on cbl1/sdk(data-bucket) and recreate the doc with same doc id
       7. Start new push_pull replication from sg1 -> sg2
       8. Verify new recreated doc got pulled to sg2
    '''

    # 1.Have 2 sgw nodes , have cbl on each SGW
    sgw_cluster1_conf_name = 'listener_tests/sg_replicate_sgw_cluster1'
    sgw_cluster2_conf_name = 'listener_tests/sg_replicate_sgw_cluster2'
    base_url = params_from_base_test_setup["base_url"]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    cluster_helper = ClusterKeywords(cluster_config)
    topology = cluster_helper.get_cluster_topology(cluster_config)
    cbs_url = topology["couchbase_servers"][0]
    write_flag = False
    read_flag = False
    sg_client = MobileRestClient()
    documentObj = Document(base_url)
    cbs_ip = host_for_url(cbs_url)

    db, num_of_docs, sg_db1, sg_db2, name1, name2, _, password, channels1, _, replicator, replicator_authenticator1, replicator_authenticator2, sg1_blip_url, sg2_blip_url, sg1, sg2, repl1, c_cluster, cbl_db1, cbl_db2, session1 = setup_syncGateways_with_cbl(params_from_base_test_setup, setup_customized_teardown_test,
                                                                                                                                                                                                                                                                 cbl_replication_type="push", sgw_cluster1_sg_config_name=sgw_cluster1_conf_name,
                                                                                                                                                                                                                                                                 sgw_cluster2_sg_config_name=sgw_cluster2_conf_name)

    bucket = c_cluster.servers[0].get_bucket_names()
    # 2. Add docs in cbl1
    if attachments:
        db.create_bulk_docs(num_of_docs, "sgw1_docs", db=cbl_db1, channels=channels1, attachments_generator=attachment.generate_png_100_100)
        db.create_bulk_docs(num_of_docs, "sgw2_docs", db=cbl_db2, channels=channels1, attachments_generator=attachment.generate_png_100_100)
    else:
        db.create_bulk_docs(num_of_docs, "sgw1_docs", db=cbl_db1, channels=channels1)
        db.create_bulk_docs(num_of_docs, "sgw2_docs", db=cbl_db2, channels=channels1)
    repl2 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url)

    replicator.wait_until_replicator_idle(repl1)
    replicator.wait_until_replicator_idle(repl2)

    if "push" in direction:
        write_flag = True
    if "pull" in direction:
        read_flag = True

    repl_id_1 = sg1.start_replication2(
        local_db=sg_db1,
        remote_url=sg2.url,
        remote_db=sg_db2,
        remote_user=name2,
        remote_password=password,
        direction=direction,
        continuous=True
    )
    sg1.admin.wait_until_sgw_replication_done(sg_db1, repl_id_1, read_flag=read_flag, write_flag=write_flag)

    replicator.wait_until_replicator_idle(repl1)
    replicator.wait_until_replicator_idle(repl2)
    # Verify docs created in cbl2
    if "push" in direction:
        cbl_doc_ids2 = db.getDocIds(cbl_db2)
        count1 = sum('sgw1_docs_' in s for s in cbl_doc_ids2)
        assert count1 == num_of_docs, "all docs do not replicate to cbl db2"
    if "pull" in direction:
        cbl_doc_ids1 = db.getDocIds(cbl_db1)
        count2 = sum('sgw2_docs_' in s for s in cbl_doc_ids1)
        assert count2 == num_of_docs, "all docs do not replicate to cbl db1"

    # 6. Delete the doc on cbl1/sdk(data-bucket) and recreate the doc with same doc id
    cbl_doc_ids1 = db.getDocIds(cbl_db1)
    random_doc_id = random.choice(cbl_doc_ids1)
    if doc_delete_source == "cbl":
        doc_body = document.create_doc(doc_id=random_doc_id, content="testing-doc-resurrec", channels=channels1, cbl=True)
        if delete_sgw_cluster == "sgw1":
            cbl_database = cbl_db1
        else:
            cbl_database = cbl_db2
        db.delete_bulk_docs(cbl_database, doc_ids=[random_doc_id])
        mutable_doc1 = documentObj.create(random_doc_id, doc_body)
        db.saveDocument(cbl_database, mutable_doc1)
    else:
        doc_body = document.create_doc(doc_id=random_doc_id, content="testing-doc-resurrec", channels=channels1)
        if delete_sgw_cluster == "sgw1":
            cbs_bucket = bucket[0]
        else:
            cbs_bucket = bucket[1]
        sdk_client = get_sdk_client_with_bucket(ssl_enabled, c_cluster, cbs_ip, cbs_bucket)
        sdk_client.remove(random_doc_id)
        replicator.wait_until_replicator_idle(repl1)
        sg1.admin.wait_until_sgw_replication_done(sg_db1, repl_id_1, read_flag=read_flag, write_flag=write_flag)
        replicator.wait_until_replicator_idle(repl2)
        sdk_client.upsert(random_doc_id, doc_body)

    replicator.wait_until_replicator_idle(repl1)
    sg1.admin.wait_until_sgw_replication_done(sg_db1, repl_id_1, read_flag=read_flag, write_flag=write_flag)
    replicator.wait_until_replicator_idle(repl2)
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    cbl_doc_ids1 = db.getDocIds(cbl_db1)
    compare_cbl_docs(db, cbl_db1, cbl_db2)
    assert random_doc_id in cbl_doc_ids2, "resurrected doc does not exist on cbl db2"
    assert random_doc_id in cbl_doc_ids1, "resurrected doc does not exist on cbl db1"
    sg_doc1 = sg_client.get_doc(url=sg1.url, db=sg_db1, doc_id=random_doc_id, auth=session1)
    sg_doc2 = sg_client.get_doc(url=sg2.admin.admin_url, db=sg_db2, doc_id=random_doc_id)
    assert sg_doc1['_rev'] == sg_doc2['_rev'], "revisions of sgw cluster1 and sgw cluster 2 did not match for the doc which resurrected"


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


def get_sg4(params_from_base_test_setup, c_cluster, sg_db="sg_db4"):
    sg_ssl = params_from_base_test_setup["sg_ssl"]
    sg4 = c_cluster.sync_gateways[3]
    sg4_ip = sg4.ip
    sg4_admin_url = sg4.admin.admin_url
    sg4_blip_url = "ws://{}:4984/{}".format(sg4_ip, sg_db)
    if sg_ssl:
        sg4_blip_url = "wss://{}:4984/{}".format(sg4_ip, sg_db)

    return sg4, sg_db, sg4_admin_url, sg4_blip_url


def create_sguser_cbl_authenticator(base_url, sg_admin_url, sg_db, name, password, channels):
    sg_client = MobileRestClient()
    authenticator = Authenticator(base_url)
    sg_client.create_user(sg_admin_url, sg_db, name, password=password, channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, name)
    session = cookie, session_id
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    return replicator_authenticator, session


@pytest.fixture(scope="function")
def setup_jsserver():
    process = subprocess.Popen(args=["nohup", "python", "libraries/utilities/host_sgw_jscode.py", "--start", "&"], stdout=subprocess.PIPE)
    yield{
        "process": process
    }
    process.kill()
