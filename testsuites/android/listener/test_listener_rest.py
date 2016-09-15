import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import os
import time

import testkit.settings
from testkit.listener import Listener
from testkit.user import User
from testkit.verify import verify_same_docs
from testkit.android import parallel_install

from testkit import settings
import logging
log = logging.getLogger(settings.LOGGER)


def start_pull_replications(db_name, source, targets):
    for target in targets:
        source.start_pull_replication(target.url, db_name, db_name)


def start_push_replications(db_name, source, targets):
    for target in targets:
        source.start_push_replication(target.url, db_name, db_name)


def stop_pull_replications(db_name, source, targets):
    for target in targets:
        source.stop_pull_replication(target.url, db_name, db_name)


def stop_push_replications(db_name, source, targets):
    for target in targets:
        source.stop_push_replication(target.url, db_name, db_name)


def test_selective_db_delete_and_replication_lifecycle():

    should_reinstall = True
    apk_path = os.environ["P2P_APP"]
    activity = "com.couchbase.ui.maven/com.couchbase.ui.MainActivity"
    db_name = "db"

    device_defs = [
        {"target_device": "emulator-5554", "local_port": 10000, "apk_path": apk_path, "activity": activity},
        {"target_device": "emulator-5556", "local_port": 11000, "apk_path": apk_path, "activity": activity},
        {"target_device": "emulator-5558", "local_port": 12000, "apk_path": apk_path, "activity": activity},
        {"target_device": "emulator-5560", "local_port": 13000, "apk_path": apk_path, "activity": activity},
        {"target_device": "emulator-5562", "local_port": 14000, "apk_path": apk_path, "activity": activity},
    ]

    listeners = parallel_install(device_defs, should_reinstall)

    time.sleep(2)

    emu_1 = listeners["emulator-5554"]
    emu_2 = listeners["emulator-5556"]
    emu_3 = listeners["emulator-5558"]
    emu_4 = listeners["emulator-5560"]
    emu_5 = listeners["emulator-5562"]

    all_emus = [emu_1, emu_2, emu_3, emu_4, emu_5]
    for emu in all_emus:
        emu.verify_launched()

    # Add docs on master device
    emu_1_pusher = User(target=emu_1, db=db_name, name="emu1_doc_pusher", password="password", channels=["ABC"])
    emu_1_pusher.add_docs(600, bulk=True)
    emu_1_pusher.add_design_doc(
        doc_id="view1",
        content={
            "views": {
                "dt1": {
                    "map": "function(doc) {if (doc.type == \'dt1\') {emit(doc._id, doc);}}"
                },
                "filters": {
                    "dt1": "function(doc) {if (doc.type == \'dt1\') {return true} return false}"
                }
            }
        }
    )

    # Start all replication
    targets = [emu_2, emu_3, emu_4, emu_5]
    start_pull_replications(db_name, emu_1, targets)
    start_push_replications(db_name, emu_1, targets)

    # Wait for all docs to push to emulators
    time.sleep(30)

    # Assert each endpoint has 601 docs
    for emu in all_emus:
        assert emu.get_num_docs(db_name) == 601

    # Stop all replication
    stop_pull_replications(db_name, emu_1, targets)
    stop_push_replications(db_name, emu_1, targets)

    # Wait for all replications to stop
    time.sleep(30)

    # Delete dbs on master and first slave
    emu_1.delete_db(db_name)
    emu_2.delete_db(db_name)

    # TODO Verify db is deleted

    time.sleep(2)

    # Add docs to the reset of the slaves
    emu_3_pusher = User(target=emu_3, db=db_name, name="emu3_doc_pusher", password="password", channels=["ABC"])
    emu_4_pusher = User(target=emu_4, db=db_name, name="emu4_doc_pusher", password="password", channels=["ABC"])
    emu_5_pusher = User(target=emu_5, db=db_name, name="emu5_doc_pusher", password="password", channels=["ABC"])

    emu_3_pusher.add_docs(20)
    emu_4_pusher.add_docs(20)
    emu_5_pusher.add_docs(20)

    time.sleep(2)

    # TODO Verify 3,4,5 have 621
    for emu in [emu_3, emu_4, emu_5]:
        assert emu.get_num_docs(db_name) == 621

    # Create dbs on master and first slave
    emu_1.create_db(db_name)
    emu_2.create_db(db_name)

    # TODO Verify db has been created, and doc count should be 0

    time.sleep(5)

    # Start all replication
    start_pull_replications(db_name, emu_1, targets)
    start_push_replications(db_name, emu_1, targets)

    time.sleep(45)

    emus = [emu_1, emu_2, emu_3, emu_4, emu_5]
    for emu in emus:
        doc_num = emu.get_num_docs(db_name)
        log.info("emu: {} doc_num: {}".format(emu.target_device, doc_num))
        assert doc_num == 661


def test_replication_unstable_network():

    should_reinstall = False
    apk_path = os.environ["P2P_APP"]
    activity = "com.couchbase.ui.maven/com.couchbase.ui.MainActivity"
    db_name = os.environ["P2P_APP_DB"]

    device_defs = [
        {"target": "06c455850b3fa11e", "local_port": None, "apk_path": apk_path, "activity": activity},
        {"target": "emulator-5554", "local_port": 10000, "apk_path": apk_path, "activity": activity},
        {"target": "emulator-5556", "local_port": 11000, "apk_path": apk_path, "activity": activity},
        {"target": "emulator-5558", "local_port": 12000, "apk_path": apk_path, "activity": activity},
        {"target": "emulator-5560", "local_port": 13000, "apk_path": apk_path, "activity": activity},
        {"target": "emulator-5562", "local_port": 14000, "apk_path": apk_path, "activity": activity},
        {"target": "emulator-5564", "local_port": 15000, "apk_path": apk_path, "activity": activity},
    ]

    listeners = parallel_install(device_defs, should_reinstall)

    dev = listeners["06c455850b3fa11e"]
    emu_1 = listeners["emulator-5554"]
    emu_2 = listeners["emulator-5556"]
    emu_3 = listeners["emulator-5558"]
    emu_4 = listeners["emulator-5560"]
    emu_5 = listeners["emulator-5562"]
    emu_6 = listeners["emulator-5564"]

    emus = [emu_1, emu_2, emu_3, emu_4, emu_5, emu_6]

    dev.verify_launched()
    for emu in emus:
        emu.verify_launched()

    log.info("Starting push replications ...")
    start_push_replications(db_name, dev, emus)

    log.info("Starting pull replications ...")
    start_pull_replications(db_name, dev, emus)

    log.info("Adding 100 docs to dev")
    dev_pusher = User(target=dev, db=db_name, name="emu1_doc_pusher", password="password", channels=["ABC"])
    dev_pusher.add_docs(100, bulk=True)

    time.sleep(10)

    # Assert each endpoint has 100 docs
    assert dev.get_num_docs(db_name) == 100
    for emu in emus:
        assert emu.get_num_docs(db_name) == 100

    # Create docs on targets
    emu_1_pusher = User(target=emu_1, db=db_name, name="emu1_doc_pusher", password="password", channels=["ABC"])
    emu_2_pusher = User(target=emu_2, db=db_name, name="emu2_doc_pusher", password="password", channels=["ABC"])
    emu_3_pusher = User(target=emu_3, db=db_name, name="emu3_doc_pusher", password="password", channels=["ABC"])
    emu_4_pusher = User(target=emu_4, db=db_name, name="emu4_doc_pusher", password="password", channels=["ABC"])
    emu_5_pusher = User(target=emu_5, db=db_name, name="emu5_doc_pusher", password="password", channels=["ABC"])
    emu_6_pusher = User(target=emu_6, db=db_name, name="emu6_doc_pusher", password="password", channels=["ABC"])

    emu_1_pusher.add_docs(10)
    emu_2_pusher.add_docs(10)
    emu_3_pusher.add_docs(10)
    emu_4_pusher.add_docs(10)
    emu_5_pusher.add_docs(10)
    emu_6_pusher.add_docs(10)

    time.sleep(5)

    # Assert each endpoint has 140 docs
    assert dev.get_num_docs(db_name) == 160

    for emu in emus:
        assert emu.get_num_docs(db_name) == 160



