import os

import pytest

from requests.exceptions import HTTPError

from keywords.utils import log_info
from keywords.ClusterKeywords import ClusterKeywords
from keywords.Logging import Logging
from keywords.constants import SYNC_GATEWAY_CONFIGS
from keywords.MobileRestClient import MobileRestClient
from keywords.CouchbaseServer import CouchbaseServer
from keywords.Document import Document


@pytest.fixture(scope="function")
def setup_1sg_1cbs_test(request):

    test_name = request.node.name
    log_info("Setting up test '{}'".format(test_name))

    sg_config = "{}/reject_all_cc.json".format(SYNC_GATEWAY_CONFIGS)

    cluster_helper = ClusterKeywords()

    cluster_helper.reset_cluster(
        cluster_config=os.environ["CLUSTER_CONFIG"],
        sync_gateway_config=sg_config
    )

    topology = cluster_helper.get_cluster_topology(os.environ["CLUSTER_CONFIG"])

    yield {
        "cbs_url": topology["couchbase_servers"][0],
        "sg_url": topology["sync_gateways"][0]["public"],
        "sg_url_admin": topology["sync_gateways"][0]["admin"],
        "sg_db": "db",
        "bucket": "data-bucket"
    }

    log_info("Tearing down test '{}'".format(test_name))

    # if the test failed pull logs
    if request.node.rep_call.failed:
        logging_helper = Logging()
        logging_helper.fetch_and_analyze_logs(cluster_config=os.environ["CLUSTER_CONFIG"], test_name=test_name)


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.attachments
@pytest.mark.usefixtures("setup_1sg_1cbs_suite")
def test_attachments_on_docs_rejected_by_sync_function(setup_1sg_1cbs_test):
    """
    1. Start sync_gateway with sync function that rejects all writes:
    function(doc, oldDoc) {
      throw({forbidden:"No writes!"});
    }
    2. Create a doc with attachment
    3. Use CBS sdk to see if attachment doc exists.  Doc ID will look like _sync:att:sha1-Kq5sNclPz7QV2+lfQIuc6R7oRu0= (where the suffix is the digest)
    4. Assert att doc does not exist
    """

    cbs_url = setup_1sg_1cbs_test["cbs_url"]
    sg_url = setup_1sg_1cbs_test["sg_url"]
    sg_url_admin = setup_1sg_1cbs_test["sg_url_admin"]
    sg_db = setup_1sg_1cbs_test["sg_db"]
    bucket = setup_1sg_1cbs_test["bucket"]

    log_info("Running 'test_attachment_revpos_when_ancestor_unavailable'")
    log_info("Using cbs_url: {}".format(cbs_url))
    log_info("Using sg_url: {}".format(sg_url))
    log_info("Using sg_url_admin: {}".format(sg_url_admin))
    log_info("Using sg_db: {}".format(sg_db))
    log_info("Using bucket: {}".format(bucket))

    sg_user_name = "sg_user"
    sg_user_password = "sg_user_password"

    sg_user_channels = ["NBC"]

    client = MobileRestClient()
    doc_util = Document()

    sg_user = client.create_user(url=sg_url_admin, db=sg_db, name=sg_user_name, password=sg_user_password, channels=sg_user_channels)
    sg_user_session = client.create_session(url=sg_url_admin, db=sg_db, name=sg_user_name)

    # Verify all docs are getting rejected
    with pytest.raises(HTTPError) as he:
        docs = client.add_docs(url=sg_url, db=sg_db, number=100, id_prefix=sg_db, channels=sg_user_channels, auth=sg_user_session)
    assert he.value[0].startswith("403 Client Error: Forbidden for url:")

    # Create doc with attachment and push to sync_gateway
    doc_with_att = doc_util.create_doc(id="att_doc", content={"sample_key": "sample_val"}, attachment_name="sample_text.txt", channels=sg_user_channels)

    # Verify all docs are getting rejected
    with pytest.raises(HTTPError) as he:
        doc = client.add_doc(url=sg_url, db=sg_db, doc=doc_with_att, auth=sg_user_session)
    assert he.value[0].startswith("403 Client Error: Forbidden for url:")

    cb_util = CouchbaseServer()

    server_att_docs = cb_util.get_server_docs_with_prefix(url=cbs_url, bucket=bucket, prefix="_sync:att:")
    num_att_docs = len(server_att_docs)
    assert num_att_docs == 0
