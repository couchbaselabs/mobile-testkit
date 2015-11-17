import pytest

from lib.cluster import Cluster


@pytest.fixture()
def cluster():
    c = Cluster()
    print(c)
    return c







