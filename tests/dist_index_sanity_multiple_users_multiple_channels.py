import time
import pytest

from prov.reset_sync_gateway import reset_sync_gateway

from lib.syncgateway import SyncGateway
from lib.user import User
from data.data import Doc


sg_host_infos = [
    {"name": "sg1", "ip": "172.23.105.165"},
    {"name": "sg2", "ip": "172.23.105.166"},
    {"name": "sg3", "ip": "172.23.105.122"},
    {"name": "sg4", "ip": "172.23.105.118"}
]

sgs = [SyncGateway(sg_host_infos, "db") for sg_host_infos in sg_host_infos]


@pytest.fixture
def reset_cluster():
    reset_sync_gateway()


def test_1(reset_cluster):


    for sg in sgs:
        r = sg.info()
        print(r.text)
        assert r.status_code == 200

    seth = User("seth", "password", ["ABC"])
    print("Adding seth")
    sgs[0].db.add_user(seth)

    adam = User("adam", "password", ["NBC", "CBS"])
    print("Adding adam")
    sgs[0].db.add_user(adam)

    traun = User("traun", "password", ["ABC", "NBC", "CBS"])
    print("Adding traun")
    sgs[0].db.add_user(traun)

    abc_docs = [Doc(channels=["ABC"], body={"abc_item": "hi abc"}) for _ in range(2356)]
    nbc_docs = [Doc(channels=["NBC"], body={"nbc_item": "hi nbc"}) for _ in range(8198)]
    cbs_docs = [Doc(channels=["CBS"], body={"cbs_item": "hi cbs"}) for _ in range(10)]

    r = sgs[0].db.add_user_bulk_documents(abc_docs, seth)
    assert r.status_code == 201
    print(r.status_code)

    r = sgs[1].db.add_user_bulk_documents(nbc_docs, seth)
    assert r.status_code == 201
    print(r.status_code)

    r = sgs[2].db.add_user_bulk_documents(cbs_docs, seth)
    assert r.status_code == 201
    print(r.status_code)

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

