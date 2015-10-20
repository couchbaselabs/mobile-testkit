import sys


sys.path = ["..", "lib"] + sys.path
sys.path = ["..", "prov"] + sys.path
sys.path = ["..", "prov", "scripts"] + sys.path
sys.path = ["..", "data"] + sys.path

# Local
# PUT /{db}/{local-doc-id}
# GET /{db}/{local-doc-id}
# DELETE /{db}/{local-doc-id}


import time
import uuid
import os
import pytest
import concurrent.futures

from concurrent.futures import ThreadPoolExecutor

from sync_gateway import SyncGateway
from user import User
from data import Document


def test_1():

    sg_ips = ["127.0.0.1"]

    sgs = [SyncGateway(sg_ip, "db") for sg_ip in sg_ips]

    for sg in sgs:
        r = sg.info()
        print(r.text)
        assert r.status_code == 200

    seth = User("seth", "password", ["ABC"])
    sgs[0].db.add_user(seth)

    adam = User("adam", "password", ["NBC", "CBS"])
    sgs[0].db.add_user(adam)

    traun = User("traun", "password", ["ABC", "NBC", "CBS"])
    sgs[0].db.add_user(traun)

    abc_docs = [Document(channels=["ABC"], body={"abc_item": "hi abc"}) for _ in range(2356)]
    nbc_docs = [Document(channels=["NBC"], body={"nbc_item": "hi nbc"}) for _ in range(8198)]
    cbs_docs = [Document(channels=["CBS"], body={"cbs_item": "hi cbs"}) for _ in range(10)]

    r_1 = sgs[0].db.add_bulk_documents(abc_docs)
    print(r_1.status_code)
    assert r_1.status_code == 201

    r_2 = sgs[0].db.add_bulk_documents(nbc_docs)
    print(r_2.status_code)
    assert r_2.status_code == 201

    r_3 = sgs[0].db.add_bulk_documents(cbs_docs)
    print(r_3.status_code)
    assert r_3.status_code == 201

    # discuss appropriate time with team
    time.sleep(30)

    # ABC
    c_seth = sgs[0].db.get_user_changes(seth)
    assert len(c_seth["results"]) == 2356

    # NBC + CBS
    c_adam = sgs[0].db.get_user_changes(adam)
    assert len(c_adam["results"]) == 8208

    # ABC + NBC + CBS
    c_traun = sgs[0].db.get_user_changes(traun)
    assert len(c_traun["results"]) == 10564

    #
    # with ThreadPoolExecutor(max_workers=40) as executor:
    #
    #     future_to_doc = {}
    #
    #     count = 0
    #     for doc in docs:
    #         sg_index = count % len(sgs)
    #         future_to_doc[executor.submit(sgs[sg_index].db.add_user_document, doc["name"], doc["doc_body"], seth)] = doc
    #         count += 1
    #
    #     docs_done = 0
    #     reported_created = 0
    #     for future in concurrent.futures.as_completed(future_to_doc):
    #         doc = future_to_doc[future]
    #         try:
    #             r = future.result()
    #         except Exception as e:
    #             print("Generated an exception: doc:{} e:{}".format(doc, e))
    #         else:
    #             print(docs_done)
    #             #print(r.status_code)
    #             if r.status_code == 201:
    #                 reported_created += 1
    #             if r.status_code != 201:
    #                 print("{}:{}".format(r.status_code, r.text))
    #             docs_done += 1
    #
    # assert reported_created == 10000
    # print("201 Created: {}".format(reported_created))
    # assert len(channel_docs) == 5000
    # print("Channel[ABC] Created: {}".format(len(channel_docs)))
    #
    # c_r = sgs[0].db.get_user_changes(seth)
    # number_of_changes = len(c_r["results"])
    #
    # print("CHANGES: {}".format(number_of_changes))
    # assert number_of_changes == 5000
