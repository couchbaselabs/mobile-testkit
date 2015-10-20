import sys


sys.path = ["..", "data"] + sys.path
sys.path = ["..", "lib"] + sys.path
sys.path = ["..", "prov"] + sys.path

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
from data import Doc
from data import ChannelDoc


@pytest.fixture
def reset_cluster():
     from prov.reset_sync_gateway import reset_sync_gateway


def test_1(reset_cluster):

    sg_ips = [
        "172.23.105.165",
        "172.23.105.166",
        "172.23.105.122",
        "172.23.105.118",
    ]

    sgs = [SyncGateway(sg_ip, "db") for sg_ip in sg_ips]

    for sg in sgs:
        r = sg.info()
        print(r.text)
        assert r.status_code == 200

    seth = User("seth", "password", ["ABC"])
    sgs[0].db.add_user(seth)

    no_channel_docs = [Doc(body={"abc_item": "hi abc"}) for _ in range(3000)]
    channel_docs = [ChannelDoc(channels=["ABC"], body={"abc_item": "hi abc"}) for _ in range(7000)]

    with ThreadPoolExecutor(max_workers=40) as executor:

        futures = []

        count = 0
        for doc in no_channel_docs:
            sg_index = count % len(sgs)
            doc_name, doc_body = doc.name_and_body()
            futures.append(executor.submit(sgs[sg_index].db.add_user_document, doc_name, doc_body, seth))
            count += 1

        count = 0
        for doc in channel_docs:
            sg_index = count % len(sgs)
            doc_name, doc_body = doc.name_and_body()
            futures.append(executor.submit(sgs[sg_index].db.add_user_document, doc_name, doc_body, seth))
            count += 1

        docs_done = 0
        reported_created = 0
        for future in concurrent.futures.as_completed(futures):
            try:
                r = future.result()
            except Exception as e:
                print("Generated an exception: doc:{} e:{}".format(doc, e))
            else:
                print(docs_done)
                #print(r.status_code)
                if r.status_code == 201:
                    reported_created += 1
                if r.status_code != 201:
                    print("{}:{}".format(r.status_code, r.text))
                docs_done += 1

    assert reported_created == 10000
    print("201 Created: {}".format(reported_created))
    assert len(channel_docs) == 7000
    print("Channel[ABC] Created: {}".format(len(channel_docs)))

    time.sleep(10)

    c_r = sgs[0].db.get_user_changes(seth)
    number_of_changes = len(c_r["results"])

    print("CHANGES: {}".format(number_of_changes))
    assert number_of_changes == 7000
