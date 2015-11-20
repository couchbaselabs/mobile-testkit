import time

import pytest
import concurrent.futures

from lib.admin import Admin
from lib.verify import verify_changes

from fixtures import cluster

@pytest.mark.distributed_index
@pytest.mark.extendedsanity
def test_dcp_reshard_sync_gateway_goes_down(cluster):

    cluster.reset(config="sync_gateway_default_functional_tests.json")

    admin = Admin(cluster.sync_gateways[2])

    traun = admin.register_user(target=cluster.sync_gateways[3], db="db", name="traun", password="password", channels=["ABC", "NBC", "CBS"])
    seth = admin.register_user(target=cluster.sync_gateways[2], db="db", name="seth", password="password", channels=["FOX"])

    print(">> Users added")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:

        futures = dict()

        # take down a sync_gateway
        futures[executor.submit(cluster.sync_gateways[0].stop)] = "Sg Stopped!"

        print(">>> Adding Seth docs")  # FOX
        futures[executor.submit(seth.add_docs, 8000, uuid_names=True)] = "seth"

        print(">>> Adding Traun docs")  # ABC, NBC, CBS
        futures[executor.submit(traun.add_docs, 2000, uuid_names=True, bulk=True)] = "traun"

        for future in concurrent.futures.as_completed(futures):
            try:
                user = futures[future]
                test = future.result()
                print("{} Completed:".format(user))
            except Exception as e:
                print("Exception thrown while adding docs: {}".format(e))
            else:
                print "Docs added!!"

    # TODO better way to do this
    time.sleep(10)

    verify_changes([traun], expected_num_docs=8001, expected_num_updates=0, expected_docs=traun.cache)
    verify_changes([seth], expected_num_docs=1999, expected_num_updates=0, expected_docs=seth.cache)


@pytest.mark.distributed_index
@pytest.mark.extendedsanity
def test_dcp_reshard_sync_gateway_comes_up(cluster):

    cluster.reset(config="sync_gateway_default_functional_tests.json")
    cluster.sync_gateways[0].stop()

    admin = Admin(cluster.sync_gateways[1])

    traun = admin.register_user(target=cluster.sync_gateways[3], db="db", name="traun", password="password", channels=["ABC", "NBC", "CBS"])
    seth = admin.register_user(target=cluster.sync_gateways[2], db="db", name="seth", password="password", channels=["FOX"])

    print(">> Users added")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:

        futures = dict()

        # Bring up a sync_gateway
        futures[executor.submit(cluster.sync_gateways[0].start, "sync_gateway_default_functional_tests.json")] = "Startup"

        time.sleep(20)

        print(">>> Adding Traun docs")  # ABC, NBC, CBS
        futures[executor.submit(traun.add_docs, 6000, uuid_names=True)] = "traun"

        print(">>> Adding Seth docs")  # FOX
        futures[executor.submit(seth.add_docs, 4000, uuid_names=True)] = "seth"

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
    traun.verify_ids_from_changes(6000, expected_traun_ids)

    expected_seth_ids = seth.cache.keys()
    seth.verify_ids_from_changes(4000, expected_seth_ids)


