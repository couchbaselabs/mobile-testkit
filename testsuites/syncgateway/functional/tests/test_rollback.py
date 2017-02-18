import time

import pytest
import requests.exceptions
import concurrent.futures

from keywords.utils import log_info
from libraries.testkit.cluster import Cluster
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import sync_gateway_config_path_for_mode

from keywords import couchbaseserver
from keywords import userinfo
from keywords import document


@pytest.mark.sanity
@pytest.mark.syncgateway
@pytest.mark.changes
@pytest.mark.parametrize("sg_conf_name", [
    "sync_gateway_default"
])
def test_rollback_server_reset(params_from_base_test_setup, sg_conf_name):
    """
    Test for sync gateway resiliency under Couchbase Server rollback

    Scenario
    1. Create user (seth:pass) and session
    2. Add 1000 docs with uuid id's
    3. Verify the docs show up in seth's changes feed
    4. Delete vBucket files on server
    5. Restart server
    6.
    """

    num_vbuckets = 1024

    cluster_config = params_from_base_test_setup["cluster_config"]
    topology = params_from_base_test_setup["cluster_topology"]
    mode = params_from_base_test_setup["mode"]

    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    cb_server_url = topology["couchbase_servers"][0]
    cb_server = couchbaseserver.CouchbaseServer(cb_server_url)

    sg_db = "db"
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cluster = Cluster(cluster_config)
    cluster.reset(sg_conf)

    client = MobileRestClient()
    seth_user_info = userinfo.UserInfo("seth", "pass", channels=["NASA"], roles=[])

    client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=seth_user_info.name,
        password=seth_user_info.password,
        channels=seth_user_info.channels
    )

    seth_session = client.create_session(
        url=sg_admin_url,
        db=sg_db,
        name=seth_user_info.name,
        password=seth_user_info.password
    )

    # create a doc that will hash to each vbucket in parallel except for vbucket 66
    doc_id_for_every_vbucket_except_66 = []
    with concurrent.futures.ProcessPoolExecutor() as pex:
        futures = [pex.submit(document.generate_doc_id_for_vbucket, i) for i in range(num_vbuckets) if i != 66]
        for future in concurrent.futures.as_completed(futures):
            doc_id = future.result()
            doc = document.create_doc(
                doc_id=doc_id,
                channels=seth_user_info.channels
            )
            doc_id_for_every_vbucket_except_66.append(doc)

    vbucket_66_docs = []
    for _ in range(5):
        vbucket_66_docs.append(document.create_doc(
            doc_id=document.generate_doc_id_for_vbucket(66),
            channels=seth_user_info.channels
        ))

    seth_docs = client.add_bulk_docs(url=sg_url, db=sg_db, docs=doc_id_for_every_vbucket_except_66, auth=seth_session)
    seth_66_docs = client.add_bulk_docs(url=sg_url, db=sg_db, docs=vbucket_66_docs, auth=seth_session)

    assert len(seth_docs) == num_vbuckets - 1
    assert len(seth_66_docs) == 5

    # Verify the all docs show up in seth's changes feed
    all_docs = seth_docs + seth_66_docs
    assert len(all_docs) == (num_vbuckets - 1) + 5

    client.verify_docs_in_changes(
        url=sg_url,
        db=sg_db,
        expected_docs=all_docs,
        auth=seth_session
    )

    # Delete vbucket and restart server
    cb_server.delete_vbucket(66, "data-bucket")
    cb_server.restart()

    max_retries = 20
    count = 0
    while count != max_retries:
        # Try to get changes, sync gateway should be able to recover and return changes
        try:
            # A changes since=0 should now be in a rolled back state due to the data loss from the removed vbucket
            # Seth should only see the docs not present in vbucket 66, unlike all the docs as above.
            changes = client.get_changes(url=sg_url, db=sg_db, since=0, auth=seth_session)
            break
        except requests.exceptions.HTTPError as he:
            log_info("{}".format(he.response.status_code))
            log_info("Retrying in 1 sec ...")
            time.sleep(1)
            count += 1

    assert count != max_retries

    # Get a list of all the changes ids that are not the user doc
    changes_ids = [change["id"] for change in changes["results"] if not change["id"].startswith("_user")]
    assert len(changes_ids) == num_vbuckets - 1
    for doc in seth_66_docs:
        assert doc["id"] not in changes_ids
