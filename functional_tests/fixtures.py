import pytest

import lib.settings

from lib.cluster import Cluster
from utilities.fetch_sg_logs import fetch_sync_gateway_logs

import settings

import logging
import lib.settings
log = logging.getLogger(lib.settings.LOGGER)


@pytest.fixture()
def cluster(request):

    def fetch_logs():

        # Fetch logs if a test fails
        if request.node.rep_call.failed:

            # example nodeid: tests/test_single_user_multiple_channels.py::test_1
            remove_slash = request.node.nodeid.replace("/", "-")
            test_id_elements = remove_slash.split("::")
            log_zip_prefix = "{0}-{1}".format(test_id_elements[0], test_id_elements[1])
            fetch_sync_gateway_logs(log_zip_prefix)

    if settings.CAPTURE_SYNC_GATEWAY_LOGS_ON_FAIL:
        request.addfinalizer(fetch_logs)

    c = Cluster()
    print(c)
    return c








