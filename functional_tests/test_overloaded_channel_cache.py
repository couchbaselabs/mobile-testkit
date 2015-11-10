import time
from lib.admin import Admin
import pytest
import concurrent

from cluster_setup import cluster

@pytest.mark.sanity
def test_1(cluster):

    cluster.reset("sync_gateway_channel_cache.json")

    start = time.time()
    target_sg = cluster.sync_gateways[0]

    admin = Admin(target_sg)

    # Add 1000 users
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        count = 0
        futures = []
        while count < 1000:
            user_name = "user_{}".format(count)
            futures.append(executor.submit(admin.register_user, target_sg, "db", user_name, "password", ["ABC"]))
            count += 1

        for f in concurrent.futures.as_completed(futures):
            try:
                print(">>> user added")
            except Exception as e:
                print("Error adding user: {}".format(e))

      #  admin.register_user(target=target_sg, db="db", name=user_name, password="password", channels=["ABC"])

    users = admin.get_users()

    assert len(users) == 1000

    end = time.time()
    print("TIME:{}s".format(end - start))

    doc_pusher = users["user_0"]
    doc_pusher.add_docs(5000, bulk=True, uuid_names=True)

    # Get changes for each user
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        count = 0
        futures = []
        while count < 1000:
            user_name = "user_{}".format(count)
            user = users[user_name]
            print(">>> {} /_changes".format(user_name))
            futures.append(executor.submit(user.get_changes()))
            count += 1

        for f in concurrent.futures.as_completed(futures):
            try:
                print(">>> Got user changes")
            except Exception as e:
                print("Error adding user: {}".format(e))

    end = time.time()
    print("TIME:{}s".format(end - start))

