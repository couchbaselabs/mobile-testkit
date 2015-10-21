import pytest

from lib.syncgateway import SyncGateway

sg_host_infos = [
    {"name": "sg1", "ip": "172.23.105.165"},
    {"name": "sg2", "ip": "172.23.105.166"},
    {"name": "sg3", "ip": "172.23.105.122"},
    {"name": "sg4", "ip": "172.23.105.118"}
]

sgs = [SyncGateway(sg_host_infos, "db") for sg_host_infos in sg_host_infos]


@pytest.fixture
def reset_cluster():
     from prov.reset_sync_gateway import reset_sync_gateway

def test_1(reset_cluster):

    for sg in sgs:
        r = sg.info()
        print(r.text)
        assert r.status_code == 200

    sgs[0].stop()
    sgs[3].stop()


