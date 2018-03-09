import pytest

from keywords.MobileRestClient import MobileRestClient
from keywords import document
from CBLClient.Replication import Replication
from CBLClient.Authenticator import Authenticator
from libraries.testkit import cluster
from CBLClient.Document import Document


def create_doc_from_document(doc_id, content, channel):
    return document.create_doc(doc_id=doc_id, content=content, channels=channel)


@pytest.mark.listener
@pytest.mark.parametrize("concurrencyType", [
    ("lastWriteWins"),
    ("failOnConflict")
])
def test_replication_with_concurrencyControl_sameDocId_createUpdate(params_from_base_test_setup, concurrencyType):
    """
    @summary:
    1. Create document id = doc1 as doc1a instance
    2. Create document id = doc1 as doc1b instance
    3. Save doc1a
    4. Save doc1b (success for LastWriteWins, fail for FailOnConflict)
    5. update document 
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    base_url = params_from_base_test_setup["base_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    channel = ["Replication-1"]
    doc_id = "doc_1"
    documentObj = Document(base_url)
    
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 1. Create document id = doc1 as doc1a instance
    doc_body = create_doc_from_document(doc_id=doc_id, content="doc1", channel=channel)
    mutable_doc1 = documentObj.create(doc_id, doc_body)

    # 2. Create document id = doc1 as doc1b instance
    doc_body2 = create_doc_from_document(doc_id=doc_id, content="doc2", channel=channel)
    mutable_doc2 = documentObj.create(doc_id, doc_body2)
    db.saveDocumentWithConcurrency(cbl_db, mutable_doc1, concurrencyType)
    db.saveDocumentWithConcurrency(cbl_db, mutable_doc2, concurrencyType)

    # 3. Get cbl docs
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    for id in cbl_doc_ids:
        if concurrencyType == "lastWriteWins":
            assert cbl_docs[id]["content"] == "doc2", "last write wins did not succeed"
        else:
            assert cbl_docs[id]["content"] == "doc1", "Fail on conflict did not work"

    # 4. update doc with first update
    document = db.getDocument(cbl_db, doc_id)
    document2 = db.getDocument(cbl_db, doc_id)
    doc_mut = documentObj.toMutable(document)
    doc_body1 = documentObj.toMap(doc_mut)
    doc_body1["concurrencyType"] = "concurrency1"
    saved_doc1 = documentObj.setData(doc_mut, doc_body1)
    db.saveDocument(cbl_db, saved_doc1)

    # update same doc to have conflict with second update
    doc_mut2 = documentObj.toMutable(document2)
    doc_body2 = documentObj.toMap(doc_mut2)
    doc_body2["concurrencyType"] = "concurrency2"
    saved_doc2 = documentObj.setData(doc_mut2, doc_body2)
    db.saveDocumentWithConcurrency(cbl_db, saved_doc2, concurrencyType)
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, cbl_doc_ids)

    for id in cbl_doc_ids:
        if concurrencyType == "lastWriteWins":
            assert cbl_docs[id]["concurrencyType"] == "concurrency2", "last write wins did not succeed"
        else:
            assert cbl_docs[id]["concurrencyType"] == "concurrency1", "Fail on conflict did not work"


@pytest.mark.listener
@pytest.mark.parametrize("concurrencyType", [
    ("lastWriteWins"),
    # ("failOnConflict")
])
def test_replication_with_concurrencyControl_deleteSameDocId(params_from_base_test_setup, concurrencyType):
    """
    @summary:
    1. Create document id = doc1 as doc1a instance
    2. Get the cbl doc and update the doc with concurrency
    3. delete same doc with concurrency
    4. Verify  (success for LastWriteWins, fail for FailOnConflict)
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    base_url = params_from_base_test_setup["base_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    channel = ["Replication-1"]
    doc_id = "doc_1"
    documentObj = Document(base_url)

    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 1. Create document id = doc1 as doc1a instance
    doc_body = document.create_doc(doc_id=doc_id, content="doc1", channels=channel)
    mutable_doc1 = documentObj.create(doc_id, doc_body)
    db.saveDocument(cbl_db, mutable_doc1)

    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_doc = db.getDocument(cbl_db, doc_id)
    doc_mut = documentObj.toMutable(cbl_doc)
    doc_body = documentObj.toMap(doc_mut)
    doc_body["concurrencyType"] = "concurrency1"
    saved_doc = documentObj.setData(doc_mut, doc_body)
    db.saveDocument(cbl_db, saved_doc)

    db.saveDocument(cbl_db, saved_doc)

    db.deleteDocumentWithConcurrency(cbl_db, cbl_doc, concurrencyType)

    if concurrencyType == "lastWriteWins":
        cbl_doc_ids = db.getDocIds(cbl_db)
        assert len(cbl_doc_ids) == 0, "last write wins did not succeed"
    else:
        cbl_doc = db.getDocument(cbl_db, doc_id)
        doc_mut = documentObj.toMutable(cbl_doc)
        doc_body = documentObj.toMap(doc_mut)
        assert doc_body["concurrencyType"] == "concurrency1", "Fail on conflict did not work"


@pytest.mark.parametrize("concurrencyType", [
    ("lastWriteWins"),
    ("failOnConflict")
])
def test_replication_with_concurrencyControl_sgCBL_sameDocId(params_from_base_test_setup, concurrencyType):
    """
    @summary:
    1. Create document id = doc1 as doc1a instance on SG
    2. start replication to cbl.
    3. Create document id = doc1 as doc1b instance on CBL
    4. save document
    5. Save doc1b (success for LastWriteWins, fail for FailOnConflict)
    """

    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    channel = ["Replication-1"]
    username = "autotest"
    password = "password"
    doc_id = "doc_1"

    sg_client = MobileRestClient()
    authenticator = Authenticator(base_url)
    documentObj = Document(base_url)

    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    sg_client.create_user(sg_admin_url, sg_db, username, password=password, channels=channel)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
    session = cookie, session_id

    # 1. Create document id = doc1 as doc1a instance on SG
    sg_doc_body = document.create_doc(doc_id=doc_id, content="sg-doc1", channels=channel)
    sg_client.add_doc(url=sg_url, db=sg_db, doc=sg_doc_body, auth=session)

    # 2. start replication to cbl.
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    replicator.configure_and_replicate(source_db=cbl_db, replicator_authenticator=replicator_authenticator, target_url=sg_blip_url,
                                       replication_type="push_pull", continuous=False, channels=channel)
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    # 1. Create document id = doc1 as doc1a instance
    doc_body = document.create_doc(doc_id=doc_id, content="doc1", channels=channel)
    mutable_doc = documentObj.create(doc_id, doc_body)

    # db.saveDocumentWithConcurrency(cbl_db, mutable_doc1, concurrencyType)
    db.saveDocumentWithConcurrency(cbl_db, mutable_doc, concurrencyType)

    # 3. Get cbl docs
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    for id in cbl_doc_ids:
        if concurrencyType == "lastWriteWins":
            assert cbl_docs[id]["content"] == "doc1", "last write wins did not succeed"
        else:
            assert cbl_docs[id]["content"] == "sg-doc1", "Fail on conflict did not work"
