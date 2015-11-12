import time

import pytest
import concurrent.futures

from lib.admin import Admin

from cluster_setup import cluster

@pytest.mark.extendedsanity
def test_dcp_reshard(cluster):

    cluster.reset("sync_gateway_default.json")

    start = time.time()

    admin = Admin(cluster.sync_gateways[2])
    admin.register_user(target=cluster.sync_gateways[3], db="db", name="traun", password="password", channels=["ABC", "NBC", "CBS"])
    admin.register_user(target=cluster.sync_gateways[2], db="db", name="seth", password="password", channels=["FOX"])
    users = admin.get_users()

    traun = users["traun"]
    seth = users["seth"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:

        futures = dict()

        print(">>> Adding Traun docs")  # ABC, NBC, CBS
        futures[executor.submit(traun.add_docs, 8001, True, True)] = "traun"

        print(">>> Adding Seth docs")  # FOX
        futures[executor.submit(seth.add_docs, 1999, True)] = "seth"

        # take down a sync_gateway
        time.sleep(7)
        cluster.sync_gateways[0].stop()

        for future in concurrent.futures.as_completed(futures):
            try:
                user = futures[future]
                print("{} Completed:".format(user))
            except Exception as e:
                print("Exception thrown while adding docs: {}".format(e))
            else:
                print "Docs added!!"

    # TODO better way to do this
    time.sleep(10)

    expected_traun_ids = traun.cache.keys()
    traun.verify_ids_from_changes(expected_traun_ids)

    expected_seth_ids = seth.cache.keys()
    seth.verify_ids_from_changes(expected_seth_ids)

    total_time = time.time() - start

    print("TIME: {}".format(total_time))
