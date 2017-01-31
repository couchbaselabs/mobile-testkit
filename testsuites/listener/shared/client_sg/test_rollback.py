import time

import pytest

from keywords.utils import log_info
from libraries.testkit import cluster
from keywords import userinfo
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import sync_gateway_config_path_for_mode
from keywords.remoteexecutor import RemoteExecutor
from keywords import utils


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.syncgateway
@pytest.mark.replication
def test_client_rollback(setup_client_syncgateway_test):
    """ Test Sync Gateway rollback handling
    Steps
    - Add docs to sync gateway
    - Sync docs to client (state 1)
    - Trigger rollback on Couchbase server (Delete the vbucket files and restart CB (How to find vbucket files: VBID.couch.REV where REV increments with every compaction in /opt/couchbase/var/lib/couchbase/data/<bucket_name>))
    - Verify sg state reflects rollback state
    - Verify couchbase client reflects rollback state
    """

    sg_db = "db"
    ls_db = "ls_db"
    num_docs = 1000

    cluster_config = setup_client_syncgateway_test["cluster_config"]
    sg_mode = setup_client_syncgateway_test["sg_mode"]
    ls_url = setup_client_syncgateway_test["ls_url"]
    sg_admin_url = setup_client_syncgateway_test["sg_admin_url"]
    sg_public_url = setup_client_syncgateway_test["sg_url"]
    cb_server_url = setup_client_syncgateway_test["cb_server_url"]

    sg_config = sync_gateway_config_path_for_mode("listener_tests/listener_tests", sg_mode)
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    log_info("Running 'test_multiple_replications_not_created_with_same_properties'")
    log_info("ls_url: {}".format(ls_url))
    log_info("sg_public_url: {}".format(sg_public_url))
    log_info("sg_admin_url: {}".format(sg_admin_url))
    log_info("cb_server_url: {}".format(cb_server_url))

    client = MobileRestClient()
    client.create_database(url=ls_url, name=ls_db)

    # Create user / session on Sync Gateway
    seth_info = userinfo.UserInfo(name="seth", password="pass", channels=["NASA"], roles=[])
    client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=seth_info.name,
        password=seth_info.password,
        channels=seth_info.channels
    )

    # Get session from Sync Gateway
    seth_session_auth = client.create_session(
        url=sg_public_url,
        db=sg_db,
        name=seth_info.name,
        password=seth_info.password
    )

    # Create authenticated continuous pull replication from Sync Gateway 'sg_db' to client 'ls_db'
    client.start_replication(
        url=ls_url,
        continuous=True,
        from_url=sg_public_url, from_db=sg_db,
        to_db=ls_db,
        from_auth=seth_session_auth
    )

    # Add 1000 docs to Sync Gateway and verify that they replicate
    sg_docs = client.add_docs(
        url=sg_public_url,
        db=sg_db,
        number=num_docs,
        id_prefix=None,
        auth=seth_session_auth,
        channels=seth_info.channels
    )
    assert len(sg_docs) == num_docs

    # Verify docs show up on changes feed
    client.verify_docs_in_changes(
        url=sg_public_url,
        db=sg_db,
        expected_docs=sg_docs,
        auth=seth_session_auth
    )

    # Verify docs replicate to client
    client.verify_docs_present(
        url=ls_url,
        db=ls_db,
        expected_docs=sg_docs
    )
    # Verify docs show up on clients changes feed
    client.verify_docs_in_changes(
        url=ls_url,
        db=ls_db,
        expected_docs=sg_docs
    )

    # rex = RemoteExecutor()

    pytest.set_trace()
