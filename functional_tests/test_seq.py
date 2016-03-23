import time

import pytest


from testkit.admin import Admin
from testkit.verify import verify_changes

import testkit.settings
import logging
log = logging.getLogger(testkit.settings.LOGGER)

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

    mode = cluster.reset(config_path=conf)
    admin = Admin(cluster.sync_gateways[0])

    # all users will share docs due to having the same channel
    users = admin.register_bulk_users(target=cluster.sync_gateways[0], db="db", name_prefix="user", number=num_users, password="password", channels=["ABC"])

    for user in users:
        user.add_docs(num_docs, bulk=True)

    for user in users:
        user.update_docs(num_revisions)

    time.sleep(5)

    user_0_changes = users[0].get_changes(since=0)
    doc_seq = user_0_changes["results"][num_docs / 2]["seq"]

    # https://github.com/couchbase/sync_gateway/issues/1475#issuecomment-172426052
    # verify you can issue _changes with since=12313-0::1023.15
    for user in users:
        changes = user.get_changes(since=doc_seq)
        log.info("Trying changes with since={}".format(doc_seq))
        assert(len(changes["results"]) > 0)

        second_to_last_doc_entry_seq = changes["results"][-2]["seq"]
        last_doc_entry_seq = changes["results"][-1]["seq"]

        log.info('Second to last doc "seq": {}'.format(second_to_last_doc_entry_seq))
        log.info('Last doc "seq": {}'.format(last_doc_entry_seq))

        if mode == "distributed_index":
            # Verify last "seq" follows the formate 12313-0, not 12313-0::1023.15
            log.info('Verify that the last "seq" is a plain hashed value')
            assert(len(second_to_last_doc_entry_seq.split("::")) == 2)
            assert(len(last_doc_entry_seq.split("::")) == 1)
        else:
            assert(second_to_last_doc_entry_seq > 0)
            assert(last_doc_entry_seq > 0)

    all_doc_caches = [user.cache for user in users]
    all_docs = {k: v for cache in all_doc_caches for k, v in cache.items()}
    verify_changes(users, expected_num_docs=num_users * num_docs, expected_num_revisions=num_revisions, expected_docs=all_docs)

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)




