import pytest
import time

from keywords.MobileRestClient import MobileRestClient
from CBLClient.Replication import Replication
from keywords.SyncGateway import sync_gateway_config_path_for_mode, replace_xattrs_sync_func_in_config
from keywords import document
from libraries.testkit import cluster
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf
from CBLClient.Database import Database
from keywords import document, attachment
from CBLClient.Replication import Replication
from CBLClient.Authenticator import Authenticator

@pytest.mark.channels
@pytest.mark.syncgateway
def test_delete_docs_with_attachments(params_from_base_test_setup):
    """
    :param params_from_base_test_setup:
    :param sg_conf_name:
    1. Have CBL and SG up and running
    2. Create docs with attachment on SG and CBL
    3. Replicate the docs
    4. Delete few docs in CBL
    5. Delete few docs in SG and pull CBL docs
    6. Verify Attachments got deleted from the bucket
    """
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    if sync_gateway_version < "3.0.0":
        pytest.skip('This test cannot run with sg version below 3.0.0')

    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    mode = params_from_base_test_setup["mode"]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    num_of_docs = 10

    channels = ["attachments"]
    db = Database(base_url)
    sg_client = MobileRestClient()

    sg_config = params_from_base_test_setup["sg_config"]
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 1. Add docs to SG.
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    sg_docs = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs,
                                   attachments_generator=attachment.generate_2_png_10_10, channels=channels)
    sg_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sg_docs, auth=session)
    assert len(sg_docs) == num_of_docs

    # Replicate to CBL
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl = replicator.configure_and_replicate(cbl_db, target_url=sg_blip_url, continuous=True,
                                               replicator_authenticator=replicator_authenticator)

    repl = replicator.create(repl)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)
    cbl_doc_ids = db.getDocIds(cbl_db)
    assert len(cbl_doc_ids) == len(sg_docs)