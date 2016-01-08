import pytest
import time
import concurrent.futures

from lib.data import Data
from lib.admin import Admin
from lib.user import User
from lib.verify import verify_changes

import lib.settings

from requests.exceptions import HTTPError

from fixtures import cluster

import logging
log = logging.getLogger(lib.settings.LOGGER)


@pytest.mark.sanity
@pytest.mark.parametrize(
    "conf,num_docs",
    [
        ("sync_gateway_default_cc.json", 5000)
    ],
    ids=["CC-1"]
)
def test_bulk_get_compression(cluster, conf, num_docs):

    log.info("Using conf: {}".format(conf))
    log.info("Using num_docs: {}".format(num_docs))

    #cluster.reset(conf)
    admin = Admin(cluster.sync_gateways[2])

    user = admin.register_user(cluster.sync_gateways[0], "db", "seth", "password", channels=["seth"])

    doc_body = Data.load("user_data_150k.json")
    for i in range(10):
        user.add_doc(doc_id="test-{}".format(i), content=doc_body)

    # POST /{db}/bulk_get
    doc_names = ["test-{}".format(i) for i in range(10)]
    response = user.get_docs(doc_ids=doc_names)

    # Uncompressed response 1500k

    print(response)


