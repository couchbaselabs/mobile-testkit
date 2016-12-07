import time

import pytest

from libraries.testkit.admin import Admin
from libraries.testkit.cluster import Cluster
from libraries.testkit.verify import verify_changes

from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.utils import log_info


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.parametrize("sg_conf_name", [
    "sync_gateway_default_functional_tests",
])
def test_multiple_users_multiple_channels(params_from_base_test_setup, sg_conf_name):

    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'multiple_users_multiple_channels'")
    log_info("cluster_conf: {}".format(cluster_conf))
    log_info("conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    num_docs_seth = 1000
    num_docs_adam = 2000
    num_docs_traun = 3000

    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])

    seth = admin.register_user(target=sgs[0], db="db", name="seth", password="password", channels=["ABC"])
    adam = admin.register_user(target=sgs[0], db="db", name="adam", password="password", channels=["NBC", "CBS"])
    traun = admin.register_user(target=sgs[0], db="db", name="traun", password="password", channels=["ABC", "NBC", "CBS"])

    # TODO use bulk docs
    seth.add_docs(num_docs_seth)  # ABC
    adam.add_docs(num_docs_adam)  # NBC, CBS
    traun.add_docs(num_docs_traun)  # ABC, NBC, CBS

    assert len(seth.cache) == num_docs_seth
    assert len(adam.cache) == num_docs_adam
    assert len(traun.cache) == num_docs_traun

    # discuss appropriate time with team
    time.sleep(10)

    # Seth should get docs from seth + traun
    seth_subset = [seth.cache, traun.cache]
    seth_expected_docs = {k: v for cache in seth_subset for k, v in cache.items()}
    verify_changes([seth], expected_num_docs=num_docs_seth + num_docs_traun, expected_num_revisions=0, expected_docs=seth_expected_docs)

    # Adam should get docs from adam + traun
    adam_subset = [adam.cache, traun.cache]
    adam_expected_docs = {k: v for cache in adam_subset for k, v in cache.items()}
    verify_changes([adam], expected_num_docs=num_docs_adam + num_docs_traun, expected_num_revisions=0, expected_docs=adam_expected_docs)

    # Traun should get docs from seth + adam + traun
    traun_subset = [seth.cache, adam.cache, traun.cache]
    traun_expected_docs = {k: v for cache in traun_subset for k, v in cache.items()}
    verify_changes([traun], expected_num_docs=num_docs_seth + num_docs_adam + num_docs_traun, expected_num_revisions=0, expected_docs=traun_expected_docs)


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.parametrize("sg_conf_name", [
    "sync_gateway_default_functional_tests",
])
def test_muliple_users_single_channel(params_from_base_test_setup, sg_conf_name):

    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'muliple_users_single_channel'")
    log_info("cluster_conf: {}".format(cluster_conf))
    log_info("conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    sgs = cluster.sync_gateways

    num_docs_seth = 1000
    num_docs_adam = 2000
    num_docs_traun = 3000

    admin = Admin(sgs[0])

    seth = admin.register_user(target=sgs[0], db="db", name="seth", password="password", channels=["ABC"])
    adam = admin.register_user(target=sgs[0], db="db", name="adam", password="password", channels=["ABC"])
    traun = admin.register_user(target=sgs[0], db="db", name="traun", password="password", channels=["ABC"])

    seth.add_docs(num_docs_seth)  # ABC
    adam.add_docs(num_docs_adam, bulk=True)  # ABC
    traun.add_docs(num_docs_traun, bulk=True)  # ABC

    assert len(seth.cache) == num_docs_seth
    assert len(adam.cache) == num_docs_adam
    assert len(traun.cache) == num_docs_traun

    # discuss appropriate time with team
    time.sleep(10)

    # Each user should get all docs from all users
    all_caches = [seth.cache, adam.cache, traun.cache]
    all_docs = {k: v for cache in all_caches for k, v in cache.items()}

    verify_changes([seth, adam, traun], expected_num_docs=num_docs_seth + num_docs_adam + num_docs_traun, expected_num_revisions=0, expected_docs=all_docs)


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.parametrize("sg_conf_name", [
    "sync_gateway_default_functional_tests",
])
def test_single_user_multiple_channels(params_from_base_test_setup, sg_conf_name):

    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'single_user_multiple_channels'")
    log_info("cluster_conf: {}".format(cluster_conf))
    log_info("conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    start = time.time()
    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])
    seth = admin.register_user(target=sgs[0], db="db", name="seth", password="password", channels=["ABC", "CBS", "NBC", "FOX"])

    # Round robin
    count = 1
    num_sgs = len(cluster.sync_gateways)
    while count <= 5:
        seth.add_docs(1000, bulk=True)
        seth.target = cluster.sync_gateways[count % num_sgs]
        count += 1

    log_info(seth)

    time.sleep(10)

    verify_changes(users=[seth], expected_num_docs=5000, expected_num_revisions=0, expected_docs=seth.cache)

    end = time.time()
    log_info("TIME:{}s".format(end - start))


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.parametrize("sg_conf_name", [
    "sync_gateway_default_functional_tests",
])
def test_single_user_single_channel(params_from_base_test_setup, sg_conf_name):

    cluster_conf = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Running 'single_user_single_channel'")
    log_info("cluster_conf: {}".format(cluster_conf))
    log_info("conf: {}".format(sg_conf))

    cluster = Cluster(config=cluster_conf)
    cluster.reset(sg_config_path=sg_conf)

    sgs = cluster.sync_gateways

    num_seth_docs = 7000
    num_cbs_docs = 3000

    admin = Admin(sgs[0])
    seth = admin.register_user(target=sgs[0], db="db", name="seth", password="password", channels=["ABC"])
    cbs_user = admin.register_user(target=sgs[0], db="db", name="cbs_user", password="password", channels=["CBS"])
    admin_user = admin.register_user(target=sgs[0], db="db", name="admin", password="password", channels=["ABC", "CBS"])

    seth.add_docs(num_seth_docs)
    cbs_user.add_docs(num_cbs_docs)

    assert len(seth.cache) == num_seth_docs
    assert len(cbs_user.cache) == num_cbs_docs
    assert len(admin_user.cache) == 0

    time.sleep(10)

    verify_changes([seth], expected_num_docs=num_seth_docs, expected_num_revisions=0, expected_docs=seth.cache)
    verify_changes([cbs_user], expected_num_docs=num_cbs_docs, expected_num_revisions=0, expected_docs=cbs_user.cache)

    all_doc_caches = [seth.cache, cbs_user.cache]
    all_docs = {k: v for cache in all_doc_caches for k, v in cache.items()}
    verify_changes([admin_user], expected_num_docs=num_cbs_docs + num_seth_docs, expected_num_revisions=0, expected_docs=all_docs)
