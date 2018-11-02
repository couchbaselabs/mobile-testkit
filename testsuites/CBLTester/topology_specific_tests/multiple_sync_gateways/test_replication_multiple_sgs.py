import pytest

from keywords.MobileRestClient import MobileRestClient
from CBLClient.Database import Database
from CBLClient.Replication import Replication
from CBLClient.Authenticator import Authenticator
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from libraries.testkit.cluster import Cluster
from libraries.testkit import cluster
from libraries.testkit.admin import Admin
from keywords.constants import CLUSTER_CONFIGS_DIR
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("sg_conf_name, num_of_docs", [
    ('listener_tests/multiple_sync_gateways', 10),
    ('listener_tests/multiple_sync_gateways', 100),
    ('listener_tests/multiple_sync_gateways', 1000)
])
def test_multiple_sgs_with_differrent_revs_limit(params_from_base_test_setup, setup_customized_teardown_test, sg_conf_name, num_of_docs):
    """
        @summary:
        1. Create 2 DBs in 2 SGS and Create docs in CBL
        2. Set up 1 SG with revs limit 30 and SG2 with revs limit 25.
        3. Do push replication to two SGS(each DB
        to each SG).
        4. Do updates on CBL for 35 times.
        5. Continue push replication to SGs
        6. Verify that revs maintained on two SGS according to revs_limit.
        7. exchange DBs of SG and do push replication.
        8. Verify that revs maintained on two SGS according to revs_limit.

    """
    sg_db1 = "sg_db1"
    sg_db2 = "sg_db2"
    protocol = "ws"
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    base_url = params_from_base_test_setup["base_url"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    sg_ssl = params_from_base_test_setup["sg_ssl"]
    db = Database(base_url)

    channels1 = ["Replication1"]
    channels2 = ["Replication2"]
    name1 = "autotest1"
    name2 = "autotest2"
    sg_client = MobileRestClient()

    if sync_gateway_version < "2.0":
        pytest.skip('--no-conflicts is enabled and does not work with sg < 2.0 , so skipping the test')

    c = cluster.Cluster(cluster_config)
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)
    c.reset(sg_config_path=sg_config)
    sg1 = c.sync_gateways[0]
    sg2 = c.sync_gateways[1]

    # Setting revs_limit to sg1
    revs_limit1 = 30
    temp_cluster_config = copy_to_temp_conf(cluster_config, sg_mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'revs_limit', revs_limit1, property_name_check=False)
    status = sg1.restart(config=sg_config, cluster_config=temp_cluster_config)
    assert status == 0, "Syncgateway did not start after changing the revs_limit on sg1"

    # Setting revs_limit to sg2
    revs_limit2 = 25
    temp_cluster_config = copy_to_temp_conf(cluster_config, sg_mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'revs_limit', revs_limit2, property_name_check=False)
    status = sg2.restart(config=sg_config, cluster_config=temp_cluster_config)
    assert status == 0, "Syncgateway did not start after changing the revs_limit on sg2"

    admin = Admin(sg1)
    admin.admin_url = sg1.url

    sg1_ip = sg1.ip
    sg2_ip = sg2.ip
    sg1_url = sg1.url
    sg1_admin_url = sg1.admin.admin_url
    sg2_url = sg2.url
    sg2_admin_url = sg2.admin.admin_url
    if sg_ssl:
        protocol = "wss"
    sg1_blip_url = "{}://{}:4984/{}".format(protocol, sg1_ip, sg_db1)
    sg2_blip_url = "{}://{}:4984/{}".format(protocol, sg2_ip, sg_db2)

    sg_client.create_user(sg1_admin_url, sg_db1, name1, password="password", channels=channels1)
    sg_client.create_user(sg2_admin_url, sg_db2, name2, password="password", channels=channels2)
    # Create bulk doc json
    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db2 = setup_customized_teardown_test["cbl_db2"]
    db.create_bulk_docs(num_of_docs, "Replication1", db=cbl_db1, channels=channels1)
    db.create_bulk_docs(num_of_docs, "Replication2", db=cbl_db2, channels=channels2)

    # 2. Do push replication to two SGS(each DB to each SG)
    replicator = Replication(base_url)
    cookie, session_id = sg_client.create_session(sg1_admin_url, sg_db1, name1)
    session1 = cookie, session_id
    authenticator = Authenticator(base_url)
    replicator_authenticator1 = authenticator.authentication(session_id, cookie, authentication_type="session")
    cookie, session_id = sg_client.create_session(sg2_admin_url, sg_db2, name2)
    session2 = cookie, session_id
    replicator_authenticator2 = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl1 = replicator.configure_and_replicate(
        source_db=cbl_db1, replicator_authenticator=replicator_authenticator1, target_url=sg1_blip_url, replication_type="push")

    repl2 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url, replication_type="push")

    db.update_bulk_docs(cbl_db1, number_of_updates=35)
    db.update_bulk_docs(cbl_db2, number_of_updates=35)

    replicator.wait_until_replicator_idle(repl1)
    replicator.wait_until_replicator_idle(repl2)
    replicator.stop(repl1)
    replicator.stop(repl2)

    # 4. Get docs from sgs and verify revs_limit is maintained
    sg_docs = sg_client.get_all_docs(url=sg1_url, db=sg_db1, auth=session1)
    sg_doc_ids = [doc['id'] for doc in sg_docs["rows"]]
    for doc_id in sg_doc_ids:
        revs = sg_client.get_revs_num_in_history(sg1_url, sg_db1, doc_id, auth=session1)
        assert len(revs) == revs_limit1

    sg_docs = sg_client.get_all_docs(url=sg2_url, db=sg_db2, auth=session2)
    sg_doc_ids = [doc['id'] for doc in sg_docs["rows"]]
    for doc_id in sg_doc_ids:
        revs = sg_client.get_revs_num_in_history(sg2_url, sg_db2, doc_id, auth=session2)
        assert len(revs) == revs_limit2

    # 7. exchange DBs of SG and do push replication.
    repl1 = replicator.configure_and_replicate(
        source_db=cbl_db1, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url, replication_type="push")
    repl2 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator1, target_url=sg1_blip_url, replication_type="push")

    replicator.stop(repl1)
    replicator.stop(repl2)

    # 4. Get docs from sgs and verify revs_limit is maintained after switching sgs
    sg_docs = sg_client.get_all_docs(url=sg1_url, db=sg_db1, auth=session1)
    sg_doc_ids = [doc['id'] for doc in sg_docs["rows"]]
    for doc_id in sg_doc_ids:
        revs = sg_client.get_revs_num_in_history(sg1_url, sg_db1, doc_id, auth=session1)
        assert len(revs) == revs_limit1

    sg_docs = sg_client.get_all_docs(url=sg2_url, db=sg_db2, auth=session2)
    sg_doc_ids = [doc['id'] for doc in sg_docs["rows"]]
    for doc_id in sg_doc_ids:
        revs = sg_client.get_revs_num_in_history(sg2_url, sg_db2, doc_id, auth=session2)
        assert len(revs) == revs_limit2


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("sg_conf_name, num_of_docs", [
    ('listener_tests/multiple_sync_gateways', 10),
    ('listener_tests/multiple_sync_gateways', 100),
    ('listener_tests/multiple_sync_gateways', 1000)
])
def test_multiple_sgs_with_CBLs(params_from_base_test_setup, setup_customized_teardown_test, sg_conf_name, num_of_docs):
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
    sg_db1 = "sg_db1"
    sg_db2 = "sg_db2"
    protocol = "ws"
    sg_mode = params_from_base_test_setup["mode"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    base_url = params_from_base_test_setup["base_url"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    liteserv_platform = params_from_base_test_setup["liteserv_platform"]
    sg_ssl = params_from_base_test_setup["sg_ssl"]

    channels1 = ["Replication1"]
    channels2 = ["Replication2"]
    name1 = "autotest1"
    name2 = "autotest2"
    sg_client = MobileRestClient()

    if sync_gateway_version < "2.0":
        pytest.skip('It does not work with sg < 2.0 , so skipping the test')
    # Modify sync-gateway config to use no-conflicts config

    cluster_config = "{}/multiple_sync_gateways_{}".format(CLUSTER_CONFIGS_DIR, sg_mode)
    c = cluster.Cluster(config=cluster_config)
    sg_config = sync_gateway_config_path_for_mode(sg_conf_name, sg_mode)
    c.reset(sg_config_path=sg_config)
    db = Database(base_url)

    sg1, sg2 = create_sync_gateways(
        cluster_config=cluster_config,
        sg_config_path=sg_config
    )

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

    sg_client.create_user(sg1_admin_url, sg_db1, "autotest1", password="password", channels=channels1)
    sg_client.create_user(sg2_admin_url, sg_db2, "autotest2", password="password", channels=channels2)
    # Create bulk doc json
    cbl_db1 = setup_customized_teardown_test["cbl_db1"]
    cbl_db2 = setup_customized_teardown_test["cbl_db2"]
    db.create_bulk_docs(num_of_docs, "Replication1", db=cbl_db1, channels=channels1)
    cbl_doc_ids1 = db.getDocIds(cbl_db1)
    db.create_bulk_docs(num_of_docs, "Replication2", db=cbl_db2, channels=channels2)
    cbl_doc_ids2 = db.getDocIds(cbl_db2)

    # 2. Do push replication to two SGS(each DB to each SG)
    replicator = Replication(base_url)
    cookie, session_id = sg_client.create_session(sg1_admin_url, sg_db1, name1)
    authenticator = Authenticator(base_url)
    replicator_authenticator1 = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl1 = replicator.configure_and_replicate(
        source_db=cbl_db1, replicator_authenticator=replicator_authenticator1, target_url=sg1_blip_url, replication_type="push")

    cookie, session_id = sg_client.create_session(sg2_admin_url, sg_db2, name2)
    authenticator = Authenticator(base_url)
    replicator_authenticator2 = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl2 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url, replication_type="push")
    replicator.stop(repl1)
    replicator.stop(repl2)

    # 3. exchange DBs of SG and do pull replication.
    repl1 = replicator.configure_and_replicate(
        source_db=cbl_db1, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url, replication_type="pull")
    repl2 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator1, target_url=sg1_blip_url, replication_type="pull")

    replicator.stop(repl1)
    replicator.stop(repl2)

    # 4. stop one of the sg.
    sg1.stop()
    # Add docs on cbl_db2
    db.create_bulk_docs(1, "Replication2-2", db=cbl_db2, channels=channels2)
    # 5. Pull again
    repl1 = replicator.configure_and_replicate(
        source_db=cbl_db1, replicator_authenticator=replicator_authenticator2, target_url=sg2_blip_url, replication_type="pull")
    repl2 = replicator.configure_and_replicate(
        source_db=cbl_db2, replicator_authenticator=replicator_authenticator1, target_url=sg1_blip_url, replication_type="pull", err_check=False)
    replicator.stop(repl1)
    repl2_error = replicator.getError(repl2)
    if liteserv_platform == "xamarin-ios":
        assert "POSIXDomain" in repl2_error
    else:
        assert "POSIXErrorDomain" in repl2_error
    # 6. Verify one CBL DB should be successful as other CBL DB should fail as associated Sg is down
    cblDB1_doc_ids = db.getDocIds(cbl_db1, limit=2000)
    for doc in cbl_doc_ids1:
        assert doc in cblDB1_doc_ids, "cbl_db1 doc does not exist in combined replication cbl_db1"
    for doc in cbl_doc_ids2:
        assert doc in cblDB1_doc_ids, "cbl_db2 doc does not exist in combined replication cbl_db1"
    replicator.stop(repl1)
    replicator.stop(repl2)


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
