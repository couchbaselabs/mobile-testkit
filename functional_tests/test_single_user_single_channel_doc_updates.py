import time

from lib.user import User
from lib.admin import Admin

from fixtures import cluster

# Scenario-2:
# Single User Single Channel: Create Unique docs and update docs verify all num docs present in changes feed.
# Verify all revisions in changes feed
# https://docs.google.com/spreadsheets/d/1nlba3SsWagDrnAep3rDZHXHIDmRH_FFDeTaYJms_55k/edit#gid=598127796

def test_update_docs_multiple_users_multiple_channels(cluster):

    start = time.time()
    cluster.reset(config="sync_gateway_default_functional_tests.json")
    num_docs = 100
    num_revisions = 10
    username = "User-1"
    password = "password"
    channels = ["channel-1"]

    sgs = cluster.sync_gateways

    admin = Admin(sgs[0])

    admin.register_user(target=sgs[0], db="db", name=username, password=password, channels=channels)

    users = admin.get_users()

    single_user = users[username]
    assert len(users) == 1

    # Not using bulk docs
    single_user.add_docs(num_docs)

    assert len(single_user.cache) == num_docs

    # let SG catch up with all the changes
    time.sleep(5)

    single_user.update_docs(num_revisions)

    time.sleep(10)

    doc_name_pattern = "test-"
    status = single_user.verify_all_docs_from_changes_feed(num_revisions, doc_name_pattern)
    assert status

    end = time.time()
    print("TIME:{}s".format(end - start))



