import time
from lib.admin import Admin
from lib.verify import verify_changes
import pytest
import concurrent
import concurrent.futures
import requests

from fixtures import cluster

@pytest.mark.regression
@pytest.mark.parametrize("user_channels, filter, limit", [
    ("*", True, 50),
    ("ABC", False, 50)
])
def test_overloaded_channel_cache(cluster, user_channels, filter, limit):

    cluster.reset(config="sync_gateway_channel_cache.json")

    target_sg = cluster.sync_gateways[0]

    admin = Admin(target_sg)

    users = admin.register_bulk_users(target_sg, "db", "user", 1000, "password", [user_channels])
    assert len(users) == 1000

    doc_pusher = admin.register_user(target_sg, "db", "abc_doc_pusher", "password", ["ABC"])
    doc_pusher.add_docs(5000, bulk=True)

    start = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:

        changes_requests = []
        errors = []

        for user in users:
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

        # Sanity check that a subset of users have _changes feed intact
        for i in range(10):
            verify_changes(users[i], expected_num_docs=5000, expected_num_revisions=0, expected_docs=doc_pusher.cache)

        # Get sync_gateway expvars
        resp = requests.get(url="http://{}:4985/_expvar".format(target_sg.ip))
        resp.raise_for_status()
        resp_obj = resp.json()

        # If number of view queries == 0 the key will not exist in the expvars
        assert("view_queries" not in resp_obj["syncGateway_changeCache"])
