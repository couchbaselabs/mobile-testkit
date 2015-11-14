import time
from lib.admin import Admin
import pytest
import concurrent
import concurrent.futures

from fixtures import cluster

@pytest.mark.regression
@pytest.mark.parametrize("user_channels, filter, limit", [
    ("*", True, 50),
    ("ABC", False, 50)
])
def test_1(cluster, user_channels, filter, limit):

    cluster.reset("sync_gateway_channel_cache.json")

    target_sg = cluster.sync_gateways[0]

    admin = Admin(target_sg)

    # Add 1000 users
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:

        add_user_requests = {executor.submit(admin.register_user, target_sg, "db", "user_{}".format(i), "password", [user_channels]): "user_{}".format(i) for i in range(1000)}

        for future in concurrent.futures.as_completed(add_user_requests):
            try:
                user = add_user_requests[future]
            except Exception as e:
                print("Error adding user: {}".format(e))

    admin.register_user(target_sg, "db", "abc_doc_pusher", "password", ["ABC"])

    users = admin.get_users()
    assert len(users) == 1001

    doc_pusher = users["abc_doc_pusher"]
    doc_pusher.add_docs(5000, bulk=True, uuid_names=True)

    start = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:

        changes_requests = []
        errors = []

        for i in range(1000):
            user = users["user_{}".format(i)]
            if filter and limit is not None:
                changes_requests.append(executor.submit(user.get_changes, since=0, limit=limit, filter="sync_gateway/bychannel", channels=["ABC"]))
            elif filter and limit is None:
                changes_requests.append(executor.submit(user.get_changes, filter="sync_gateway/bychannel", channels=["ABC"]))
            elif not filter and limit is not None:
                changes_requests.append(executor.submit(user.get_changes, limit=limit))
            elif not filter and limit is None:
                changes_requests.append(executor.submit(user.get_changes))

        for future in concurrent.futures.as_completed(changes_requests):
            try:
                changes = future.result()
                if limit is not None:
                    assert len(changes["results"]) == 50
                else:
                    assert len(changes["results"]) == 5001
            except Exception as e:
                errors.append(e)
                print("Error getting _changes: {}".format(e))

        # changes feed should all be successful
        print(len(errors))
        assert len(errors) == 0

        if limit is not None:
            # HACK: Should be less than a minute unless blocking on view calls
            end = time.time()
            time_for_users_to_get_all_changes = end - start
            print("Time for users to get all changes: {}".format(time_for_users_to_get_all_changes))
            assert time_for_users_to_get_all_changes < 60

        for i in range(10):
            user = users["user_{}".format(i)]
            doc_pusher = users["abc_doc_pusher"]

            user.verify_ids_from_changes(doc_pusher.cache.keys())

        #TODO: Autoverify 4985/db/_expvar view queries
