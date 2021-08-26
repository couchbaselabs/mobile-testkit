import re
import pytest
import random
import time

from CBLClient.Authenticator import Authenticator
from CBLClient.Database import Database
from CBLClient.Document import Document
from CBLClient.Replication import Replication
from keywords import document
from keywords.MobileRestClient import MobileRestClient
from keywords.utils import host_for_url, random_string, log_info, get_event_changes
from libraries.data import doc_generators
from libraries.testkit import cluster
from utilities.cluster_config_utils import get_cluster


@pytest.fixture(scope="function")
def setup_teardown_test(params_from_base_test_setup):
    cbl_db_name = "cbl_db"
    base_url = params_from_base_test_setup["base_url"]
    db = Database(base_url)
    db_config = db.configure()
    log_info("Creating db")
    cbl_db = db.create(cbl_db_name, db_config)

    yield{
        "db": db,
        "cbl_db": cbl_db,
        "cbl_db_name": cbl_db_name
    }

    log_info("Deleting the db")
    db.deleteDB(cbl_db)


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.parametrize("replicator_direction", [
    pytest.param("pull", marks=pytest.mark.sanity),
    pytest.param("push"),
    ("pushAndPull")
])
def test_user_removed_from_channel_basic(params_from_base_test_setup, replicator_direction):
    """
        @summary:
        Channel Access Revocation Test Plan (CBL) #1
        1. on SGW create a user with channel A and channel B
        2. on SGW create 10 docs with channel A, and 15 docs with channel B, and 9 docs with channel A and B
        3. on CBL start a pull replicator with the user's credential to bring SGW docs to CBL
        4. assertion: doc count on CBL equals to docs on SGW, both are 34 (=10+15+9)
        5. on SGW remove the user from channel A
        6. on CBL, start replication with pull/push/push-pull replicator type
        7. assertion:
            pull/push-pull assertion: doc counts: CBL=24, 10 docs auto purged on CBL
            push: doc counts: CBL=34, auto-purge not impact for push only
    """
    sg_db = "db"
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    base_url = params_from_base_test_setup["base_url"]
    cbl_db = params_from_base_test_setup["source_db"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    db = params_from_base_test_setup["db"]

    if sync_gateway_version < "3.0.0" or liteserv_version < "3.0.0":
        pytest.skip('This test cannot run with version below 3.0')

    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    sg_client = MobileRestClient()

    # 1. on SGW create a user autotest with channel A and channel B
    channels_sg = ["A", "B"]
    username = "autotest"
    password = "password"
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels_sg)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, username)
    session = cookie, session_id

    # 2. on SGW create 10 docs with channel A, and 15 docs with channel B, and 9 docs with channel A and B
    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=10, id_prefix="CH_A_doc",
                       channels=["A"], auth=session)

    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=15, id_prefix="CH_B_doc",
                       channels=["B"], auth=session)

    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=9, id_prefix="CH_ANB_doc",
                       channels=channels_sg, auth=session)

    # 3. on CBL start a pull replicator with default purge config
    authenticator = Authenticator(base_url)
    replicator = Replication(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl = replicator.configure_and_replicate(source_db=cbl_db,
                                              target_url=sg_blip_url,
                                              continuous=True,
                                              replication_type="pull",
                                              replicator_authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    # 4. assertion: doc count on CBL equals to docs on SGW, both are 34
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)
    sg_doc_ids = [doc["id"] for doc in sg_docs["rows"]]

    cbl_doc_count = db.getCount(cbl_db)
    assert cbl_doc_count == 34, "Number of cbl docs is not equal to total number expected"
    cbl_doc_ids = db.getDocIds(cbl_db)
    for doc_id in sg_doc_ids:
        assert doc_id in cbl_doc_ids, "doc is missing during replication"

    # 5. on SGW remove the user from channel A
    sg_client.update_user(url=sg_admin_url, db=sg_db, name=username, channels=["B"])

    # 6. on CBL, start replication with pull/push/push-pull replicator type
    repl = replicator.configure_and_replicate(source_db=cbl_db,
                                              target_url=sg_blip_url,
                                              continuous=True,
                                              replication_type=replicator_direction,
                                              replicator_authenticator=replicator_authenticator)

    replicator.wait_until_replicator_idle(repl)

    # 7. assertion based on replicator type
    cbl_doc_count = db.getCount(cbl_db)
    cbl_doc_ids = db.getDocIds(cbl_db)
    if replicator_direction == "push":
        assert cbl_doc_count == 34, "local doc should not be impacted while channel revoked on sgw"
    else:
        assert cbl_doc_count == 24, "local doc should be purged while channel revoked on sgw"
        for doc_id in cbl_doc_ids:
            assert not doc_id.startswith("CH_A_doc")
            assert (doc_id.startswith("CH_B_doc") or doc_id.startswith("CH_ANB_doc"))


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.parametrize("replicator_direction", [
    pytest.param("pull", marks=pytest.mark.sanity),
    pytest.param("push"),
    ("pushAndPull")
])
def test_user_removed_from_channel_with_doc_mutation(params_from_base_test_setup, replicator_direction):
    """
        @summary:
        Channel Access Revocation Test Plan (CBL) #1
        1. on SGW create a user autotest with channel A and channel B
        2. on SGW create 10 docs with channel A, and 15 docs with channel B, and 9 docs with channel A and B
        3. on CBL start a pull replicator with the user credential
        4. assertion: doc count on CBL equals to docs on SGW, both are 34 (10 + 15 + 9)
        5. on SGW remove the user from channel A
        6. on cbl randomly pick some channel A docs and some docs belong to A and B, update a few times
        7. on CBL, start replication with pull/push/push-pull replicator type
        8. assertion based on replicator type
        9. create new docs on revoked channel, assertion: docs are not replicated to SGW
    """
    sg_db = "db"
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    base_url = params_from_base_test_setup["base_url"]
    cbl_db = params_from_base_test_setup["source_db"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    db = params_from_base_test_setup["db"]

    if sync_gateway_version < "3.0.0" or liteserv_version < "3.0.0":
        pytest.skip('This test cannot run with version below 3.0')

    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    sg_client = MobileRestClient()

    # 1. on SGW create a user autotest with channel A and channel B
    channels_sg = ["A", "B"]
    username = "autotest"
    password = "password"
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels_sg)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, username)
    session = cookie, session_id

    # 2. on SGW create 10 docs with channel A, and 15 docs with channel B, and 9 docs with channel A and B
    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=10, id_prefix="CH_A_doc",
                       channels=["A"], auth=session)

    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=15, id_prefix="CH_B_doc",
                       channels=["B"], auth=session)

    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=9, id_prefix="CH_ANB_doc",
                       channels=channels_sg, auth=session)

    # 3. on CBL start a pull replicator with the user credential
    authenticator = Authenticator(base_url)
    replicator = Replication(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl = replicator.configure_and_replicate(source_db=cbl_db,
                                              target_url=sg_blip_url,
                                              continuous=False,
                                              replication_type="pull",
                                              replicator_authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)

    # 4. assertion: doc count on CBL equals to docs on SGW, both are 34
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    assert len(sg_docs["rows"]) == 34, "Number of sg docs is not equal to total number expected"

    cbl_doc_count = db.getCount(cbl_db)
    assert len(sg_docs["rows"]) == cbl_doc_count, "Number of sg docs is not equal to total number of cbl docs"

    # 5. on SGW remove the user from channel A
    sg_client.update_user(url=sg_admin_url, db=sg_db, name=username, channels=["B"])

    # 6. on cbl randomly pick some channel A docs and some docs belong to A and B, update a few times
    channel_A_docs = []
    channel_ANB_docs = []
    cbl_doc_ids = db.getDocIds(cbl_db)
    for doc_id in cbl_doc_ids:
        if doc_id.startswith("CH_A_doc"):
            channel_A_docs.append(doc_id)
        if doc_id.startswith("CH_ANB_doc"):
            channel_ANB_docs.append(doc_id)
    db.update_bulk_docs(database=cbl_db, number_of_updates=3, doc_ids=random.sample(channel_A_docs, 2))
    db.update_bulk_docs(database=cbl_db, number_of_updates=2, doc_ids=random.sample(channel_ANB_docs, 3))

    # 7. on CBL, start replication with pull/push/push-pull replicator type
    repl = replicator.configure_and_replicate(source_db=cbl_db,
                                              target_url=sg_blip_url,
                                              continuous=False,
                                              replication_type=replicator_direction,
                                              replicator_authenticator=replicator_authenticator)

    replicator.wait_until_replicator_idle(repl)

    # 8. assertion based on replicator type
    cbl_doc_count = db.getCount(cbl_db)
    cbl_doc_ids = db.getDocIds(cbl_db)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    if replicator_direction == "pull":
        # pull replicator
        assert cbl_doc_count == 24, "Number of cbl docs is not expected"
        for doc_id in cbl_doc_ids:
            assert not doc_id.startswith("CH_A_doc"), "to be auto-purged doc is still accessible from cbl"
    elif replicator_direction == "push":
        # push replicator
        assert cbl_doc_count == 34, "Number of cbl docs is not expected"
    else:
        # push-pull replicator
        assert cbl_doc_count == 24, "Number of cbl docs is not expected"
        for doc_id in cbl_doc_ids:
            assert not doc_id.startswith("CH_A_doc"), "to be auto-purged doc is still accessible from cbl"

    # 9. create new docs on revoked channel, assertion: docs are not replicated to SGW
    new_doc_ids = db.create_bulk_docs(2, "CH_A_post_access_removal", db=cbl_db, channels=["A"])
    repl = replicator.configure_and_replicate(source_db=cbl_db,
                                              target_url=sg_blip_url,
                                              continuous=False,
                                              replication_type=replicator_direction,
                                              replicator_authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)

    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    sg_doc_ids = [doc["id"] for doc in sg_docs["rows"]]
    for doc_id in new_doc_ids:
        assert doc_id not in sg_doc_ids, "unaccessible docs got replicated to sync gateway"


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.parametrize("replicator_direction", [
    pytest.param("pull", marks=pytest.mark.sanity),
    pytest.param("push"),
    ("pushAndPull")
])
def test_user_removed_from_role(params_from_base_test_setup, replicator_direction):
    """
        @summary:
        1. on SGW create role1 and role2, create a user autotest belongs to role1, role2 and channel C
        2. on SGW create docs in channels
        3. on CBL, start a one-time pull replicator with the user credential and verify docs are replicated
        4. on CBL, start a new continuous replication with pull/push/push-pull replicator type
        5. on SGW remove the user from role1
        6. assertion based on replicator type
        7. if push-pull, create new docs, assertion: newly created docs not replicated to SGW
        8. on SGW remove the user from role2
        9. assertion based on replicator type
    """
    sg_db = "db"
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    base_url = params_from_base_test_setup["base_url"]
    cbl_db = params_from_base_test_setup["source_db"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    db = params_from_base_test_setup["db"]

    if sync_gateway_version < "3.0.0" or liteserv_version < "3.0.0":
        pytest.skip('This test cannot run with version below 3.0')

    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    sg_client = MobileRestClient()

    # 1. on SGW create role1 and role2, create a user autotest belongs to role1, role2 and channel C
    role1 = "R1"
    role2 = "R2"
    roles = [role1, role2]
    role1_channels = ["A", "B"]
    role2_channels = ["B", "C"]
    other_channels = ["C"]
    username = "autotest"
    password = "password"

    sg_client.create_role(url=sg_admin_url, db=sg_db, name=role1, channels=role1_channels)
    sg_client.create_role(url=sg_admin_url, db=sg_db, name=role2, channels=role2_channels)
    sg_client.create_user(sg_admin_url, sg_db, username, password=password, channels=other_channels, roles=roles)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, username)
    session = cookie, session_id

    # 2. on SGW create docs in channels
    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=10, id_prefix="CH_A_doc",
                       channels=["A"], auth=session)
    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=15, id_prefix="CH_B_doc",
                       channels=["B"], auth=session)
    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=9, id_prefix="CH_ANB_doc",
                       channels=["A", "B"], auth=session)
    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=7, id_prefix="CH_ANC_doc",
                       channels=["A", "C"], auth=session)
    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=5, id_prefix="CH_C_doc",
                       channels=["C"], auth=session)

    # 3. on CBL start a one-time pull replicator with the user credential and verify docs are replicated
    authenticator = Authenticator(base_url)
    replicator = Replication(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl = replicator.configure_and_replicate(source_db=cbl_db,
                                              target_url=sg_blip_url,
                                              continuous=False,
                                              replication_type="pull",
                                              replicator_authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)

    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    assert len(sg_docs["rows"]) == 46, "Number of sg docs is not equal to total number expected"

    cbl_doc_count = db.getCount(cbl_db)
    assert len(sg_docs["rows"]) == cbl_doc_count, "Number of sg docs is not equal to total number of cbl docs"

    # 4. on CBL, start a new continuous replication with pull/push/push-pull replicator type
    repl = replicator.configure_and_replicate(source_db=cbl_db,
                                              target_url=sg_blip_url,
                                              continuous=True,
                                              replication_type=replicator_direction,
                                              replicator_authenticator=replicator_authenticator)

    # 5. on SGW remove the user from role1
    sg_client.update_user(url=sg_admin_url, db=sg_db, name=username, channels=other_channels, roles=[role2])
    time.sleep(3)
    replicator.wait_until_replicator_idle(repl)

    # 6. assertion based on replicator type
    cbl_doc_count = db.getCount(cbl_db)
    cbl_doc_ids = db.getDocIds(cbl_db)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    if replicator_direction == "pull":
        # pull replicator
        assert cbl_doc_count == 36, "Number of cbl docs is not expected"
        for doc_id in cbl_doc_ids:
            assert not doc_id.startswith("CH_A_doc"), "to be auto-purged doc is still accessible from cbl"
    elif replicator_direction == "push":
        # push replicator
        assert cbl_doc_count == 46, "Number of cbl docs is not expected"
    else:
        # push-pull replicator
        assert cbl_doc_count == 36, "Number of cbl docs is not expected"
        for doc_id in cbl_doc_ids:
            assert not doc_id.startswith("CH_A_doc"), "to be auto-purged doc is still accessible from cbl"

        # 7. on push-pull, create new docs, assertion: newly created docs not replicated to SGW
        new_doc_ids_A = db.create_bulk_docs(2, "role1_removal_doc_on_channel_A", db=cbl_db, channels=["A"])
        new_doc_ids_B = db.create_bulk_docs(3, "role1_removal_doc_on_channel_B", db=cbl_db, channels=["B"])
        time.sleep(2)
        replicator.wait_until_replicator_idle(repl)

        sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
        sg_doc_ids = [doc["id"] for doc in sg_docs["rows"]]
        for doc_id in new_doc_ids_A:
            assert doc_id not in sg_doc_ids, "unaccessible docs got replicated to sync gateway"
        for doc_id in new_doc_ids_B:
            assert doc_id in sg_doc_ids, "docs on accessible channel should get replicated to sync gateway"

    # 8. on SGW remove the user from role2
    sg_client.update_user(url=sg_admin_url, db=sg_db, name=username, channels=other_channels, roles=[])
    time.sleep(3)
    replicator.wait_until_replicator_idle(repl)

    # 9. assertion based on replicator type
    cbl_doc_count = db.getCount(cbl_db)
    cbl_doc_ids = db.getDocIds(cbl_db)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)

    if replicator_direction == "pull":
        # pull replicator
        assert cbl_doc_count == 12, "Number of cbl docs is not expected"
        for doc_id in cbl_doc_ids:
            assert not doc_id.startswith("CH_A_doc"), "to be auto-purged doc is still accessible from cbl"
            assert not doc_id.startswith("CH_B_doc"), "to be auto-purged doc is still accessible from cbl"
            assert not doc_id.startswith("CH_ANB_doc"), "to be auto-purged doc is still accessible from cbl"
    elif replicator_direction == "push":
        # push replicator
        assert cbl_doc_count == 46, "Number of cbl docs is not expected"
    else:
        # push-pull replicator
        assert cbl_doc_count == 14, "Number of cbl docs is not expected"
        for doc_id in cbl_doc_ids:
            assert not doc_id.startswith("CH_A_doc"), "to be auto-purged doc is still accessible from cbl"
            assert not doc_id.startswith("CH_B_doc"), "to be auto-purged doc is still accessible from cbl"
            assert not doc_id.startswith("CH_ANB_doc"), "to be auto-purged doc is still accessible from cbl"

    replicator.stop(repl)


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.parametrize("replicator_type", [
    pytest.param("pull", marks=pytest.mark.sanity),
    pytest.param("push"),
    ("pushAndPull")
])
def test_users_role_revoked(params_from_base_test_setup, replicator_type):
    """
        @summary:
        1. on SGW create role1, and a user autotest belongs to role1 and channel C
        2. on SGW create docs on channels
        3. on CBL start a one-time pull replicator with the user credential, and verify docs are replicated to SGW
        4. on CBL, start a new continuous replication with pull/push/push-pull replicator type
        5. role1 lost access to channel A
        6. assertion based on replicator type
        7. if push-pull, create new docs, assert the newly created docs rejected by SGW
        8. on SGW role1 lost access to channel B as well
        9. assertion based on replicator type
    """
    sg_db = "db"
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    base_url = params_from_base_test_setup["base_url"]
    cbl_db = params_from_base_test_setup["source_db"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    db = params_from_base_test_setup["db"]

    if sync_gateway_version < "3.0.0" or liteserv_version < "3.0.0":
        pytest.skip('This test cannot run with version below 3.0')

    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    sg_client = MobileRestClient()

    # 1. on SGW create role1, and a user autotest belongs to role1 and channel C
    role1 = "R1"
    roles = [role1]
    role1_channels = ["A", "B"]
    other_channels = ["C"]
    username = "autotest"
    password = "password"

    sg_client.create_role(url=sg_admin_url, db=sg_db, name=role1, channels=role1_channels)
    sg_client.create_user(sg_admin_url, sg_db, username, password=password, channels=other_channels, roles=roles)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, username)
    session = cookie, session_id

    # 2. on SGW create docs on channels
    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=10, id_prefix="CH_A_doc",
                       channels=["A"], auth=session)
    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=15, id_prefix="CH_B_doc",
                       channels=["B"], auth=session)
    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=9, id_prefix="CH_ANB_doc",
                       channels=["A", "B"], auth=session)
    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=7, id_prefix="CH_ANC_doc",
                       channels=["A", "C"], auth=session)
    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=5, id_prefix="CH_C_doc",
                       channels=["C"], auth=session)

    # 3. on CBL start a one-time pull replicator with the user credential, and verify docs are replicated to SGW
    authenticator = Authenticator(base_url)
    replicator = Replication(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl = replicator.configure_and_replicate(source_db=cbl_db,
                                              target_url=sg_blip_url,
                                              continuous=False,
                                              replication_type="pull",
                                              replicator_authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)

    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    assert len(sg_docs["rows"]) == 46, "Number of sg docs is not equal to total number expected"

    cbl_doc_count = db.getCount(cbl_db)
    assert len(sg_docs["rows"]) == cbl_doc_count, "Number of sg docs is not equal to total number of cbl docs"

    # 4. on CBL, start a new continuous replication with pull/push/push-pull replicator type
    repl = replicator.configure_and_replicate(source_db=cbl_db,
                                              target_url=sg_blip_url,
                                              continuous=True,
                                              replication_type=replicator_type,
                                              replicator_authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)

    # 5. role1 lost access to channel A
    sg_client.update_role(url=sg_admin_url, db=sg_db, name=role1, channels=["B"])
    time.sleep(3)

    replicator.wait_until_replicator_idle(repl)

    # 6. assertion based on replicator type
    cbl_doc_count = db.getCount(cbl_db)
    cbl_doc_ids = db.getDocIds(cbl_db)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    if replicator_type == "pull":
        # pull replicator
        assert cbl_doc_count == 36, "Number of cbl docs is not expected"
        for doc_id in cbl_doc_ids:
            assert not doc_id.startswith("CH_A_doc"), "to be auto-purged doc is still accessible from cbl"
    elif replicator_type == "push":
        # push replicator
        assert cbl_doc_count == 46, "Number of cbl docs is not expected"
    else:
        # push-pull replicator
        assert cbl_doc_count == 36, "Number of cbl docs is not expected"
        for doc_id in cbl_doc_ids:
            assert not doc_id.startswith("CH_A_doc"), "to be auto-purged doc is still accessible from cbl"

    # 7. if push-pull, create new docs, assert the newly created docs rejected by SGW
    if replicator_type == "pushAndPull":
        new_doc_ids_A = db.create_bulk_docs(2, "role1_removal_doc_on_channel_A", db=cbl_db, channels=["A"])
        new_doc_ids_B = db.create_bulk_docs(3, "role1_removal_doc_on_channel_B", db=cbl_db, channels=["B"])
        replicator.wait_until_replicator_idle(repl)

        sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
        sg_doc_ids = [doc["id"] for doc in sg_docs["rows"]]
        for doc_id in new_doc_ids_A:
            assert doc_id not in sg_doc_ids, "unaccessible docs got replicated to sync gateway"
        for doc_id in new_doc_ids_B:
            assert doc_id in sg_doc_ids, "accessible docs were not replicated to sync gateway"

    # 8. on SGW role1 lost access to channel B as well
    sg_client.update_role(url=sg_admin_url, db=sg_db, name=role1, channels=[])
    time.sleep(3)

    replicator.wait_until_replicator_idle(repl)

    # 9. assertion based on replicator type
    cbl_doc_count = db.getCount(cbl_db)
    cbl_doc_ids = db.getDocIds(cbl_db)
    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
    if replicator_type == "pull":
        # pull replicator
        assert cbl_doc_count == 12, "Number of cbl docs is not expected"
        for doc_id in cbl_doc_ids:
            assert not doc_id.startswith("CH_A_doc"), "to be auto-purged doc is still accessible from cbl"
            assert not doc_id.startswith("CH_B_doc"), "to be auto-purged doc is still accessible from cbl"
            assert not doc_id.startswith("CH_ANB_doc"), "to be auto-purged doc is still accessible from cbl"
    elif replicator_type == "push":
        # push replicator
        assert cbl_doc_count == 46, "Number of cbl docs is not expected"
    else:
        # push-pull replicator
        assert cbl_doc_count == 14, "Number of cbl docs is not expected"
        for doc_id in cbl_doc_ids:
            assert not doc_id.startswith("CH_A_doc"), "to be auto-purged doc is still accessible from cbl"
            assert not doc_id.startswith("CH_B_doc"), "to be auto-purged doc is still accessible from cbl"
            assert not doc_id.startswith("CH_ANB_doc"), "to be auto-purged doc is still accessible from cbl"

    replicator.stop(repl)


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.parametrize("auto_purge_flag", [
    ("no_flag"),
    ("enabled"),
    ("disabled")
])
def test_auto_purge_config_settings(params_from_base_test_setup, auto_purge_flag):
    """
        @summary:
        1. on SGW create a user autotest with a channel
        2. on SGW create 10 docs with channel
        3. create replication with specified auto purge config setting, and verify docs are replicated
        4. on SGW remove the user from channel, and assert docs auto purge behavior
        5. reset disable_auto_purge to true, verify auto-purged will not be pulled down to CBL with reset checkpoint to true
    """
    sg_db = "db"
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    base_url = params_from_base_test_setup["base_url"]
    cbl_db = params_from_base_test_setup["source_db"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    db = params_from_base_test_setup["db"]

    if sync_gateway_version < "3.0.0" or liteserv_version < "3.0.0":
        pytest.skip('This test cannot run with version below 3.0')

    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    sg_client = MobileRestClient()

    # 1. on SGW create a user autotest with a channel
    channels_sg = ["CH_Flag"]
    username = "autotest"
    password = "password"
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels_sg)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, username)
    session = cookie, session_id

    # 2. on SGW create 10 docs with channel
    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=10, id_prefix="doc_for_auto_purge",
                       channels=channels_sg, auth=session)

    # 3. create replication with specified auto purge config setting, and verify docs are replicated
    authenticator = Authenticator(base_url)
    replicator = Replication(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    if auto_purge_flag == "enabled":
        log_info("start a replication and explicitly enable its auto purge")
        repl = replicator.configure_and_replicate(source_db=cbl_db,
                                                  target_url=sg_blip_url,
                                                  continuous=True,
                                                  replication_type="pull",
                                                  replicator_authenticator=replicator_authenticator,
                                                  auto_purge="enabled")
    elif auto_purge_flag == "disabled":
        log_info("start a replication and disable its auto purge setting")
        repl = replicator.configure_and_replicate(source_db=cbl_db,
                                                  target_url=sg_blip_url,
                                                  continuous=True,
                                                  replication_type="pull",
                                                  replicator_authenticator=replicator_authenticator,
                                                  auto_purge="disabled")
    elif auto_purge_flag == "no_flag":
        log_info("start a replication with default auto purge setting")
        repl = replicator.configure_and_replicate(source_db=cbl_db,
                                                  target_url=sg_blip_url,
                                                  continuous=True,
                                                  replication_type="pull",
                                                  replicator_authenticator=replicator_authenticator)

    replicator.wait_until_replicator_idle(repl)

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)
    assert len(sg_docs["rows"]) == 10, "Number of sg docs is not equal to total number expected"

    cbl_doc_count = db.getCount(cbl_db)
    assert cbl_doc_count == 10, "Number of cbl docs is not expected"

    # 4. on SGW remove the user from channel, and assert docs auto purge behavior
    sg_client.update_user(url=sg_admin_url, db=sg_db, name=username, channels=["B"])
    time.sleep(3)
    replicator.wait_until_replicator_idle(repl)

    cbl_doc_count = db.getCount(cbl_db)
    if auto_purge_flag == "disabled":
        assert cbl_doc_count == 10, "docs on cbl expected not to be auto purge"
    else:
        assert cbl_doc_count == 0, "docs on cbl expected to be auto purge"

    # 5. reset disable_auto_purge to true, verify auto-purged will not be pulled down to CBL with reset checkpoint to true
    repl_config = replicator.getConfig(repl)
    replicator.setAutoPurgeFlag(configuration=repl_config, auto_purge_flag=False)
    time.sleep(2)
    replicator.resetCheckPoint(repl)
    time.sleep(2)

    cbl_doc_count = db.getCount(cbl_db)
    if auto_purge_flag == "disabled":
        assert cbl_doc_count == 10, "docs on cbl expected not to be auto purge"
    else:
        assert cbl_doc_count == 0, "docs on cbl expected to be auto purge"
