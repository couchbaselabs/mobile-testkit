import sys
sys.path = ["..", "lib"] + sys.path
sys.path = ["..", "prov"] + sys.path
sys.path = ["..", "data"] + sys.path


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

    sgs[0].stop()


