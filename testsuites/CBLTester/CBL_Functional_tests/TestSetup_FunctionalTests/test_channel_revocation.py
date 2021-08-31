import pytest
import random
import time
import os
import subprocess
import zipfile
import io

from CBLClient.Authenticator import Authenticator
from CBLClient.Database import Database
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
    time.sleep(5)
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
        time.sleep(3)
        replicator.wait_until_replicator_idle(repl)

        sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session)
        sg_doc_ids = [doc["id"] for doc in sg_docs["rows"]]
        for doc_id in new_doc_ids_A:
            assert doc_id not in sg_doc_ids, "unaccessible docs got replicated to sync gateway"
        for doc_id in new_doc_ids_B:
            assert doc_id in sg_doc_ids, "docs on accessible channel should get replicated to sync gateway"

    # 8. on SGW remove the user from role2
    sg_client.update_user(url=sg_admin_url, db=sg_db, name=username, channels=other_channels, roles=[])
    time.sleep(5)
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
    time.sleep(5)

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
    time.sleep(5)

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
        repl_config = replicator.configure(source_db=cbl_db,
                                           target_url=sg_blip_url,
                                           continuous=True,
                                           replication_type="pull",
                                           replicator_authenticator=replicator_authenticator,
                                           auto_purge="enabled")
    elif auto_purge_flag == "disabled":
        log_info("start a replication and disable its auto purge setting")
        repl_config = replicator.configure(source_db=cbl_db,
                                           target_url=sg_blip_url,
                                           continuous=True,
                                           replication_type="pull",
                                           replicator_authenticator=replicator_authenticator,
                                           auto_purge="disabled")
    elif auto_purge_flag == "no_flag":
        log_info("start a replication with default auto purge setting")
        repl_config = replicator.configure(source_db=cbl_db,
                                           target_url=sg_blip_url,
                                           continuous=True,
                                           replication_type="pull",
                                           replicator_authenticator=replicator_authenticator)

    repl = replicator.create(repl_config)
    replicator.start(repl)
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
    replicator.stop(repl)
    replicator.setAutoPurgeFlag(configuration=repl_config, auto_purge_flag=False)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)

    replicator.resetCheckPoint(repl)
    time.sleep(2)

    cbl_doc_count = db.getCount(cbl_db)
    if auto_purge_flag == "disabled":
        assert cbl_doc_count == 10, "docs on cbl expected not to be auto purge"
    else:
        assert cbl_doc_count == 0, "docs on cbl expected to be auto purge"


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.parametrize("removal_access_type", [
    ("doc_removed_from_channel"),
    ("user_removed_from_channel")
])
def test_auto_purge_config_with_removal_type(params_from_base_test_setup, removal_access_type):
    """
        @summary:
        1. on SGW create a user autotest with a channel
        2. on SGW create 10 docs with channel and synced down to CBL
        3. create a replication, verify docs get replicated
        4. pick a doc id, remove doc access by access type
        5. verify doc auto purged on CBL
        6. disable auto_purge setting, verify auto-purged will not be pulled down to CBL even after reset checkpoint
    """
    sg_db = "db"
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_url = params_from_base_test_setup["sg_url"]
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

    # 2. on SGW create 10 docs with channel and synced down to CBL
    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=10, id_prefix="sg_doc",
                       channels=channels_sg, auth=session)

    # 3. create a replication, verify docs get replicated
    authenticator = Authenticator(base_url)
    replicator = Replication(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl_config = replicator.configure(source_db=cbl_db,
                                       target_url=sg_blip_url,
                                       continuous=True,
                                       replication_type="pull",
                                       replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)
    assert len(sg_docs["rows"]) == 10, "Number of sg docs is not equal to total number expected"

    cbl_doc_count = db.getCount(cbl_db)
    assert cbl_doc_count == 10, "Number of cbl docs is not expected"

    # 4. pick a doc id, remove doc access by access type
    picked_doc_id = "sg_doc_0"
    if removal_access_type == "doc_removed_from_channel":
        sg_client.update_doc(url=sg_url, db=sg_db, doc_id=picked_doc_id, auth=session, channels=["CH_Other"])
    elif removal_access_type == "user_removed_from_channel":
        sg_client.update_user(url=sg_admin_url, db=sg_db, name=username, channels=["B"])
    time.sleep(5)

    # 5. verify doc auto purged on CBL
    replicator.wait_until_replicator_idle(repl)
    purged_doc = db.getDocument(cbl_db, picked_doc_id)
    assert purged_doc == -1, "doc should have been purged"

    cbl_doc_count = db.getCount(cbl_db)
    if removal_access_type == "doc_removed_from_channel":
        assert cbl_doc_count == 9
        cbl_doc_ids = db.getDocIds(cbl_db)
        assert picked_doc_id not in cbl_doc_ids
    else:
        assert cbl_doc_count == 0

    # 6. disable auto_purge setting, verify auto-purged will not be pulled down to CBL even after reset checkpoint
    replicator.stop(repl)
    time.sleep(1)
    replicator.setAutoPurgeFlag(configuration=repl_config, auto_purge_flag=False)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)

    replicator.resetCheckPoint(repl)
    replicator.wait_until_replicator_idle(repl)
    purged_doc = db.getDocument(cbl_db, picked_doc_id)
    assert purged_doc == -1, "doc have been purged should not be brought down to CBL after reset checkpoint"

    replicator.stop(repl)


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.parametrize("auto_purge_flag", [
    ("enabled"),
    ("disabled")
])
def test_auto_purge_notification(params_from_base_test_setup, auto_purge_flag):
    """
        @summary:
        1. on SGW create a user autotest with a channel
        2. on SGW create docs with channel and synced down to CBL
        3. create a replication, disable auto purge config, verify docs replicated
        4. user revoked access to channel A
        5. Verifying the delete event in event captures
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

    # 2. on SGW create docs with channel and synced down to CBL
    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=10, id_prefix="doc_auto_purged",
                       channels=channels_sg, auth=session)

    # 3. create a replication, disable auto purge config, verify docs replicated
    authenticator = Authenticator(base_url)
    replicator = Replication(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    if auto_purge_flag == "disabled":
        repl_config = replicator.configure(source_db=cbl_db,
                                           target_url=sg_blip_url,
                                           continuous=True,
                                           replication_type="pull",
                                           replicator_authenticator=replicator_authenticator,
                                           auto_purge="disabled")
    else:
        repl_config = replicator.configure(source_db=cbl_db,
                                           target_url=sg_blip_url,
                                           continuous=True,
                                           replication_type="pull",
                                           replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    repl_delete_change_listener = replicator.addReplicatorEventChangeListener(repl)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)
    assert len(sg_docs["rows"]) == 10, "Number of sg docs is not equal to total number expected"

    cbl_doc_count = db.getCount(cbl_db)
    assert cbl_doc_count == 10, "Number of cbl docs is not expected"

    # 4. user revoked access to channel A
    sg_client.update_user(url=sg_admin_url, db=sg_db, name=username, channels=["B"])
    time.sleep(3)
    replicator.wait_until_replicator_idle(repl)

    # 5. Verifying the delete event in event captures
    doc_delete_event_changes = replicator.getReplicatorEventChanges(repl_delete_change_listener)
    event_dict = get_event_changes(doc_delete_event_changes)
    replicator.removeReplicatorEventListener(repl, repl_delete_change_listener)
    replicator.stop(repl)

    assert len(event_dict) != 0, "Replication listener didn't caught events."

    doc_id = "doc_auto_purged_1"
    flags = event_dict[doc_id]["flags"]
    assert flags == "2" or flags == "[ACCESS_REMOVED]" or flags == "AccessRemoved", \
        'Deleted flag is not tagged for document. Flag value: {}'.format(event_dict[doc_id]["flags"])


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.parametrize('auto_purge', [
    ("disabled"),
    ("enabled"),
])
def test_auto_purge_with_pull_filtering(params_from_base_test_setup, auto_purge):
    """
        @summary:
        TODO - NOT COMPLETED
        1. have SGW and CBL up and running
        2. on SGW create a user with channel A and channel B
        3. on SGW create 10 docs with channel A, and 15 docs with channel B, and 9 docs with channel A & B
        4. on CBL start a pull replicator with the user's credential to bring SGW docs to CBL
        5. assertion: doc count on CBL equals to docs on SGW, both are 34 (=10+15+9)
        6. on SGW remove the user from channel A
        7. on cbl randomly pick some channel A docs and some docs belong to A and B, update a few times
        8. on CBL start a (pull/push/push-pull one-time) replicator with the user's credential, and wait for replication to idle
        9. assertion:
            pull/push-pull assertion: doc counts: CBL=24, 10 docs auto purged on CBL
            push: doc counts: CBL=34, auto-purge not impact for push only
        10. on push-pull, create a new doc, assertion: doc counts: CBL=25 10 updated docs rejected by SGW
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
    liteserv_platform = params_from_base_test_setup["liteserv_platform"]
    log_file = params_from_base_test_setup["test_db_log_file"]
    test_cbllog = params_from_base_test_setup["test_cbllog"]

    if sync_gateway_version < "3.0.0" or liteserv_version < "3.0.0":
        pytest.skip('This test cannot run with version below 3.0')

    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    sg_client = MobileRestClient()

    delete_tmp_logs()  # Clean up tmp logs before test runs

    # 1. on SGW create a user autotest with channel A and channel B
    channels_sg = ["A", "B"]
    username = "autotest"
    password = "password"
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels_sg)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, username)
    session = cookie, session_id

    # 2. on SGW create 10 docs with channel A
    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=10, id_prefix="CH_A_doc",
                       channels=["A"], auth=session)

    # 3. on CBL start a one-time pull replicator with the user credential, and verify docs replicated
    authenticator = Authenticator(base_url)
    replicator = Replication(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl = replicator.configure_and_replicate(source_db=cbl_db,
                                              target_url=sg_blip_url,
                                              continuous=False,
                                              replication_type="pull",
                                              replicator_authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)
    assert len(sg_docs["rows"]) == 10, "Number of sg docs is not equal to total number expected"

    cbl_doc_count = db.getCount(cbl_db)
    assert cbl_doc_count == 10, "Number of cbl docs is not equal to total number expected"

    # 5. create a new replication, verify the doc lost access is not purged
    repl_config = replicator.configure(source_db=cbl_db,
                                       target_url=sg_blip_url,
                                       continuous=True,
                                       replication_type='pull',
                                       pull_filter=True,
                                       filter_callback_func='access_revoked',
                                       auto_purge=auto_purge,
                                       replicator_authenticator=replicator_authenticator)

    repl = replicator.create(repl_config)
    repl_delete_change_listener = replicator.addReplicatorEventChangeListener(repl)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)

    # 4. on SGW remove doc from channel
    sg_client.update_user(url=sg_admin_url, db=sg_db, name=username, channels=["B"])
    time.sleep(5)
    replicator.wait_until_replicator_idle(repl)

    cbl_doc_count = db.getCount(cbl_db)
    assert cbl_doc_count == 10, "auto purge expected not to happen"

    # 5. Verifying the delete event in event captures if auto purge is enabled
    if auto_purge == "enabled":
        doc_delete_event_changes = replicator.getReplicatorEventChanges(repl_delete_change_listener)
        event_dict = get_event_changes(doc_delete_event_changes)
        replicator.removeReplicatorEventListener(repl, repl_delete_change_listener)

        doc_id = "CH_A_doc_1"
        flags = event_dict[doc_id]["flags"]
        assert flags == "2" or flags == "[ACCESS_REMOVED]" or flags == "AccessRemoved", \
            'Deleted flag is not tagged for document. Flag value: {}'.format(event_dict[doc_id]["flags"])

        verify_doc_replication_rejection(liteserv_platform, log_file, test_cbllog)

    replicator.stop(repl)


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.parametrize("replicator_direction", [
    pytest.param("pull", marks=pytest.mark.sanity),
    ("pushAndPull")
])
def test_user_reassigned_to_channel_pull(params_from_base_test_setup, replicator_direction):
    """
        @summary:
        1. on SGW create a user autotest with channel A and channel B
        2. on SGW create 10 docs with channel A, and 15 docs with channel B
        3. on CBL start a pull replicator with the user credential
        4. assertion: doc count on CBL equals to docs on SGW, both are 25
        5. on SGW remove the user from channel A
        6. assertion channel A docs got purged
        7. reassign user access to channel A
        8. assertion channel A docs got pulled back
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

    # 2. on SGW create 10 docs with channel A, and 15 docs with channel B
    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=10, id_prefix="CH_A_doc",
                       channels=["A"], auth=session)

    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=15, id_prefix="CH_B_doc",
                       channels=["B"], auth=session)

    # 3. on CBL start a pull replicator with the user credential
    authenticator = Authenticator(base_url)
    replicator = Replication(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl = replicator.configure_and_replicate(source_db=cbl_db,
                                              target_url=sg_blip_url,
                                              continuous=True,
                                              replication_type=replicator_direction,
                                              replicator_authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)

    # 4. assertion: doc count on CBL equals to docs on SGW, both are 25
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)
    assert len(sg_docs["rows"]) == 25, "Number of sg docs is not equal to total number expected"

    cbl_doc_count = db.getCount(cbl_db)
    cbl_doc_ids = db.getDocIds(cbl_db)
    assert len(sg_docs["rows"]) == cbl_doc_count, "Number of sg docs is not equal to total number of cbl docs"

    channel_A_doc_ids = []
    for doc_id in cbl_doc_ids:
        if doc_id.startswith("CH_A_doc"):
            channel_A_doc_ids.append(doc_id)

    # 5. on SGW remove the user from channel A
    sg_client.update_user(url=sg_admin_url, db=sg_db, name=username, channels=["B"])
    time.sleep(3)
    replicator.wait_until_replicator_idle(repl)

    # 6. assertion channel A docs got purged
    cbl_doc_count = db.getCount(cbl_db)
    cbl_doc_ids = db.getDocIds(cbl_db)
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)
    assert cbl_doc_count == 15, "Number of cbl docs is not expected"
    for doc_id in cbl_doc_ids:
        assert not doc_id.startswith("CH_A_doc"), "to be auto-purged doc is still accessible from cbl"

    # 7. reassign user access to channel A
    sg_client.update_user(url=sg_admin_url, db=sg_db, name=username, channels=channels_sg)
    time.sleep(3)
    replicator.wait_until_replicator_idle(repl)

    # 8. assertion channel A docs got pulled back
    cbl_doc_count = db.getCount(cbl_db)
    cbl_doc_ids = db.getDocIds(cbl_db)
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)
    assert cbl_doc_count == 25, "Number of cbl docs is not expected"
    for doc_id in channel_A_doc_ids:
        assert doc_id in cbl_doc_ids, "docs expected to be pulled down after regain channel access are missing"

    replicator.stop(repl)


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.parametrize("with_doc_update", [
    pytest.param(False),
    pytest.param(True)
])
def test_user_reassigned_to_channel_push(params_from_base_test_setup, with_doc_update):
    """
        @summary:
        1. on SGW create a user autotest with channel A and channel B
        2. on SGW create 10 docs with channel A, and 15 docs with channel B
        3. on CBL start a one-time pull replicator, verify docs replicated
        4. on CBL, start a continous push replication
        5. on SGW remove the user from channel A, verify docs on channel A not impacted
        6. if required, update docs between last pull till user lost access
        7. reassign user access to channel A
        8. verify replication results after reassign
    """
    sg_db = "db"
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_url = params_from_base_test_setup["sg_url"]
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

    # 2. on SGW create 10 docs with channel A, and 15 docs with channel B
    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=10, id_prefix="CH_A_doc",
                       channels=["A"], auth=session)

    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=15, id_prefix="CH_B_doc",
                       channels=["B"], auth=session)

    # 3. on CBL start a one-time pull replicator, verify docs replicated
    authenticator = Authenticator(base_url)
    replicator = Replication(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl = replicator.configure_and_replicate(source_db=cbl_db,
                                              target_url=sg_blip_url,
                                              continuous=False,
                                              replication_type="pull",
                                              replicator_authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)
    assert len(sg_docs["rows"]) == 25, "Number of sg docs is not equal to total number expected"

    cbl_doc_count = db.getCount(cbl_db)
    assert len(sg_docs["rows"]) == cbl_doc_count, "Number of sg docs is not equal to total number of cbl docs"

    # 4. on CBL, start a continous push replication
    repl = replicator.configure_and_replicate(source_db=cbl_db,
                                              target_url=sg_blip_url,
                                              continuous=True,
                                              replication_type="push",
                                              replicator_authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)

    # 5. on SGW remove the user from channel A, verify docs on channel A not impacted
    sg_client.update_user(url=sg_admin_url, db=sg_db, name=username, channels=["B"])
    time.sleep(5)
    replicator.wait_until_replicator_idle(repl)

    cbl_doc_count = db.getCount(cbl_db)
    assert cbl_doc_count == 25, "Number of cbl docs is not expected"

    # 6. if required, update docs between last pull till user lost access
    if with_doc_update:
        cbl_doc_ids = db.getDocIds(cbl_db)
        channel_A_doc_ids = []
        for doc_id in cbl_doc_ids:
            if doc_id.startswith("CH_A_doc"):
                channel_A_doc_ids.append(doc_id)
        db.update_bulk_docs(database=cbl_db, number_of_updates=3, doc_ids=channel_A_doc_ids)

    # 7. reassign user access to channel A
    sg_client.update_user(url=sg_admin_url, db=sg_db, name=username, channels=channels_sg)
    time.sleep(5)
    replicator.wait_until_replicator_idle(repl)

    # 8. verify replication results after reassign
    cbl_doc_count = db.getCount(cbl_db)
    assert cbl_doc_count == 25, "Number of cbl docs is not expected"

    if with_doc_update:
        sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, include_docs=True, auth=session)
        for sg_doc in sg_docs["rows"]:
            if sg_doc["id"] in channel_A_doc_ids:
                assert sg_doc["doc"]["updates-cbl"] > 0, "doc update failed to replicate"

        replicator.resetCheckPoint(repl)
        time.sleep(3)
        replicator.wait_until_replicator_idle(repl)
        sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, include_docs=True, auth=session)
        for sg_doc in sg_docs["rows"]:
            if sg_doc["id"] in channel_A_doc_ids:
                assert sg_doc["doc"]["updates-cbl"] > 0, "doc update failed to replicate"

    replicator.stop(repl)


@pytest.mark.listener
@pytest.mark.channel_revocation
def test_tombstoned_doc_auto_purge(params_from_base_test_setup):
    """
        @summary:
        1. on SGW create a user autotest with channel A and channel B
        2. on SGW create docs with channel A, B and channel A and B
        3. on CBL start a pull replicator and verify docs replicated
        4. pick docs, make them tombstoned on SG and apply updates on CBL
        5. remove user access from channel A
        6. on CBL, start a new pull replication
        7. assertion based on replicator type
    """
    sg_db = "db"
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_url = params_from_base_test_setup["sg_url"]
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

    # 2. on SGW create docs with channel A, B and channel A and B
    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=10, id_prefix="CH_A_doc",
                       channels=["A"], auth=session)

    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=2, id_prefix="CH_B_doc",
                       channels=["B"], auth=session)

    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=5, id_prefix="CH_ANB_doc",
                       channels=channels_sg, auth=session)

    # 3. on CBL start a pull replicator and verify docs replicated
    authenticator = Authenticator(base_url)
    replicator = Replication(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl = replicator.configure_and_replicate(source_db=cbl_db,
                                              target_url=sg_blip_url,
                                              continuous=False,
                                              replication_type="pull",
                                              replicator_authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)
    assert len(sg_docs["rows"]) == 17, "Number of sg docs is not equal to total number expected"

    cbl_doc_count = db.getCount(cbl_db)
    assert len(sg_docs["rows"]) == cbl_doc_count, "Number of sg docs is not equal to total number of cbl docs"

    # 4. pick docs, make them tombstoned on SG and apply updates on CBL
    # pick a channel A doc, this doc expected to be auto-purged after lost channel access
    picked_ch_A_doc_id = "CH_A_doc_{}".format(random.randrange(10))
    # tombstone selected doc on SGW
    doc = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=picked_ch_A_doc_id, auth=session)
    sg_client.delete_doc(url=sg_url, db=sg_db, doc_id=picked_ch_A_doc_id, rev=doc['_rev'], auth=session)
    # update selected doc on CBL
    db.update_bulk_docs(database=cbl_db, number_of_updates=3, doc_ids=[picked_ch_A_doc_id])

    # pick a channel ANB doc, this doc not be impacted by channel access revokation but auto-purged due to tombstoned.
    picked_ch_ANB_doc_id = "CH_ANB_doc_{}".format(random.randrange(5))
    # tombstone selected doc on SGW
    doc = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=picked_ch_ANB_doc_id, auth=session)
    sg_client.delete_doc(url=sg_url, db=sg_db, doc_id=picked_ch_ANB_doc_id, rev=doc['_rev'], auth=session)

    # 5. remove user access from channel A
    sg_client.update_user(url=sg_admin_url, db=sg_db, name=username, channels=["B"])
    time.sleep(5)

    # 6. on CBL, start a new pull replication
    repl = replicator.configure_and_replicate(source_db=cbl_db,
                                              target_url=sg_blip_url,
                                              continuous=False,
                                              replication_type="pull",
                                              replicator_authenticator=replicator_authenticator)

    replicator.wait_until_replicator_idle(repl)

    # 7. assertion based on replicator type
    cbl_doc_count = db.getCount(cbl_db)
    cbl_doc_ids = db.getDocIds(cbl_db)

    assert cbl_doc_count == 6, "Number of cbl docs is not expected"
    for doc_id in cbl_doc_ids:
        assert not doc_id.startswith("CH_A_doc"), "doc to be auto-purged is still accessible from cbl"
        assert doc_id != picked_ch_ANB_doc_id, "tombstoned doc is not purged on CBL"


@pytest.mark.listener
@pytest.mark.channel_revocation
@pytest.mark.parametrize('resurrect_keep_body, deletion_type, resurrect_type', [
    (True, 'tombstone', 'api'),
    (True, 'tombstone', 'sdk'),
    (False, 'tombstone', 'api'),
    (False, 'tombstone', 'sdk'),
    (True, 'purge', 'api'),
    (True, 'purge', 'sdk'),
    (False, 'purge', 'api'),
    (False, 'purge', 'sdk')
])
def test_resurrected_doc_auto_purge(params_from_base_test_setup, resurrect_keep_body, deletion_type, resurrect_type):
    """
        @summary:
        1. on SGW create a user autotest with channel A and channel B
        2. on SGW create 10 docs with channel A, and 15 docs with channel B
        3. pick a doc, update several times
        4. on CBL start a pull replicator, verify docs replicated
        5. delete the picked doc
        6. doc resurrected
        7. on SGW remove the user from channel A
        8. on CBL, start replication with pull/push/push-pull replicator type
        9. assertion based on replicator type
    """
    sg_db = "db"
    cluster_topology = params_from_base_test_setup['cluster_topology']
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_url = params_from_base_test_setup["sg_url"]
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

    # 2. on SGW create 10 docs with channel A, and 15 docs with channel B
    sg_client.add_docs(url=sg_url, db=sg_db, number=10, id_prefix="CH_A_doc",
                       channels=["A"], auth=session)

    sg_client.add_docs(url=sg_url, db=sg_db, number=15, id_prefix="CH_B_doc",
                       channels=["B"], auth=session)

    # 3. pick a doc, update several times
    picked_doc_id = "CH_A_doc_{}".format(random.randrange(10))
    picked_doc_rev_1 = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=picked_doc_id, auth=session)

    for i in range(5):
        sg_client.update_doc(url=sg_url, db=sg_db, doc_id=picked_doc_id, number_updates=1, auth=session, property_updater=property_updater)

    # 4. on CBL start a pull replicator, verify docs replicated
    authenticator = Authenticator(base_url)
    replicator = Replication(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl = replicator.configure_and_replicate(source_db=cbl_db,
                                              target_url=sg_blip_url,
                                              continuous=False,
                                              replication_type="pull",
                                              replicator_authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)
    assert len(sg_docs["rows"]) == 25, "Number of sg docs is not equal to total number expected"

    cbl_doc_count = db.getCount(cbl_db)
    assert len(sg_docs["rows"]) == cbl_doc_count, "Number of sg docs is not equal to total number of cbl docs"

    # 5. delete the picked doc
    doc = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=picked_doc_id, auth=session)
    if deletion_type == "tombstone":
        deleted = sg_client.delete_doc(url=sg_url, db=sg_db, doc_id=picked_doc_id, rev=doc['_rev'], auth=session)
        log_info('tombstone doc via Sync Gateway')
        log_info(deleted)
    elif deletion_type == "purge":
        log_info('Purging doc via Sync Gateway')
        sg_client.purge_doc(url=sg_admin_url, db=sg_db, doc=doc)

    # 6. doc resurrected
    doc_body = {}
    if resurrect_keep_body:
        doc_body = get_doc_body(picked_doc_rev_1)
    else:
        doc_body = doc_generators.simple()
        doc_body = document.create_doc(doc_id=picked_doc_id, content=doc_generators.simple(), channels=["A"])

    if resurrect_type == "api":
        sg_client.add_doc(url=sg_url, db=sg_db, doc=doc_body, auth=session)
    elif resurrect_type == "sdk":
        cbs_url = cluster_topology['couchbase_servers'][0]
        cbs_host = host_for_url(cbs_url)
        bucket_name = "travel-sample"

        if ssl_enabled and c.ipv6:
            connection_url = "couchbases://{}?ssl=no_verify&ipv6=allow".format(cbs_host)
        elif ssl_enabled and not c.ipv6:
            connection_url = "couchbases://{}?ssl=no_verify".format(cbs_host)
        elif not ssl_enabled and c.ipv6:
            connection_url = "couchbase://{}?ipv6=allow".format(cbs_host)
        else:
            connection_url = 'couchbase://{}'.format(cbs_host)
        sdk_client = get_cluster(connection_url, bucket_name)

        sdk_docs = {picked_doc_id: doc_body}
        log_info('Creating SDK docs')
        sdk_client.upsert_multi(sdk_docs)
    time.sleep(5)

    # 7. on SGW remove the user from channel A
    sg_client.update_user(url=sg_admin_url, db=sg_db, name=username, channels=["B"])
    time.sleep(5)

    # 8. on CBL, start replication with pull/push/push-pull replicator type
    repl = replicator.configure_and_replicate(source_db=cbl_db,
                                              target_url=sg_blip_url,
                                              continuous=False,
                                              replication_type="pull",
                                              replicator_authenticator=replicator_authenticator)

    replicator.wait_until_replicator_idle(repl)

    # 9. assertion based on replicator type
    cbl_doc_count = db.getCount(cbl_db)
    assert cbl_doc_count == 15, "Number of cbl docs is not expected"
    cbl_doc_ids = db.getDocIds(cbl_db)
    for doc_id in cbl_doc_ids:
        assert not doc_id.startswith("CH_A_doc"), "to be auto-purged doc is still accessible from cbl"


@pytest.mark.listener
@pytest.mark.channel_revocation
def test_role_ressignment_end_to_end(params_from_base_test_setup):
    """
        @summary:
        1. on SGW create role1 and role2, create user1 in role1 and user2 in role2
        2. on SGW create docs in channels
        3. on CBL start a continous push-pull replication with user1, verify docs replicated
        4. on SGW grant role2 to user1, verify docs belong to channel B get replicated
        5. create some docs on channel B
        6. user1 is revoked role2, verify docs purged
    """
    sg_db = "db"
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_url = params_from_base_test_setup["sg_url"]
    base_url = params_from_base_test_setup["base_url"]
    cbl_db = params_from_base_test_setup["source_db"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    db = params_from_base_test_setup["db"]

    if sync_gateway_version < "3.0.0" or liteserv_version < "3.0.0":
        pytest.skip('This test cannot run with version below 3.0')

    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    sg_client = MobileRestClient()

    # 1. on SGW create role1 and role2, create user1 in role1 and user2 in role2
    role1 = "R1"
    role2 = "R2"
    roles = [role1, role2]
    role1_channels = ["A"]
    role2_channels = ["A", "B"]
    username1 = "autotest"
    username2 = "admintest"
    password = "password"

    # role1 access channel A
    sg_client.create_role(url=sg_admin_url, db=sg_db, name=role1, channels=role1_channels)
    # role2 access channel A and channel B
    sg_client.create_role(url=sg_admin_url, db=sg_db, name=role2, channels=role2_channels)
    # user1 access channel A
    sg_client.create_user(sg_admin_url, sg_db, username1, password=password, roles=[role1])
    # user2 access channel A and channel B
    sg_client.create_user(sg_admin_url, sg_db, username2, password=password, roles=roles)
    cookie1, session_id1 = sg_client.create_session(sg_admin_url, sg_db, username1)
    session1 = cookie1, session_id1
    cookie2, session_id2 = sg_client.create_session(sg_admin_url, sg_db, username2)
    session2 = cookie2, session_id2

    # 2. on SGW create docs in channels
    # create docs with user1
    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=10, id_prefix="CH_A_doc",
                       channels=["A"], auth=session1)
    # create docs with user2
    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=15, id_prefix="CH_B_doc",
                       channels=["B"], auth=session2)
    sg_client.add_docs(url=sg_admin_url, db=sg_db, number=9, id_prefix="CH_ANB_doc",
                       channels=["A", "B"], auth=session2)

    # 3. on CBL start a continous push-pull replication with user1, verify docs replicated
    authenticator = Authenticator(base_url)
    replicator = Replication(base_url)
    replicator_authenticator = authenticator.authentication(session_id1, cookie1, authentication_type="session")
    repl = replicator.configure_and_replicate(source_db=cbl_db,
                                              target_url=sg_blip_url,
                                              continuous=True,
                                              replication_type="pushAndPull",
                                              replicator_authenticator=replicator_authenticator)
    replicator.wait_until_replicator_idle(repl)

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)
    assert len(sg_docs["rows"]) == 34, "Number of sg docs is not equal to total number expected"

    cbl_doc_count = db.getCount(cbl_db)
    assert cbl_doc_count == 19, "Number of cbl docs is not equal to total number expected"

    # 4. on SGW grant role2 to user1, verify docs belong to channel B get replicated
    sg_client.update_user(url=sg_admin_url, db=sg_db, name=username1, roles=roles)
    time.sleep(3)
    replicator.wait_until_replicator_idle(repl)

    cbl_doc_count = db.getCount(cbl_db)
    assert cbl_doc_count == 34, "Number of cbl docs is not expected"

    # 5. create some docs on channel B
    db.create_bulk_docs(3, "additional_CH_B_doc", db=cbl_db, channels=["B"])
    replicator.wait_until_replicator_idle(repl)

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db)
    assert len(sg_docs["rows"]) == 37, "Number of sg docs is not expected"

    sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=session1)
    assert len(sg_docs["rows"]) == 37, "Number of sg docs is not expected"

    # 6. user1 is revoked role2, verify docs purged
    sg_client.update_user(url=sg_admin_url, db=sg_db, name=username1, roles=[role1])
    time.sleep(5)
    replicator.wait_until_replicator_idle(repl)

    cbl_doc_count = db.getCount(cbl_db)
    assert cbl_doc_count == 19, "Number of cbl docs is not expected"

    cbl_doc_ids = db.getDocIds(cbl_db)
    for doc_id in cbl_doc_ids:
        assert not doc_id.startswith("CH_B_doc"), "to be auto-purged doc is still accessible from cbl"
        assert not doc_id.startswith("additional_CH_B_doc"), "to be auto-purged doc is still accessible from cbl"

    replicator.stop(repl)


def property_updater(doc_body):
    doc_body["sg_new_update1"] = random_string(length=20)
    doc_body["sg_new_update2"] = random_string(length=20)

    return doc_body


def get_doc_body(doc_body):
    del doc_body['_rev']
    del doc_body['_revisions']

    return doc_body


def verify_doc_replication_rejection(liteserv_platform, log_file, test_cbllog):
    """
       @note: Porting logs for Android, xamarin-android, net-core and net-uwp platform, as the logs reside
           outside runner's file directory
    """
    delimiter = "/"
    if "-msft" in liteserv_platform or liteserv_platform == "uwp":
        delimiter = "\\"
    log_dir = log_file.split(delimiter)[-1]
    log_full_path_dir = "/tmp/cbl-logs/"
    os.mkdir(log_full_path_dir)
    log_info("\n Collecting logs")
    zip_data = test_cbllog.get_logs_in_zip()
    if zip_data == -1:
        raise Exception("Failed to get zip log files from CBL app")
    test_log_zip_file = "cbl_log.zip"
    test_log = os.path.join(log_full_path_dir, test_log_zip_file)
    log_info("Log file for failed test is: {}".format(test_log_zip_file))

    target_zip = zipfile.ZipFile(test_log, 'w')
    with zipfile.ZipFile(io.BytesIO(zip_data)) as thezip:
        for zipinfo in thezip.infolist():
            target_zip.writestr(zipinfo.filename, thezip.read(zipinfo.filename))
    target_zip.close()

    # unzipping the zipped log files
    log_dir_path = os.path.join(log_full_path_dir, log_dir)
    if zipfile.is_zipfile(test_log):
        with zipfile.ZipFile(test_log, 'r') as zip_ref:
            zip_ref.extractall(log_full_path_dir)

    log_info("Checking {} for copied log files - {}".format(log_dir_path, os.listdir(log_dir_path)))
    log_file = subprocess.check_output("ls -t {} | head -1".format(log_dir_path), shell=True)
    assert len(os.listdir(log_dir_path)) != 0, "Log files are not available at {}".format(log_dir_path)
    command = "grep '{}' {}/*.cbllog | wc -l".format("WebSocket error 403", log_dir_path)
    log_info("Running command: {}".format(command))
    output = subprocess.check_output(command, shell=True)
    output = int(output.strip())
    assert output != 0, "WebSocket error 403 is expected"

    command = "grep '{}' {}/*.cbllog | wc -l".format("rejected by validation function", log_dir_path)
    log_info("Running command: {}".format(command))
    output = subprocess.check_output(command, shell=True)
    output = int(output.strip())
    assert output != 0, "rejected by validation function is expected"


def delete_tmp_logs():
    del_output = subprocess.check_output("rm -rf /tmp/cbl-logs", shell=True)
    log_info("delete output is ", del_output)
