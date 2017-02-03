import time

import pytest
import requests.exceptions

from keywords.utils import log_info
from libraries.testkit.cluster import Cluster
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import sync_gateway_config_path_for_mode

from keywords import remoteexecutor
from keywords import userinfo
from keywords import utils
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

    cluster_config = params_from_base_test_setup["cluster_config"]
    topology = params_from_base_test_setup["cluster_topology"]
    mode = params_from_base_test_setup["mode"]

    sg_url = topology["sync_gateways"][0]["public"]
    sg_admin_url = topology["sync_gateways"][0]["admin"]
    cb_server_url = topology["couchbase_servers"][0]
    sg_db = "db"
    num_docs = 1000

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

    vbucket_33_docs = document.generate_doc_ids_for_vbucket(33, number_doc_ids=50)

    seth_docs = client.add_docs(
        url=sg_url,
        db=sg_db,
        number=num_docs,
        id_prefix=None,
        auth=seth_session,
        channels=seth_user_info.channels
    )

    assert len(seth_docs) == num_docs

    client.verify_docs_in_changes(
        url=sg_url,
        db=sg_db,
        expected_docs=seth_docs,
        auth=seth_session
    )

    # rex = remoteexecutor.RemoteExecutor(utils.host_for_url(cb_server_url))
    #
    # # Delete some vBucket (5*) files to start a server rollback
    # # Example vbucket files - 195.couch.1  310.couch.1  427.couch.1  543.couch.1
    # log_info("Deleting vBucket files with the '5' prefix")
    # rex.must_execute('sudo find /opt/couchbase/var/lib/couchbase/data/data-bucket -name "5*" -delete')
    # log_info("Listing vBucket files ...")
    # out, err = rex.must_execute("sudo ls /opt/couchbase/var/lib/couchbase/data/data-bucket/")
    #
    # # out format: [u'0.couch.1     264.couch.1  44.couch.1\t635.couch.1  820.couch.1\r\n',
    # # u'1000.couch.1  265.couch.1 ...]
    # vbucket_files = []
    # for entry in out:
    #     vbucket_files.extend(entry.split())
    #
    # # Verify that the vBucket files starting with 5 are all gone
    # log_info("Verifing vBucket files are deleted ...")
    # for vbucket_file in vbucket_files:
    #     assert not vbucket_file.startswith("5")
    #
    # # Restart the server
    # rex.must_execute("sudo systemctl restart couchbase-server")
    #
    # max_retries = 20
    # count = 0
    # while count != max_retries:
    #     # Try to get changes, sync gateway should be able to recover and return changes
    #     try:
    #         client.get_changes(url=sg_url, db=sg_db, since=0, auth=seth_session, feed="normal")
    #         break
    #     except requests.exceptions.HTTPError as he:
    #         log_info("{}".format(he.response.status_code))
    #         log_info("Retrying in 1 sec ...")
    #         time.sleep(1)
    #         count += 1
    #
    # assert count != max_retries
