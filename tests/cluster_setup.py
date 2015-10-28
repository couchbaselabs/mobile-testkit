import pytest

from prov.reset_sync_gateway import reset_sync_gateway
from lib.cluster import Cluster


@pytest.fixture()
def cluster():
    c = Cluster("conf/hosts.ini")
    c.reset()
    return c







