import sys
sys.path = ["..", "lib"] + sys.path
sys.path = ["..", "prov"] + sys.path
sys.path = ["..", "data"] + sys.path


import time
import concurrent.futures

from concurrent.futures import ThreadPoolExecutor

from sync_gateway import SyncGateway
from user import User
from data import Doc

from prov.kill_sync_gateway_instance import kill_sync_gateway_instance


def test_1():

    sg_ips = [
        "172.23.105.165",
        "172.23.105.166",
        "172.23.105.122",
        "172.23.105.118",
    ]

    sgs = [SyncGateway(sg_ip, "db") for sg_ip in sg_ips]
    #
    for sg in sgs:
        r = sg.info()
        print(r.text)
        assert r.status_code == 200

    kill_sync_gateway_instance("sg1")

    #
    # seth = User("seth", "password", ["ABC"])
    # print("Adding seth")
    # sgs[0].db.add_user(seth)
    #
    # adam = User("adam", "password", ["NBC", "CBS"])
    # print("Adding adam")
    # sgs[0].db.add_user(adam)
    #
    # traun = User("traun", "password", ["ABC", "NBC", "CBS"])
    # print("Adding traun")
    # sgs[0].db.add_user(traun)
    #
    # abc_docs = [Document(channels=["ABC"], body={"abc_item": "hi abc"}) for _ in range(2356)]
    # nbc_docs = [Document(channels=["NBC"], body={"nbc_item": "hi nbc"}) for _ in range(8198)]
    # cbs_docs = [Document(channels=["CBS"], body={"cbs_item": "hi cbs"}) for _ in range(10)]
    #
    # bulk_docs = [abc_docs, nbc_docs, cbs_docs]
    #
    # with ThreadPoolExecutor() as executor:
    #
    #     count = 0
    #     futures = []
    #
    #     for bulk_doc in bulk_docs:
    #         futures.append(executor.submit(sgs[count].db.add_user_bulk_documents, bulk_doc, seth))
    #         count += 1
    #
    #     for future in concurrent.futures.as_completed(futures):
    #         try:
    #             response = future.result()
    #             print("FUTURE")
    #         except Exception as e:
    #             print("Future _bulk_docs failed: {}".format(e))
    #         else:
    #             print(response.status_code)
    #             print(response.text)
    #
    #
    # # discuss appropriate time with team
    # time.sleep(30)
    #
    # # ABC
    # c_seth = sgs[0].db.get_user_changes(seth)
    # assert len(c_seth["results"]) == 2356
    #
    # # NBC + CBS
    # c_adam = sgs[0].db.get_user_changes(adam)
    # assert len(c_adam["results"]) == 8208
    #
    # # ABC + NBC + CBS
    # c_traun = sgs[0].db.get_user_changes(traun)
    # assert len(c_traun["results"]) == 10564

