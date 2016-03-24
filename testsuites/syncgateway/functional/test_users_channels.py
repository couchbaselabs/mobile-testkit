import time

from testkit.admin import Admin
from testkit.cluster import Cluster
from testkit.verify import verify_changes

import testkit.settings
import logging
log = logging.getLogger(testkit.settings.LOGGER)


def test_multiple_users_multiple_channels(conf):

    log.info("conf: {}".format(conf))

    cluster = Cluster()
    mode = cluster.reset(config_path=conf)

    # TODO Parametrize
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

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)


def test_muliple_users_single_channel(conf):

    log.info("conf: {}".format(conf))

    cluster = Cluster()
    mode = cluster.reset(config_path=conf)

    sgs = cluster.sync_gateways

    # TODO parametrize
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

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)


def test_single_user_multiple_channels(conf):

    log.info("conf: {}".format(conf))

    cluster = Cluster()
    mode = cluster.reset(config_path=conf)

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

    log.info(seth)

    time.sleep(10)

    verify_changes(users=[seth], expected_num_docs=5000, expected_num_revisions=0, expected_docs=seth.cache)

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)

    end = time.time()
    log.info("TIME:{}s".format(end - start))


def test_single_user_single_channel(conf):

    log.info("conf: {}".format(conf))

    cluster = Cluster()
    mode = cluster.reset(config_path=conf)

    sgs = cluster.sync_gateways

    # TODO Parametrize
    num_seth_docs = 7000
    num_admin_docs = 3000

    admin = Admin(sgs[0])
    seth = admin.register_user(target=sgs[0], db="db", name="seth", password="password", channels=["ABC"])
    admin_user = admin.register_user(target=sgs[0], db="db", name="admin", password="password", channels=["*"])

    seth.add_docs(num_seth_docs)
    admin_user.add_docs(num_admin_docs)

    assert len(seth.cache) == num_seth_docs
    assert len(admin_user.cache) == num_admin_docs

    time.sleep(10)

    verify_changes([seth], expected_num_docs=num_seth_docs, expected_num_revisions=0, expected_docs=seth.cache)

    all_doc_caches = [seth.cache, admin_user.cache]
    all_docs = {k: v for cache in all_doc_caches for k, v in cache.items()}
    verify_changes([admin_user], expected_num_docs=num_seth_docs + num_admin_docs, expected_num_revisions=0, expected_docs=all_docs)

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)



