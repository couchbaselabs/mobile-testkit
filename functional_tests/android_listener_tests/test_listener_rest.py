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


def test_scenario_two():

    apk_path = os.environ["P2P_APP"]
    activity = ""
    db_name = "db"

    emulator_1 = Listener(target_device="emulator-5554", local_port=10000, apk_path=apk_path, activity=activity)
    emulator_2 = Listener(target_device="emulator-5556", local_port=11000, apk_path=apk_path, activity=activity)
    device_1 = Listener(target_device="", local_port=12000, apk_path=apk_path, activity=activity)

    emulator_1.verify_lauched()
    emulator_2.verify_lauched()
    device_1.verify_lauched()

    emu1_dbs = emulator_1.get_dbs()
    emu2_dbs = emulator_2.get_dbs()
    dev1_dbs = device_1.get_dbs()

    log.info("emu1_dbs: {}".format(emu1_dbs))
    log.info("emu2_dbs: {}".format(emu2_dbs))
    log.info("dev1_dbs: {}".format(dev1_dbs))

    emu1_pusher = User(target=emulator_1, db=db_name, name="emu1_doc_pusher", password="password", channels=["ABC"])
    emu2_pusher = User(target=emulator_2, db=db_name, name="emu2_doc_pusher", password="password", channels=["ABC"])

    emu1_pusher.add_docs(100, bulk=True)
    emu2_pusher.add_docs(100, bulk=True)

    device_1.start_pull_replication(emulator_1.url, db=db_name)
    device_1.start_pull_replication(emulator_2.url, db=db_name)
    device_1.start_push_replication(emulator_1.url, db=db_name)
    device_1.start_push_replication(emulator_2.url, db=db_name)
