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

    emulator_1 = Listener(target_device="emulator-5556", local_port=10000, apk_path=apk_path, activity=activity)
    emulator_2 = Listener(target_device="emulator-5554", local_port=11000, apk_path=apk_path, activity=activity)
    device_1 = Listener(target_device="06c455850b3fa11e", local_port=12000, apk_path=apk_path, activity=activity)

    emu1_dbs = emulator_1.get_dbs()
    emu2_dbs = emulator_2.get_dbs()
    dev1_dbs = device_1.get_dbs()

    log.info("emu1_dbs: {}".format(emu1_dbs))
    log.info("emu2_dbs: {}".format(emu2_dbs))
    log.info("dev1_dbs: {}".format(dev1_dbs))

#def test_scenario_one():

    # db_name = "db"
    # num_users = 50
    # num_docs_per_user = 100
    #
    # liteserv = LiteServ(port=5984)
    # liteserv.reset()
    # liteserv.create_db(db_name)
    #
    # users = [User(target=liteserv, db=db_name, name="client_{}".format(i), password="password", channels=["ABC"]) for i in range(num_users)]
    # terminator = User(target=liteserv, db=db_name, name="terminator", password="password", channels=["ABC"])
    #
    #
    # with ThreadPoolExecutor(max_workers=lib.settings.MAX_REQUEST_WORKERS) as executor:
    #
    #     long_poll_future_to_user = {executor.submit(user.start_longpoll_changes_tracking, "termdoc"): user for user in users}
    #     push_op_to_user_name = {executor.submit(user.add_docs, num_docs_per_user, True): user.name for user in users}
    #
    #     for future in concurrent.futures.as_completed(push_op_to_user_name):
    #         user_name = push_op_to_user_name[future]
    #
    #         log.info("{} finished pushing docs".format(user_name))
    #
    #     all_caches = [user.cache for user in users]
    #     all_docs = {k: v for cache in all_caches for k, v in cache.items()}
    #
    #     terminator.add_doc("termdoc")
    #
    #     for future in concurrent.futures.as_completed(long_poll_future_to_user):
    #         user = long_poll_future_to_user[future]
    #         docs, seq_num = future.result()
    #         log.info("{} num_changes in longpoll: {}".format(user, len(docs)))
    #         verify_same_docs(num_users * num_docs_per_user, all_docs, docs)
