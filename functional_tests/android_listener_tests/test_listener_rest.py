import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import os

import lib.settings
from lib.listener import Listener
from lib.user import User
from lib.verify import verify_same_docs

from lib import settings
import logging
log = logging.getLogger(settings.LOGGER)

import time


def create_listener(target_device, local_port, apk_path, activity, reinstall):
    return Listener(target_device=target_device, local_port=local_port, apk_path=apk_path, activity=activity, reinstall=reinstall)


def test_scenario_two():

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

    listeners = {}

    # Create all listeners concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(device_defs)) as executor:

        future_to_device_name = {
            executor.submit(
                create_listener,
                target_device=device_def["target_device"],
                local_port=device_def["local_port"],
                apk_path=device_def["apk_path"],
                activity=device_def["activity"],
                reinstall=should_reinstall,
            ): device_def["target_device"]
            for device_def in device_defs
        }

        for future in concurrent.futures.as_completed(future_to_device_name):

            name = future_to_device_name[future]
            listener = future.result()

            listeners[name] = listener
            log.info("Listener created: {} {}".format(name, listener))

    time.sleep(2)

    emu_1 = listeners["emulator-5554"]
    emu_2 = listeners["emulator-5556"]
    emu_3 = listeners["emulator-5558"]
    emu_4 = listeners["emulator-5560"]
    emu_5 = listeners["emulator-5562"]

    emu_1.verify_launched()
    emu_2.verify_launched()
    emu_3.verify_launched()
    emu_4.verify_launched()
    emu_5.verify_launched()

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
    emu_1.start_pull_replication(emu_2.url, db=db_name)
    emu_1.start_pull_replication(emu_3.url, db=db_name)
    emu_1.start_pull_replication(emu_4.url, db=db_name)
    emu_1.start_pull_replication(emu_5.url, db=db_name)

    emu_1.start_push_replication(emu_2.url, db=db_name)
    emu_1.start_push_replication(emu_3.url, db=db_name)
    emu_1.start_push_replication(emu_4.url, db=db_name)
    emu_1.start_push_replication(emu_5.url, db=db_name)

    # Wait for all docs to push to emulators
    time.sleep(30)

    # TODO Assert each endpoint has 200 docs

    # Stop all replication
    emu_1.stop_pull_replication(emu_2.url, db=db_name)
    emu_1.stop_pull_replication(emu_3.url, db=db_name)
    emu_1.stop_pull_replication(emu_4.url, db=db_name)
    emu_1.stop_pull_replication(emu_5.url, db=db_name)

    emu_1.stop_push_replication(emu_2.url, db=db_name)
    emu_1.stop_push_replication(emu_3.url, db=db_name)
    emu_1.stop_push_replication(emu_4.url, db=db_name)
    emu_1.stop_push_replication(emu_5.url, db=db_name)

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

    # TODO Verify 3,4,5 have 240

    time.sleep(2)

    # Create dbs on master and first slave
    emu_1.create_db(db_name)
    emu_2.create_db(db_name)

    # TODO Verify db has been created, and doc count should be 0

    time.sleep(5)

    # Start all replication
    emu_1.start_pull_replication(emu_2.url, db=db_name)
    emu_1.start_pull_replication(emu_3.url, db=db_name)
    emu_1.start_pull_replication(emu_4.url, db=db_name)
    emu_1.start_pull_replication(emu_5.url, db=db_name)

    emu_1.start_push_replication(emu_2.url, db=db_name)
    emu_1.start_push_replication(emu_3.url, db=db_name)
    emu_1.start_push_replication(emu_4.url, db=db_name)
    emu_1.start_push_replication(emu_5.url, db=db_name)

    time.sleep(45)

    emus = [emu_1, emu_2, emu_3, emu_4, emu_5]
    for emu in emus:
        doc_num = emu.get_num_docs(db_name)
        log.info("emu: {} doc_num: {}".format(emu.target_device, doc_num))
        # assert (doc_num == 661)
