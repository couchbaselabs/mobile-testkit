import concurrent.futures

import pytest

from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient
from keywords.ChangesTracker import ChangesTracker
from keywords.ClusterKeywords import ClusterKeywords
from keywords.SyncGateway import sync_gateway_config_path_for_mode


@pytest.mark.topospecific
@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.nginx
@pytest.mark.changes
def test_load_balance_sanity(params_from_base_test_setup):

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf_name = "sync_gateway_default_functional_tests"
    sg_conf_path = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cluster_util = ClusterKeywords()
    cluster_util.reset_cluster(
        cluster_config=cluster_config,
        sync_gateway_config=sg_conf_path
    )

    topology = cluster_util.get_cluster_topology(cluster_config)
    admin_sg_one = topology["sync_gateways"][0]["admin"]
    lb_url = topology["load_balancers"][0]

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
