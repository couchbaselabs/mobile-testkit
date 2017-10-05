import pytest
import time

from keywords.MobileRestClient import MobileRestClient
from requests import Session
from keywords.utils import log_info
from keywords.SyncGateway import SyncGateway


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf_name", [
    "sync_gateway_default"
])
def test_deleted_docs_from_changes_active_only(params_from_base_test_setup, sg_conf_name):
    """
    https://github.com/couchbase/sync_gateway/issues/2955
    1. Create a document
    2. Delete the document
    3. Restart Sync Gateway (to force rebuild of cache from view)
    4. Issue an active_only=true changes request
    5. Issue an active_only=false changes request
    The deleted document was not being included in the result set in step 5.
    """
    cluster_config = params_from_base_test_setup["cluster_config"]
    topology = params_from_base_test_setup["cluster_topology"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    sg_db = "db"
    num_docs = 1
    client = MobileRestClient()

    # Add doc to SG
    added_doc = client.add_docs(
        url=sg_admin_url,
        db=sg_db,
        number=num_docs,
        id_prefix="test_changes"
    )

    # Delete the doc
    log_info("added_doc: {}".format(added_doc))
    doc_id = added_doc[0]["id"]
    doc = client.get_doc(url=sg_admin_url, db=sg_db, doc_id=doc_id)
    doc_rev = doc['_rev']
    client.delete_doc(sg_admin_url, sg_db, doc_id, doc_rev)

    # Restart SG
    sg_obj = SyncGateway()
    sg_obj.restart_sync_gateways(cluster_config)
    time.sleep(5)

    session = Session()
    # Changes request with active_only=true
    request_url = "{}/{}/_changes?active_only=true".format(sg_admin_url, sg_db)
    log_info("Issuing changes request {}".format(request_url))
    resp = session.get(request_url)
    resp.raise_for_status()
    resp_obj = resp.json()
    log_info("resp1: {}".format(resp_obj))
    assert doc_id not in resp_obj["results"]["id"]

    # Changes request with active_only=false
    request_url = "{}/{}/_changes?active_only=false".format(sg_admin_url, sg_db)
    log_info("Issuing changes request {}".format(request_url))
    resp = session.get(request_url)
    resp.raise_for_status()
    resp_obj = resp.json()
    log_info("resp2: {}".format(resp_obj))
    assert doc_id in resp_obj["results"]["id"]
    assert resp_obj["results"]["deleted"] == "true"
