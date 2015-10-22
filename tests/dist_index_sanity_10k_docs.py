import time
from threading import Thread
import pytest

from prov.reset_sync_gateway import reset_sync_gateway

from lib.syncgateway import SyncGateway
from lib.user import User
from data.data import Doc

sg_host_infos = [
    {"name": "sg1", "ip": "172.23.105.165"},
    {"name": "sg2", "ip": "172.23.105.166"},
    {"name": "sg3", "ip": "172.23.105.122"},
]

sgs = [SyncGateway(sg_host_infos, "db") for sg_host_infos in sg_host_infos]


@pytest.fixture
def reset_cluster():
    reset_sync_gateway()


def doc_spliter(docs, batch_num=100):
    for i in xrange(0, len(docs), batch_num):
        yield docs[i:i+batch_num]


def issue_requests_for_docs(docs, user):
    count = 0
    for doc in docs:
        sg_index = count % len(sgs)
        doc_name, doc_body = doc.name_and_body()
        r = sgs[sg_index].db.add_user_document(doc_name, doc_body, user)
        assert(r.status_code == 201)
        print(r.status_code)


def test_1(reset_cluster):

    start = time.time()

    for sg in sgs:
        r = sg.info()
        print(r.text)
        assert r.status_code == 200

    seth = User("seth", "password", ["ABC"])
    sgs[0].db.add_user(seth)

    no_channel_docs = [Doc(channels=[], body={"abc_item": "hi abc"}) for _ in range(3000)]
    channel_docs = [Doc(channels=["ABC"], body={"abc_item": "hi abc"}) for _ in range(7000)]

    no_channel_docs.extend(channel_docs)

    docs = no_channel_docs
    print(len(docs))

    batches = doc_spliter(docs)

    threads = []
    for batch in batches:
        threads.append(Thread(target=issue_requests_for_docs, args=(batch, seth)))

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    print("Channel[ABC] Created: {}".format(len(channel_docs)))

    time.sleep(10)

    c_r = sgs[0].db.get_user_changes(seth)
    number_of_changes = len(c_r["results"])

    end = time.time()
    print("TIME:{}s".format(end - start))

    print("CHANGES: {}".format(number_of_changes))
    assert number_of_changes == 7000
