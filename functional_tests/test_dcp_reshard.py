import time

import pytest
import concurrent.futures

from lib.admin import Admin
from lib.verify import verify_changes
import lib.settings
import logging
log = logging.getLogger(lib.settings.LOGGER)

from fixtures import cluster


@pytest.mark.distributed_index
@pytest.mark.extendedsanity
@pytest.mark.parametrize(
        "conf", [
            ("sync_gateway_default_functional_tests_di.json"),
        ],
        ids=["DI-1"]
)
def test_dcp_reshard_sync_gateway_goes_down(cluster, conf):

    log.info("conf: {}".format(conf))

    cluster.reset(config=conf)

    admin = Admin(cluster.sync_gateways[2])

    traun = admin.register_user(target=cluster.sync_gateways[1], db="db", name="traun", password="password", channels=["ABC", "NBC", "CBS"])
    seth = admin.register_user(target=cluster.sync_gateways[2], db="db", name="seth", password="password", channels=["FOX"])

    log.info(">> Users added")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:

        futures = dict()

        # take down a sync_gateway
        futures[executor.submit(cluster.sync_gateways[0].stop)] = "sg_down"

        log.info(">>> Adding Seth docs")  # FOX
        futures[executor.submit(seth.add_docs, 8000)] = "seth"

        log.info(">>> Adding Traun docs")  # ABC, NBC, CBS
        futures[executor.submit(traun.add_docs, 2000, bulk=True)] = "traun"

        for future in concurrent.futures.as_completed(futures):
            tag = futures[future]
            log.info("{} Completed:".format(tag))
            if tag == "sg_down":
                # Assert takedown was successful
                shutdown_status = future.result()
                assert shutdown_status == 0

    # TODO better way to do this
    time.sleep(60)

    verify_changes(traun, expected_num_docs=2000, expected_num_revisions=0, expected_docs=traun.cache)
    verify_changes(seth, expected_num_docs=8000, expected_num_revisions=0, expected_docs=seth.cache)

    # Verify that the sg1 is down but the other sync_gateways are running
    errors = cluster.verify_sync_gateways_running()
    assert(len(errors) == 1 and errors[0][0].hostname == "sg1")


@pytest.mark.distributed_index
@pytest.mark.extendedsanity
@pytest.mark.parametrize(
        "conf", [
            ("sync_gateway_default_functional_tests_di.json"),
        ],
        ids=["DI-1"]
)
def test_dcp_reshard_sync_gateway_comes_up(cluster, conf):

    log.info("conf: {}".format(conf))

    cluster.reset(config=conf)
    cluster.sync_gateways[0].stop()

    admin = Admin(cluster.sync_gateways[1])

    traun = admin.register_user(target=cluster.sync_gateways[1], db="db", name="traun", password="password", channels=["ABC", "NBC", "CBS"])
    seth = admin.register_user(target=cluster.sync_gateways[2], db="db", name="seth", password="password", channels=["FOX"])

    log.info(">> Users added")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:

        futures = dict()

        # Bring up a sync_gateway
        futures[executor.submit(cluster.sync_gateways[0].start, conf)] = "sg_up"

        time.sleep(5)

        log.info(">>> Adding Traun docs")  # ABC, NBC, CBS
        futures[executor.submit(traun.add_docs, 6000)] = "traun"

        log.info(">>> Adding Seth docs")  # FOX
        futures[executor.submit(seth.add_docs, 4000)] = "seth"

        for future in concurrent.futures.as_completed(futures):
            tag = futures[future]
            log.info("{} Completed:".format(tag))
            if tag == "sg_up":
                up_status = future.result()
                assert up_status == 0

    # TODO better way to do this
    time.sleep(60)

    verify_changes(traun, expected_num_docs=6000, expected_num_revisions=0, expected_docs=traun.cache)
    verify_changes(seth, expected_num_docs=4000, expected_num_revisions=0, expected_docs=seth.cache)

    # Verify all sync_gateways are running
    errors = cluster.verify_sync_gateways_running()
    assert(len(errors) == 0)

