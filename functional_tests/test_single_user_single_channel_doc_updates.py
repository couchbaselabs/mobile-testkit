import time
import pytest
from lib.user import User
from lib.admin import Admin
from lib.verify import verify_changes
from fixtures import cluster
import pytest

import lib.settings
import logging
log = logging.getLogger(lib.settings.LOGGER)

# Scenario-2:
# Single User Single Channel: Create Unique docs and update docs verify all num docs present in changes feed.
# Verify all revisions in changes feed
# https://docs.google.com/spreadsheets/d/1nlba3SsWagDrnAep3rDZHXHIDmRH_FFDeTaYJms_55k/edit#gid=598127796

@pytest.mark.sanity
@pytest.mark.distributed_index
@pytest.mark.parametrize(
        "conf, num_docs, num_revisions", [
            ("sync_gateway_default_functional_tests_di.json", 100, 100),
            ("sync_gateway_default_functional_tests_cc.json", 100, 100)
        ],
        ids=["DI-1", "CC-2"]
)
def test_single_user_single_channel_doc_updates(cluster, conf, num_docs, num_revisions):

    log.info("conf: {}".format(conf))
    log.info("num_docs: {}".format(num_docs))
    log.info("num_revisions: {}".format(num_revisions))

    start = time.time()
    mode = cluster.reset(config=conf)
    num_docs = num_docs
    num_revisions = num_revisions
    username = "User-1"
    password = "password"
    channels = ["channel-1"]

    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])

    single_user = admin.register_user(target=sgs[0], db="db", name=username, password=password, channels=channels)

    # Not using bulk docs
    single_user.add_docs(num_docs, name_prefix="test-")

    assert len(single_user.cache) == num_docs

    # let SG catch up with all the changes
    time.sleep(5)

    single_user.update_docs(num_revisions)

    time.sleep(10)

    verify_changes([single_user], expected_num_docs=num_docs, expected_num_revisions=num_revisions, expected_docs=single_user.cache)

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)

    end = time.time()
    print("TIME:{}s".format(end - start))



