import time

import pytest


from lib.admin import Admin
from lib.verify import verify_changes

import lib.settings
import logging
log = logging.getLogger(lib.settings.LOGGER)

from fixtures import cluster


@pytest.mark.distributed_index
@pytest.mark.sanity
@pytest.mark.parametrize(
        "conf, num_users, num_docs, num_revisions", [
            ("sync_gateway_default_functional_tests_di.json", 10, 500, 1),
            ("sync_gateway_default_functional_tests_cc.json", 10, 500, 1)
        ],
        ids=["DI-1", "CC-2"]
)
def test_seq(cluster, conf, num_users, num_docs, num_revisions):

    log.info("conf: {}".format(conf))
    log.info("num_users: {}".format(num_users))
    log.info("num_docs: {}".format(num_docs))
    log.info("num_revisions: {}".format(num_revisions))

    mode = cluster.reset(config=conf)
    admin = Admin(cluster.sync_gateways[0])

    # all users will share docs due to having the same channel
    users = admin.register_bulk_users(target=cluster.sync_gateways[0], db="db", name_prefix="user", number=num_users, password="password", channels=["ABC"])

    for user in users:
        user.add_docs(num_docs, bulk=True)

    for user in users:
        user.update_docs(num_revisions)

    time.sleep(5)

    user_0_changes = users[0].get_changes(since=0)
    doc_seq = user_0_changes["results"][250]["seq"]
    log.info("Trying changes with since={}".format(doc_seq))

    # https://github.com/couchbase/sync_gateway/issues/1475#issuecomment-172426052
    for user in users:
        changes = user.get_changes(since=doc_seq)
        assert(len(changes["results"]) > 0)

    all_doc_caches = [user.cache for user in users]
    all_docs = {k: v for cache in all_doc_caches for k, v in cache.items()}
    verify_changes(users, expected_num_docs=num_users * num_docs, expected_num_revisions=num_revisions, expected_docs=all_docs)

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)




