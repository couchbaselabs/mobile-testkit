import time

import concurrent.futures

from testkit.admin import Admin
from testkit.verify import verify_changes
from testkit.cluster import Cluster

import testkit.settings
import logging
log = logging.getLogger(testkit.settings.LOGGER)


def test_dcp_reshard_sync_gateway_goes_down(conf):

    log.info("conf: {}".format(conf))

    cluster = Cluster()
    mode = cluster.reset(config_path=conf)

    admin = Admin(cluster.sync_gateways[0])

    traun = admin.register_user(target=cluster.sync_gateways[0], db="db", name="traun", password="password", channels=["ABC", "NBC", "CBS"])
    seth = admin.register_user(target=cluster.sync_gateways[0], db="db", name="seth", password="password", channels=["FOX"])

    log.info(">> Users added")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:

        futures = dict()

        log.info(">>> Adding Seth docs")  # FOX
        futures[executor.submit(seth.add_docs, 8000)] = "seth"

        log.info(">>> Adding Traun docs")  # ABC, NBC, CBS
        futures[executor.submit(traun.add_docs, 2000, bulk=True)] = "traun"

        # stop sg_accel
        shutdown_status = cluster.sg_accels[0].stop()
        assert shutdown_status == 0

        for future in concurrent.futures.as_completed(futures):
            tag = futures[future]
            log.info("{} Completed:".format(tag))

    # TODO better way to do this
    time.sleep(120)

    verify_changes(traun, expected_num_docs=2000, expected_num_revisions=0, expected_docs=traun.cache)
    verify_changes(seth, expected_num_docs=8000, expected_num_revisions=0, expected_docs=seth.cache)

    # Verify that the sg1 is down but the other sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 1 and errors[0][0].hostname == "ac1")


def test_dcp_reshard_sync_gateway_comes_up(conf):

    log.info("conf: {}".format(conf))

    cluster = Cluster()
    mode = cluster.reset(config_path=conf)
    stop_status = cluster.sg_accels[0].stop()
    assert stop_status == 0, "Failed to stop sg_accel"

    admin = Admin(cluster.sync_gateways[0])

    traun = admin.register_user(target=cluster.sync_gateways[0], db="db", name="traun", password="password", channels=["ABC", "NBC", "CBS"])
    seth = admin.register_user(target=cluster.sync_gateways[0], db="db", name="seth", password="password", channels=["FOX"])

    log.info(">> Users added")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:

        futures = dict()

        time.sleep(5)

        log.info(">>> Adding Traun docs")  # ABC, NBC, CBS
        futures[executor.submit(traun.add_docs, 6000)] = "traun"

        log.info(">>> Adding Seth docs")  # FOX
        futures[executor.submit(seth.add_docs, 4000)] = "seth"

        # Bring up a sync_gateway
        up_status = cluster.sg_accels[0].start(conf)
        assert up_status == 0

        for future in concurrent.futures.as_completed(futures):
            tag = futures[future]
            log.info("{} Completed:".format(tag))

    # TODO better way to do this
    time.sleep(60)

    verify_changes(traun, expected_num_docs=6000, expected_num_revisions=0, expected_docs=traun.cache)
    verify_changes(seth, expected_num_docs=4000, expected_num_revisions=0, expected_docs=seth.cache)

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)


def test_dcp_reshard_single_sg_accel_goes_down_and_up(conf):

    log.info("conf: {}".format(conf))

    cluster = Cluster()
    mode = cluster.reset(config_path=conf)

    # Stop the second sg_accel
    stop_status = cluster.sg_accels[1].stop()
    assert stop_status == 0, "Failed to stop sg_accel"

    admin = Admin(cluster.sync_gateways[0])

    traun = admin.register_user(target=cluster.sync_gateways[0], db="db", name="traun", password="password", channels=["ABC", "NBC", "CBS"])
    seth = admin.register_user(target=cluster.sync_gateways[0], db="db", name="seth", password="password", channels=["FOX"])

    log.info(">> Users added")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:

        futures = dict()

        log.info(">>> Adding Seth docs")  # FOX
        futures[executor.submit(seth.add_docs, 8000)] = "seth"

        log.info(">>> Adding Traun docs")  # ABC, NBC, CBS
        futures[executor.submit(traun.add_docs, 10000, bulk=True)] = "traun"

        # take down a sync_gateway
        shutdown_status = cluster.sg_accels[0].stop()
        assert shutdown_status == 0

        # Add more docs while no writers are online
        log.info(">>> Adding Seth docs")  # FOX
        futures[executor.submit(seth.add_docs, 2000, bulk=True)] = "seth"

        # Start a single writer
        start_status = cluster.sg_accels[0].start(conf)
        assert start_status == 0

        for future in concurrent.futures.as_completed(futures):
            tag = futures[future]
            log.info("{} Completed:".format(tag))

    # TODO better way to do this
    time.sleep(120)

    verify_changes(traun, expected_num_docs=10000, expected_num_revisions=0, expected_docs=traun.cache)
    verify_changes(seth, expected_num_docs=10000, expected_num_revisions=0, expected_docs=seth.cache)

    # Start second writer again
    start_status = cluster.sg_accels[1].start(conf)
    assert start_status == 0

    # Verify that all sync_gateways and
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)
