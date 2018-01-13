import pytest
import json

from keywords.MobileRestClient import MobileRestClient
from CBLClient.Database import Database
from CBLClient.Replication import Replication
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from libraries.testkit.cluster import Cluster
from libraries.testkit import cluster
from libraries.testkit.admin import Admin


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.noconflicts
@pytest.mark.parametrize("sg_conf_name, num_of_docs", [
    ('listener_tests/multiple_sync_gateways', 10),
    # ('listener_tests/listener_tests_no_conflicts', 100, 10),
    # ('listener_tests/listener_tests_no_conflicts', 1000, 10)
])
def test_multiple_sgs_with_CBLs(params_from_base_test_setup, sg_conf_name, num_of_docs):
    """
        @summary:
        1. Create 2 DBs and Create docs in CBL
        2. Do push replication to two SGS(each DB
        to each SG)
        3. exchange DBs of SG and do pull replication.
        4. stop one of the sg.
        5. pull again
        6. Verify one CBL DB should be successful
        other CBL DB should fail as associated Sg is down

    """
    # base_url = "http://192.168.0.109:8989"
    
    sg_db1 = "sg_db1"
    sg_db2 = "sg_db2"
    cbl_db_name1 = "cbl_db1"
    cbl_db_name2 = "cbl_db2"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    no_conflicts_enabled = params_from_base_test_setup["no_conflicts_enabled"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    channels1 = ["Replication1"]
    channels2 = ["Replication2"]
    name1 = "autotest1"
    name2 = "autotest2"
    sg_client = MobileRestClient()

    if sync_gateway_version < "2.0":
        pytest.skip('--no-conflicts is enabled and does not work with sg < 2.0 , so skipping the test')
    # Modify sync-gateway config to use no-conflicts config
    db = Database(base_url)
    if no_conflicts_enabled:
        sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)
        c = cluster.Cluster(config=cluster_config)
        c.reset(sg_config_path=sg_config)
    else:
        # This is the config set by conftest.py
        c = cluster.Cluster(cluster_config)
        sg_config = sync_gateway_config_path_for_mode("listener_tests/multiple_sync_gateways", sg_mode)
        c.reset(sg_config_path=sg_config)
    
    sg1, sg2 = create_sync_gateways(
        cluster_config=cluster_config,
        sg_config_path=sg_config
    )

    admin = Admin(sg1)
    admin.admin_url = sg1.url
    
    sg1_ip = sg1.ip
    sg2_ip = sg2.ip
    sg1_url = sg1.url
    sg1_admin_url = sg1.admin.admin_url
    sg2_url = sg2.url
    sg2_admin_url = sg2.admin.admin_url
    sg1_blip_url = "blip://{}:4984/{}".format(sg1_ip, sg_db1)
    sg2_blip_url = "blip://{}:4984/{}".format(sg2_ip, sg_db2)

    sg1_user = sg_client.create_user(sg1_admin_url, sg_db1, "autotest1", password="password", channels=channels1)
    sg2_user = sg_client.create_user(sg2_admin_url, sg_db2, "autotest2", password="password", channels=channels2)
    # Create bulk doc json
    cbl_db1 = db.deleteDBIfExistsCreateNew(cbl_db_name1)
    cbl_db2 = db.deleteDBIfExistsCreateNew(cbl_db_name2)
    db.create_bulk_docs(num_of_docs, "Replication1", db=cbl_db1, channels=channels1)
    cbl_doc_ids1 = db.getDocIds(cbl_db1)
    db.create_bulk_docs(num_of_docs, "Replication2", db=cbl_db2, channels=channels2)
    cbl_doc_ids2 = db.getDocIds(cbl_db2)
    
    # 2. Do push replication to two SGS(each DB to each SG)
    replicator = Replication(base_url)
    cookie, session_id = sg_client.create_session(sg1_admin_url, sg_db1, name1)
    session = cookie, session_id
    replicator_authenticator = replicator.authentication(session_id, cookie, authentication_type="session")
    repl1 = replicator.configure_and_replicate(source_db=cbl_db1, replicator=replicator,
                                               replicator_authenticator=replicator_authenticator, target_url=sg1_blip_url, replication_type="push")

    cookie, session_id = sg_client.create_session(sg2_admin_url, sg_db2, name2)
    session = cookie, session_id
    replicator_authenticator = replicator.authentication(session_id, cookie, authentication_type="session")
    repl2 = replicator.configure_and_replicate(source_db=cbl_db2, replicator=replicator,
                                               replicator_authenticator=replicator_authenticator, target_url=sg2_blip_url, replication_type="push")
    replicator.stop(repl1)
    replicator.stop(repl2)

    # 3. exchange DBs of SG and do pull replication.
    repl1 = replicator.configure_and_replicate(source_db=cbl_db1, replicator=replicator,
                                               replicator_authenticator=replicator_authenticator, target_url=sg2_blip_url, replication_type="pull")
    repl2 = replicator.configure_and_replicate(source_db=cbl_db2, replicator=replicator,
                                               replicator_authenticator=replicator_authenticator, target_url=sg1_blip_url, replication_type="pull")
    
    replicator.stop(repl1)
    replicator.stop(repl2)

    # 4. stop one of the sg.
    sg1.stop()

    # 5. Pull again 
    repl1 = replicator.configure_and_replicate(source_db=cbl_db1, replicator=replicator,
                                               replicator_authenticator=replicator_authenticator, target_url=sg2_blip_url, replication_type="pull")
    repl2 = replicator.configure_and_replicate(source_db=cbl_db2, replicator=replicator,
                                               replicator_authenticator=replicator_authenticator, target_url=sg1_blip_url, replication_type="pull")
    
    replicator.stop(repl1)
    repl2_error = replicator.getError(repl2)
    print "The error is:", repl2_error
    replicator.stop(repl2)
    # 6. Verify one CBL DB should be successful as other CBL DB should fail as associated Sg is down
    cblDB1_doc_ids = db.getDocIds(cbl_db1)
    cbl_docs1 = db.getDocuments(cbl_db1, cblDB1_doc_ids)
    print "CBL1  docs ", cbl_docs1
    for doc in cbl_doc_ids1:
        assert doc in cblDB1_doc_ids, "cbl_db1 doc does not exist in combined replication cbl_db1"
    for doc in cbl_doc_ids2:
        assert doc in cblDB1_doc_ids, "cbl_db2 doc does not exist in combined replication cbl_db1"

    cblDB2_doc_ids = db.getDocIds(cbl_db2)
    cbl_docs2 = db.getDocuments(cbl_db2, cbl_doc_ids2)
    print "CBL2  docs ", cbl_docs2
    for doc in cbl_doc_ids1:
        assert doc not in cblDB2_doc_ids, "cbl_db1 doc exist in combined replication cbl_db2"
    for doc in cbl_doc_ids2:
        assert doc in cblDB2_doc_ids, "cbl_db2 doc does not exist in combined replication cbl_db2"



def create_sg_users(sg1, sg2, db1, db2, name1, password1, name2, password2, channels):

    admin1 = Admin(sg1)
    admin2 = Admin(sg2)
    sg1_user = admin1.register_user(
        target=sg1,
        db=db1,
        name=name1,
        password=password1,
        channels=channels,
    )
    sg2_user = admin2.register_user(
        target=sg2,
        db=db2,
        name=name2,
        password=password2,
        channels=channels,
    )
    return sg1_user, sg2_user


def create_sync_gateways(cluster_config, sg_config_path):

    cluster = Cluster(config=cluster_config)
    cluster.reset(sg_config_path=sg_config_path)
    sg1 = cluster.sync_gateways[0]
    sg2 = cluster.sync_gateways[1]

    return sg1, sg2
