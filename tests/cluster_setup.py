import pytest

from lib.cluster import Cluster


@pytest.fixture()
def cluster():
    c = Cluster("conf/hosts.ini")
    return c







