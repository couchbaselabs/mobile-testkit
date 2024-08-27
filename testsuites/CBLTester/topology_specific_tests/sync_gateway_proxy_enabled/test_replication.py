import pytest
import time
import uuid

from keywords.MobileRestClient import MobileRestClient
from keywords.utils import log_info
from CBLClient.Database import Database
from CBLClient.Replication import Replication
from CBLClient.Authenticator import Authenticator
from libraries.testkit import cluster
from keywords.constants import RBAC_FULL_ADMIN, NGINX_SGW_USER_NAME, NGINX_SGW_PASSWORD
from keywords.ClusterKeywords import ClusterKeywords
from libraries.provision.install_nginx import install_nginx


@pytest.fixture(scope="function")
def setup_teardown_test(params_from_base_test_setup):
    cbl_db_name = "cbl_db"
    base_url = params_from_base_test_setup["base_url"]
    db = Database(base_url)
    db_config = db.configure()
    log_info("Creating db")
    cbl_db = db.create(cbl_db_name, db_config)

    yield{
        "db": db,
        "cbl_db": cbl_db,
        "cbl_db_name": cbl_db_name
    }

    log_info("Deleting the db")
    db.deleteDB(cbl_db)


@pytest.mark.replication
def test_replication_heartbeat(params_from_base_test_setup):
    """
        @summary:
        This test to verify heartbeat keeps websocket connection alive
        1. create cbl db and add 10 docs on CBL
        2. create 15 docs on SGW
        3. create a push_pull continuous replicator, start replication
        4. verify docs are all replicated
        5. sleep for 90 seconds, then create some docs on cbl
        6. verify if docs are replicated to sync gateway
    """
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_url = params_from_base_test_setup["sg_url"]
    base_url = params_from_base_test_setup["base_url"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    db = params_from_base_test_setup["db"]
    db_config = params_from_base_test_setup["db_config"]
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]

    # Reset nginx with shorter keep_alive frequency config
    from libraries.provision.install_nginx import install_nginx
    install_nginx(cluster_config, True)

    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    sg_db = "db"
    channels = ["ABC"]
    username = "autotest"
    password = "password"

    sg_client = MobileRestClient()
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    sg_client.create_user(sg_admin_url, sg_db, username, password=password, channels=channels, auth=auth)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, username, auth=auth)
    auth_session = cookie, session_id

    heartbeat = '15'
    # 1. create cbl db and add 10 docs on CBL
    cbl_db_name = "heartbeat-" + str(time.time())
    cbl_db = db.create(cbl_db_name, db_config)
    db.create_bulk_docs(db=cbl_db, number=10, id_prefix="cbl_batch_1", channels=channels)

    # 2. create 15 docs on SGW
    sg_client.add_docs(url=sg_url, db=sg_db, number=15, id_prefix="sg_batch_1", channels=channels, auth=auth_session)

    # 3. create a push_pull continuous replicator, start replication
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    if heartbeat == "default":
        repl = replicator.configure_and_replicate(source_db=cbl_db,
                                                  target_url=sg_blip_url,
                                                  continuous=True,
                                                  replicator_authenticator=replicator_authenticator,
                                                  replication_type="pushAndPull")
    else:
        repl = replicator.configure_and_replicate(source_db=cbl_db,
                                                  target_url=sg_blip_url,
                                                  continuous=True,
                                                  replicator_authenticator=replicator_authenticator,
                                                  replication_type="pushAndPull",
                                                  heartbeat=heartbeat)

    # 4. verify docs are all replicated
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True, auth=auth)["rows"]
    log_info("count of sg_docs = {}".format(len(sg_docs)))
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_db_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    log_info("count of cbl_db_docs = {}".format(len(cbl_db_docs)))
    assert len(sg_docs) == len(cbl_db_docs), "docs are not replicated correctly"

    # 5. sleep for 90 seconds, then create some docs on cbl
    time.sleep(90)
    db.create_bulk_docs(db=cbl_db, number=9, id_prefix="cbl_batch_2", channels=channels)

    # 6. wait for 20 seconds, verify if docs are replicated to sync gateway
    time.sleep(10)
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True, auth=auth)["rows"]
    log_info("count of sg_docs = {}".format(len(sg_docs)))
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_db_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    log_info("count of cbl_db_docs = {}".format(len(cbl_db_docs)))

    assert len(sg_docs) == len(cbl_db_docs)
    replicator.stop(repl)


def test_proxy_authentication(params_from_base_test_setup):
    """
    @summary: Testing that proxy authetication works. The test does not check data validity,
    just that the repliacation works with Proxy authentication
    1. Start nginx with basic authentication
    2. Configure replication with Proxy authentication and start it
    """
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    base_url = params_from_base_test_setup["base_url"]
    db = params_from_base_test_setup["db"]
    db_config = params_from_base_test_setup["db_config"]
    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    # Reset cluster to ensure no data in system
    # c = cluster.Cluster(config=cluster_config)
    cluster_util = ClusterKeywords(cluster_config)
    topology = cluster_util.get_cluster_topology(cluster_config)
    proxy_url = topology["load_balancers"][0]
    proxy_url = proxy_url.replace("http", "ws")
    topology = cluster_util.get_cluster_topology(cluster_config, lb_enable=False)
    sg = topology["sync_gateways"][0]
    sg_admin_url = sg["admin"]
    sg_url = sg["public"]
    random_suffix = str(uuid.uuid4())[:8]
    sg_db = "db"
    channels = ["ABC"]
    # sgw_user = "proxy-auth-test1"
    # sgw_password = "password"
    # data = {"bucket": "data-bucket-1",  "num_index_replicas": 0}

    # c_cluster = cluster.Cluster(config=cluster_config)
    # admin_client = Admin(c_cluster.sync_gateways[0])
    # c.reset(sg_config_path=sg_config)
    # admin_client.create_db(sg_db, data)

    sgw_user = NGINX_SGW_USER_NAME
    sgw_password = NGINX_SGW_PASSWORD
 
    proxy_username = NGINX_SGW_USER_NAME
    proxy_password = NGINX_SGW_PASSWORD

    cbl_db_name = "proxyAuth-" + str(random_suffix)
    cbl_db = db.create(cbl_db_name, db_config)
 
    # 1. Start nginx with basic authentication. If base_url, nginx will be installed as a proxy, rather than a 
    # reverse prox (will use nginx_proxy.conf.j2). 
    # TODO: change this mechanism for something more obvious similar to: "reverse_preoxy = False, base_url=base_url"
    #
    install_nginx(cluster_config, True, userName=proxy_username, password=proxy_password, base_url=base_url)
    # install_nginx(cluster_config, True, username=username, password=password)
    sg_client = MobileRestClient()
    auth = need_sgw_admin_auth and (RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']) or None
    sg_client.create_user(sg_admin_url, sg_db, sgw_user, password=sgw_password, channels=channels, auth=auth)
 
    # 2. Configure replication with Proxy authentication and start it
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    print("++++++++++++++++++++++++++++++++++sg_blip_url=" + str(sg_blip_url))
    replicator_authenticator = authenticator.authentication(username=sgw_user, password=sgw_password, authentication_type="basic")
    repl_config = replicator.configure(source_db=cbl_db,
                                       # target_url=proxy_url + ":8080",
                                       target_url=sg_blip_url,
                                       continuous=True,
                                       replicator_authenticator=replicator_authenticator,
                                       replication_type="pushAndPull"
                                      )
    proxy_authenticator = authenticator.authentication(username=proxy_username, password=proxy_password, authentication_type="proxy")
    # repl_config = replicator.setProxyAuthenticator(repl_config, proxy_authenticator)
    print("*************************************repl_config" + str(repl_config))
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl, err_check=False)
    replicator.stop(repl)
