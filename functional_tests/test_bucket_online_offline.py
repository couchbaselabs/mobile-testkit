import pytest

from fixtures import cluster

@pytest.mark.sanity
def test_online_rest(cluster):

    cluster.reset("bucket_online_offline/bucket_online_offline_offline_false.json")







