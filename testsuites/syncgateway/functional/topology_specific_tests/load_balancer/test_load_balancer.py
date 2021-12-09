import concurrent.futures
import pytest
import time

from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.ChangesTracker import ChangesTracker
from keywords.ClusterKeywords import ClusterKeywords
from keywords.SyncGateway import sync_gateway_config_path_for_mode, create_docs_via_sdk
from libraries.testkit import cluster
from libraries.testkit.cluster import Cluster


@pytest.mark.topospecific
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.nginx
@pytest.mark.changes
@pytest.mark.session
@pytest.mark.channel
@pytest.mark.oscertify
def test_load_balance_sanity(params_from_base_test_setup):

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sg_platform = params_from_base_test_setup["sg_platform"]

    sg_conf_name = "sync_gateway_default_functional_tests"
    sg_conf_path = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cluster_util = ClusterKeywords(cluster_config)
    cluster_util.reset_cluster(
        cluster_config=cluster_config,
        sync_gateway_config=sg_conf_path
    )

    topology = cluster_util.get_cluster_topology(cluster_config)
    admin_sg_one = topology["sync_gateways"][0]["admin"]
    lb_url = "{}:4984".format(topology["load_balancers"][0])

    sg_db = "db"
    num_docs = 1000
    sg_user_name = "seth"
    sg_user_password = "password"
    channels = ["ABC", "CBS"]

    client = MobileRestClient()
    user = client.create_user(admin_sg_one, sg_db, sg_user_name, sg_user_password, channels=channels)
    session = client.create_session(admin_sg_one, sg_db, sg_user_name)

    log_info(user)
    log_info(session)

    log_info("Adding docs to the load balancer ...")
    ct = ChangesTracker(url=lb_url, db=sg_db, auth=session)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        log_info("Starting ...")
        if "macos" in sg_platform:
            ct_task = executor.submit(ct.start, timeout=180000)
        else:
            ct_task = executor.submit(ct.start)
        log_info("Adding docs ...")
        docs = client.add_docs(lb_url, sg_db, num_docs, "test_doc", channels=channels, auth=session)
        assert len(docs) == num_docs

        log_info("Adding docs done")
        wait_for_changes = executor.submit(ct.wait_until, docs)

        if wait_for_changes.result():
            log_info("Stopping ...")
            log_info("Found all docs ...")
            executor.submit(ct.stop)
            ct_task.result()
        else:
            executor.submit(ct.stop)
            ct_task.result()
            raise Exception("Could not find all changes in feed before timeout!!")


@pytest.mark.topospecific
@pytest.mark.syncgateway
@pytest.mark.nginx
def test_sgw_down_with_load_balancer(params_from_base_test_setup, sgw_down_with_load_balancer_teardown):
    """
    @summary :
    1. Have 2 SGWs having load balancer with shared_bucket_access=true and have CBS set up
    2. Create docs in CBS in one thread.
    3. Bring down one SGW node in 2nd thread
    4. Continue to create docs from #2.
    5. stop thread one which stops creating docs.
    6. Try to retrieve docs using changes API
        a . Retry changes API until all changes show up or timeout happens
    7. All expected changes should appear
    """

    cluster_config = sgw_down_with_load_balancer_teardown["cluster_config"]
    sg1 = sgw_down_with_load_balancer_teardown["sg1"]
    sg_conf_path = sgw_down_with_load_balancer_teardown["sg_conf_path"]
    sg_ce = params_from_base_test_setup["sg_ce"]

    if sg_ce:
        pytest.skip('--sg-ce is enabled. This test runs only on enterprise edition of sgw')
    # 1. Have 2 SGWs having load balancer with shared_bucket_access=true and have CBS set up
    cluster_utils = ClusterKeywords(cluster_config)
    cluster_topology = cluster_utils.get_cluster_topology(cluster_config)
    cluster_utils.reset_cluster(cluster_config=cluster_config, sync_gateway_config=sg_conf_path)

    topology = cluster_utils.get_cluster_topology(cluster_config)
    lb_url = "{}:4985".format(topology["load_balancers"][0])

    sg_db = "db"
    num_docs = 100
    bucket_name = 'data-bucket'

    client = MobileRestClient()
    cbs_url = cluster_topology['couchbase_servers'][0]
    cbs_cluster = Cluster(config=cluster_config)

    sdk_docs, sdk_client = create_docs_via_sdk(cbs_url, cbs_cluster, bucket_name, num_docs)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        log_info("Starting ...")
        create_docs_task = executor.submit(sdk_client.upsert_multi, sdk_docs)

        # 3. Bring down one SGW node in 2nd thread
        sg_stop_task = executor.submit(sg1.stop)
        sg_stop_task.result()
        # 4. Continue to create docs from #2.
        # 5. stop thread one which stops creating docs.
        create_docs_task.result()

    # 6. Try to retrieve docs using changes API
    #    a . Retry changes API until all changes show up or timeout happens
    # 7. All expected changes should appear
    retries = 0
    while retries < 30:
        changes = client.get_changes(url=lb_url, db=sg_db, auth=None, since=0)
        if len(changes["results"]) == num_docs:
            break
        retries = retries + 1
        time.sleep(2)
    assert len(changes["results"]) == num_docs, "results in changes did not match with num of docs"


@pytest.fixture(scope='function')
def sgw_down_with_load_balancer_teardown(params_from_base_test_setup):

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    c = cluster.Cluster(config=cluster_config)
    sg1 = c.sync_gateways[0]
    sg_conf_name = "xattrs/no_import"
    sg_conf_path = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    yield{
        "cluster_config": cluster_config,
        "sg1": sg1,
        "sg_conf_path": sg_conf_path
    }

    sg1.start(sg_conf_path)
