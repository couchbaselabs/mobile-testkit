import pytest
import time

from keywords.MobileRestClient import MobileRestClient
from keywords.utils import random_string
from CBLClient.Database import Database
from CBLClient.Replication import Replication
from CBLClient.Document import Document
from CBLClient.Authenticator import Authenticator
from keywords import document
from CBLClient.Dictionary import Dictionary
from libraries.testkit import cluster
from CBLClient.ReplicatorCallback import ReplicatorCallback
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf
from keywords.utils import get_event_changes
from libraries.data import doc_generators
from keywords.utils import deep_dict_compare


@pytest.mark.listener
@pytest.mark.callback
@pytest.mark.sanity
def test_basic_replication_with_encryption(params_from_base_test_setup):
    """
    @summary:
    Create various types of Encrypted values.
    https://docs.google.com/spreadsheets/d/1-E7qv8UlR3-AyhaKvagsFtwB-i4JOBZWGKHJn6JDSqY/edit#gid=0
    test1,2,7,9,10

    1. Have SG and CBL up and running
    2. Create a simple document with encryption property (String, int, Double, Float, dict , Array, and Dict)
    3. Start the replicator and make sure documents are
    replicated on SG. Verify encrypted fields and Verify data is encrypted.
    4.  Verify Updates on the Encrypted doc on CBL
    5.  Start the replicator and verify the docs
    6. Verify Delete on the Encrypted document on CBL and replicate
    """

    liteserv_platform = params_from_base_test_setup["liteserv_platform"]
    if "c-" not in liteserv_platform.lower():
        pytest.skip('This test cannot run other than C.')

    sg_db = "db"
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    number_of_updates = 2
    sg_client = MobileRestClient()

    if sync_gateway_version < "2.0.0":
        pytest.skip('This test cannot run with sg version below 2.0')
    channels_sg = ["ABCD"]
    username = "autotest"
    password = "password"
    # 1. Have SG and CBL up and running
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create docs in CBL
    doc_id = "doc_3"
    documentObj = Document(base_url)
    doc_body = document.create_doc(doc_id=doc_id, content="doc3", channels=channels_sg, non_sgw=True)
    dictionary = Dictionary(base_url)
    mutable = dictionary.toMutableDictionary(doc_body)
    encryptable = ReplicatorCallback(base_url)

    # 2. Create a simple document with encryption property (String, int, Double, Float, dict , Array, and Dict)
    dict2 = dictionary.toMutableDictionary(
        {"balance": "$2,393.65", "picture": "http://placehold.it/32x32", "email": "ofeliasears@imageflow.com",
         "phone": "+1 (939) 542-2185"})
    encrypted_value = encryptable.create("Dict", dict2)
    # Add the encrypted key value in the document dictionary
    dictionary.setEncryptable(mutable, "encrypted_field", encrypted_value)
    encrypted_value = encryptable.create("Bool", True)
    dictionary.setEncryptable(mutable, "encrypted_field", encrypted_value)

    encrypted_value = encryptable.create("Null")
    dictionary.setEncryptable(mutable, "encrypted_field", encrypted_value)
    encrypted_value = encryptable.create("Double", 19.340320403204324)
    dictionary.setEncryptable(mutable, "encrypted_field_Double", encrypted_value)
    encrypted_value = encryptable.create("UInt", 4294967295)
    dictionary.setEncryptable(mutable, "encrypted_field_UInt", encrypted_value)

    encrypted_value = encryptable.create("String", "Testt&#[{()_/^%@")
    dictionary.setEncryptable(mutable, "encrypted_field_String", encrypted_value)
    encrypted_value = encryptable.create("Int", 1234)
    dictionary.setEncryptable(mutable, "encrypted_field_Int", encrypted_value)
    encrypted_value = encryptable.create("UInt", 4294967295)
    dictionary.setEncryptable(mutable, "encrypted_field_Uint", encrypted_value)

    doc_body_new = dictionary.toMap(mutable)
    doc1 = documentObj.create(doc_id, doc_body_new)
    db.saveDocument(cbl_db, doc1)

    # Create an encryptor for replicator
    encryptor = encryptable.createEncryptor("xor", "testkit")

    # 3. Start the replicator and make sure documents are
    #     replicated on SG. Verify encrypted fields and Verify data is encrypted.
    replicator = Replication(base_url)
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels_sg)
    session, replicator_authenticator, repl = replicator.create_session_configure_replicate(base_url, sg_admin_url,
                                                                                            sg_db, username, password,
                                                                                            channels_sg,
                                                                                            sg_client, cbl_db,
                                                                                            sg_blip_url,
                                                                                            continuous=True,
                                                                                            encryptor=encryptor)

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True)
    sg_docs = sg_docs["rows"]

    # Assert encrypted fields in the SG
    assert "alg" and "ciphertext" and "kid" in sg_docs[0]["doc"]['encrypted$encrypted_field_String'], \
        "All required fields are not present in the encrypted data"
    assert "testkit_data" not in sg_docs[0]["doc"]['encrypted$encrypted_field_String']["ciphertext"], \
        "Data is not encrypted in the SG"

    # Verify database doc counts in CBL
    cbl_doc_count = db.getCount(cbl_db)
    assert len(sg_docs) == cbl_doc_count, "Expected number of docs does not exist in sync-gateway after replication"

    # 4.  Verify Updates on the Encrypted doc on CBL
    db.update_bulk_docs(database=cbl_db, number_of_updates=number_of_updates)
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_db_docs = db.getDocuments(cbl_db, cbl_doc_ids)

    # Update encrypted field data in the CBL DOC
    # 5.  Start the replicator and verify the docs
    for doc in cbl_db_docs:
        doc_body = cbl_db_docs[doc]
        mutable = dictionary.toMutableDictionary(doc_body)
        encrypted_value = encryptable.create("String", "Test-update&#[{()_/^%@")
        dictionary.setEncryptable(mutable, "encrypted_field_String", encrypted_value)
        doc_body_new = dictionary.toMap(mutable)
        updated_docs = {doc: doc_body_new}
        db.updateDocuments(cbl_db, updated_docs)

    for doc in cbl_doc_ids:
        assert cbl_db_docs[doc]["updates-cbl"] == number_of_updates, "updates-cbl did not get updated"

    replicator.wait_until_replicator_idle(repl)

    # 6. Verify Delete on the Encrypted document on CBL and replicate
    # Delete all documents Verify that docs with encrypted fields are deleted.
    db.cbl_delete_bulk_docs(cbl_db)
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_docs = db.getDocuments(cbl_db, cbl_doc_ids)
    assert len(cbl_docs) == 0, "did not delete docs after delete operation"
    replicator.wait_until_replicator_idle(repl)
    total = replicator.getTotal(repl)
    completed = replicator.getCompleted(repl)
    replicator.stop(repl)
    assert total == completed, "total is not equal to completed"
    time.sleep(30)
    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True)
    assert len(sg_docs["rows"]) == 0, "did not delete docs after delete operation"


@pytest.mark.listener
@pytest.mark.callback
def test_replication_with_error(params_from_base_test_setup):
    """
    @summary:
    Verify Event Error code without the encryptor
    https://docs.google.com/spreadsheets/d/1-E7qv8UlR3-AyhaKvagsFtwB-i4JOBZWGKHJn6JDSqY/edit#gid=0
    test3,6

    1. Have SG and CBL up and running
    2. Create a simple document with encryption property (String)
    3. Configure replicator without the encryptor. Start the replicator with event listener
    4.  Verify event listener for error codes
    5.  Verify event listener for error domain
    """

    liteserv_platform = params_from_base_test_setup["liteserv_platform"]
    if "c-" not in liteserv_platform.lower():
        pytest.skip('This test cannot run in other than C CBLs.')

    sg_db = "db"
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    sg_client = MobileRestClient()

    if sync_gateway_version < "2.0.0":
        pytest.skip('This test cannot run with sg version below 2.0')
    channels_sg = ["ABCD"]
    username = "autotest"
    password = "password"

    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create docs in CBL
    doc_id = "doc_3"
    documentObj = Document(base_url)
    doc_body = document.create_doc(doc_id=doc_id, content="doc3", channels=channels_sg, non_sgw=True)
    dictionary = Dictionary(base_url)
    mutable = dictionary.toMutableDictionary(doc_body)
    replicator_callback = ReplicatorCallback(base_url)

    # 2.Create a simple document with encryption property (String)
    encrypted_value = replicator_callback.create("UInt", 4294967295)
    dictionary.setEncryptable(mutable, "encrypted_field_Uint", encrypted_value)

    doc_body_new = dictionary.toMap(mutable)
    doc1 = documentObj.create(doc_id, doc_body_new)
    db.saveDocument(cbl_db, doc1)

    # Configure replication with push/pull
    replicator = Replication(base_url)
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels_sg)

    cookie, session = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username)
    sync_cookie = "{}={}".format(cookie, session)
    session_header = {"Cookie": sync_cookie}
    repl_config = replicator.configure(source_db=cbl_db,
                                       target_url=sg_blip_url,
                                       continuous=True,
                                       headers=session_header)
    repl = replicator.create(repl_config)

    # 3. Configure replicator without the encryptor. Start the replicator with event listener
    repl_change_listener = replicator.addReplicatorEventChangeListener(repl)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl, max_times=500)

    # 4. Getting changes from the replication event listener
    doc_repl_event_changes = replicator.getReplicatorEventChanges(repl_change_listener)
    replicator.removeReplicatorEventListener(repl, repl_change_listener)

    # 5. Verify error Events
    replicated_event_changes = get_event_changes(doc_repl_event_changes)
    for doc in replicated_event_changes:
        assert replicated_event_changes[doc]["error_code"] == "22", "Incorrect encryption error code. {}".format(
            replicated_event_changes[doc]["error_code"])
        assert replicated_event_changes[doc]["error_domain"] == "CouchbaseLite", \
            "Incorrect encryption error domain. {}".format(replicated_event_changes[doc]["error_domain"])
    replicator.removeReplicatorEventListener(repl, repl_change_listener)
    replicator.stop(repl)

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True)
    sg_docs = sg_docs["rows"]
    # Verify database doc counts in CBL
    assert len(sg_docs) == 0, "Expected number of docs does not exist in sync-gateway after replication"


@pytest.mark.listener
@pytest.mark.callback
@pytest.mark.parametrize("num_of_non_encryptable_docs, num_of_encryptable_docs, replication_type", [
    (2, 3, "pull"),
    (2, 3, "push")
])
def test_delta_sync_with_encryption(params_from_base_test_setup, num_of_non_encryptable_docs, num_of_encryptable_docs, replication_type):

    """
    @summary:
    Verify Delta sync do not work when encryption callback hook is present
    Verify Doc is not editable in the SG
    test #11
    @Steps
    1. Have delta sync enabled
    2. Create docs with encrypted field in CBL
    3. Do push/pull replication to SGW
    4. update docs in CBL & SG
    5. replicate docs using pull replication
    6. Verify Bandwidth is saved for other documents
    """

    liteserv_platform = params_from_base_test_setup["liteserv_platform"]
    if "c-" not in liteserv_platform.lower():
        pytest.skip('This test cannot run other than C')
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    if sync_gateway_version < "2.5.0":
        pytest.skip('This test cannnot run with sg version below 2.5')
    sg_db = "db"
    sg_url = params_from_base_test_setup["sg_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    mode = params_from_base_test_setup["mode"]
    sg_config = params_from_base_test_setup["sg_config"]

    channels = ["ABC"]
    username = "autotest"
    password = "password"

    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)
    temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'delta_sync_enabled', True)
    status = c.sync_gateways[0].restart(config=sg_config, cluster_config=temp_cluster_config)
    assert status == 0, "Sync_gateway did not start"
    time.sleep(10)

    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, sg_db, username, password=password, channels=channels)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, username)
    session = cookie, session_id

    expvars = sg_client.get_expvars(url=sg_admin_url)
    delta_push_doc_count = expvars['syncgateway']['per_db']['db']['delta_sync']['delta_push_doc_count']

    # 2. Create docs in CBL
    # 2.1 - create num_of_non_encryptable_docs regular docs without encryptable property
    db.create_bulk_docs(num_of_non_encryptable_docs, "doc_no_encrypt", db=cbl_db, channels=channels)

    # 2.2 - create additional 3 docs with encryptable property
    encryptable = ReplicatorCallback(base_url)
    documentObj = Document(base_url)
    dictionary = Dictionary(base_url)
    for i in range(num_of_encryptable_docs):
        doc_id = "doc_encrypt_{}".format(i)
        init_doc_body = document.create_doc(doc_id=doc_id, content="doc {} with encryptable property".format(i), channels=channels, cbl=True)
        mutable_dict = dictionary.toMutableDictionary(init_doc_body)
        encrypted_value = encryptable.create("UInt", 4294967295 + i)
        dictionary.setEncryptable(mutable_dict, "encrypted_field_UInt", encrypted_value)
        doc_body_new = dictionary.toMap(mutable_dict)
        doc_body = doc_body_new["dictionary"]
        doc_body['encrypted_field_UInt'] = doc_body_new['encrypted_field_UInt']
        doc_to_save = documentObj.create(doc_id, doc_body)
        db.saveDocument(cbl_db, doc_to_save)
    encryptor = encryptable.createEncryptor("xor", "testkit")

    # 3. Do push replication to SGW
    replicator = Replication(base_url)
    session2, replicator_authenticator, repl = replicator.create_session_configure_replicate(base_url, sg_admin_url,
                                                                                             sg_db, username, password,
                                                                                             channels,
                                                                                             sg_client, cbl_db,
                                                                                             sg_blip_url,
                                                                                             continuous=True,
                                                                                             encryptor=encryptor)

    # 4. update docs in SGW/CBL
    if replication_type == "push":
        doc_ids = db.getDocIds(cbl_db)
        cbl_db_docs = db.getDocuments(cbl_db, doc_ids)
        for doc_id, doc_body in list(cbl_db_docs.items()):
            doc_body["new-1"] = random_string(length=70)
            doc_body["new-2"] = random_string(length=30)
            db.updateDocument(database=cbl_db, data=doc_body, doc_id=doc_id)
    else:
        def property_updater(doc_body):
            doc_body["sg_new_update"] = random_string(length=70)
            return doc_body

        for i in range(num_of_encryptable_docs):
            doc_id = "doc_encrypt_{}".format(i)
            sg_client.update_doc(url=sg_url, db=sg_db, doc_id=doc_id, number_updates=1, auth=session, channels=channels,
                                 property_updater=property_updater)

    repl = replicator.configure_and_replicate(source_db=cbl_db,
                                              target_url=sg_blip_url,
                                              continuous=True,
                                              replicator_authenticator=replicator_authenticator,
                                              replication_type=replication_type, encryptor=encryptor)
    replicator.stop(repl)
    expvars = sg_client.get_expvars(url=sg_admin_url)
    if replication_type == "pull":
        delta_pull_replication_count = expvars['syncgateway']['per_db']['db']['delta_sync']['delta_pull_replication_count']

        assert delta_pull_replication_count == num_of_non_encryptable_docs, "only non-encryptable docs should enable delta replication"
    else:
        delta_push_doc_count = expvars['syncgateway']['per_db']['db']['delta_sync']['delta_push_doc_count']
        assert delta_push_doc_count == num_of_non_encryptable_docs, "only non-encryptable docs should enable delta replication"


@pytest.mark.listener
@pytest.mark.callback
def test_encryption_with_two_dbs(params_from_base_test_setup):
    """
    @summary:
    Verify encrypted docs are replicated to another DB
    test 3

    1. Have SG and CBL up and running
    2. Create a simple document with encryption property
    3. Start the replicator and make sure documents are
    replicated on SG.
    4. Create another CBL DB then create 2 documents
    5. Verify both DBs docs are replicated to SG
    6. Verify Both BDs got all documents, verify Decrypter works fine as expected
    7. Verify the Encypted value in DB2
    """

    liteserv_platform = params_from_base_test_setup["liteserv_platform"]
    if "c-" not in liteserv_platform.lower():
        pytest.skip('This test cannot run other than C.')

    sg_db = "db"
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    sg_client = MobileRestClient()

    db2 = Database(base_url)

    channels_sg = ["ABCD"]
    username = "autotest"
    password = "password"

    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create docs in CBL
    doc_id = "doc_3"
    documentObj = Document(base_url)
    doc_body = document.create_doc(doc_id=doc_id, content="doc3", channels=channels_sg, non_sgw=True)
    dictionary = Dictionary(base_url)
    mutable = dictionary.toMutableDictionary(doc_body)
    encryptable = ReplicatorCallback(base_url)

    # 2. Create a simple document with encryption property
    dict = {"balance": "$2,393.65", "picture": "http://placehold.it/32x32", "email": "ofeliasears@imageflow.com",
            "phone": "+1 (939) 542-2185"}
    dict2 = dictionary.toMutableDictionary(dict)
    encrypted_value = encryptable.create("Dict", dict2)
    dictionary.setEncryptable(mutable, "encrypted_field_dict", encrypted_value)
    dictionary.setEncryptable(mutable, "encrypted_field_dict", encrypted_value)
    # # Add the encrypted key value in the document dictionary
    doc_body_new = dictionary.toMap(mutable)
    doc_body2 = doc_body_new["dictionary"]
    doc_body2['encrypted_field_dict'] = doc_body_new['encrypted_field_dict']
    doc1 = documentObj.create(doc_id, doc_body2)
    db.saveDocument(cbl_db, doc1)

    # Create an encryptor for replicator
    encryptor = encryptable.createEncryptor("xor", "testkit")

    # Configure replication with push/pull
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels_sg)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, username)
    cookie, session_id
    authenticator = Authenticator(base_url)
    replicator = Replication(base_url)
    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")

    repl = replicator.configure_and_replicate(source_db=cbl_db,
                                              target_url=sg_blip_url,
                                              continuous=True,
                                              replicator_authenticator=replicator_authenticator,
                                              encryptor=encryptor)
    replicator.wait_until_replicator_idle(repl)

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True)
    sg_docs = sg_docs["rows"]

    # 3. Start the replicator and make sure documents are replicated on SG.
    cbl_doc_count = db.getCount(cbl_db)
    assert len(sg_docs) == cbl_doc_count, "Expected number of docs does not exist in sync-gateway after replication"

    #  4. Create another CBL DB then create 2 documents
    cbl_db_name2 = "cbl_db_name2" + str(time.time())
    db_config = db2.configure(password="password")
    cbl_db2 = db2.create(cbl_db_name2, db_config)

    db2.create_bulk_docs(2, "cbl_sync2", db=cbl_db2, channels=channels_sg)

    replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
    repl2 = replicator.configure_and_replicate(source_db=cbl_db2, target_url=sg_blip_url, continuous=True,
                                               replicator_authenticator=replicator_authenticator, encryptor=encryptor)
    replicator.wait_until_replicator_idle(repl2)
    replicator.wait_until_replicator_idle(repl)
    cbl_doc_ids2 = db2.getDocIds(cbl_db2)
    cbl_doc_ids = db.getDocIds(cbl_db)

    assert len(cbl_doc_ids2) == len(cbl_doc_ids)

    # 5 Verify the encrypted doc content that got replicated from DB1
    cbl_doc_ids = db.getDocIds(cbl_db)
    cbl_db_docs = db.getDocuments(cbl_db, cbl_doc_ids)

    encrypted_doc = cbl_db_docs["doc_3"]
    assert deep_dict_compare(encrypted_doc['encrypted_field_dict']['value']['dictionary'],
                             dict), "Decryption is not working "


@pytest.mark.listener
@pytest.mark.callback
@pytest.mark.sanity
def test_replication_complex_doc_encryption(params_from_base_test_setup):
    """
    @summary:
    Testing  dict and array encrypted values are present in 10-15th level of complex doc and replicated should detected
    values without any errors .
    test 13-16

    1. Have SG and CBL up and running
    2. Create a complex document with encryption property (Array, and Dict)
    3. Start the replicator and make sure documents are
    replicated on SG. Verify encrypted fields and Verify data is encrypted.
    4. Verify encrypted values at 15th level of array and dic are detected by replicator and shown correctly on sg
    """

    liteserv_platform = params_from_base_test_setup["liteserv_platform"]
    if "c-" not in liteserv_platform.lower():
        pytest.skip('This test cannot run other than C.')

    sg_db = "db"
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    sg_client = MobileRestClient()

    if sync_gateway_version < "2.0.0":
        pytest.skip('This test cannot run with sg version below 2.0')
    channels_sg = ["ABCD"]
    username = "autotest"
    password = "password"

    # 1.Have SG and CBL up and running
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Create docs in CBL
    encryptable = ReplicatorCallback(base_url)
    documentObj = Document(base_url)
    dictionary = Dictionary(base_url)

    # 2. Create a complex document with encryption property
    doc_body = doc_generators.complex_doc()
    mutable = dictionary.toMutableDictionary(doc_body)
    encrypted_value = encryptable.create("UInt", 4294967295)
    dictionary.setEncryptable(mutable, "encrypted_field_Uint", encrypted_value)

    doc_body_new = dictionary.toMap(mutable)
    doc = doc_body_new["dictionary"]

    doc['purchasedetails'][0]['item']['barcodes'][0]['test'] = [
        {'test1': [{'test2': [{'test3': [{'encrypted_field_Uint': doc_body_new['encrypted_field_Uint']}]}]}]}]

    doc1 = documentObj.create("cbl_sync2_0", doc)
    db.saveDocument(cbl_db, doc1)

    # Create an encryptor for replicator
    encryptor = encryptable.createEncryptor("xor", "testkit")

    # 3. Start the replicator and make sure documents are
    #     replicated on SG. Verify encrypted fields and Verify data is encrypted.
    replicator = Replication(base_url)
    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels_sg)
    session, replicator_authenticator, repl = replicator.create_session_configure_replicate(base_url, sg_admin_url,
                                                                                            sg_db, username, password,
                                                                                            channels_sg,
                                                                                            sg_client, cbl_db,
                                                                                            sg_blip_url,
                                                                                            continuous=True,
                                                                                            encryptor=encryptor)

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, include_docs=True)
    sg_docs = sg_docs["rows"]

    # 4. Verify encrypted values at 15th level of array and dic are detected by replicator and shown correctly on sg
    assert 'alg' and 'ciphertext' and 'kid' in \
           sg_docs[0]["doc"]['purchasedetails'][0]['item']['barcodes'][0]['test'][0]['test1'][0]['test2'][0]['test3'][
               0]['encrypted$encrypted_field_Uint'], \
        "All required fields are not present in the encrypted data"
    assert "4294967295" not in \
           sg_docs[0]["doc"]['purchasedetails'][0]['item']['barcodes'][0]['test'][0]['test1'][0]['test2'][0]['test3'][
               0]['encrypted$encrypted_field_Uint']["ciphertext"], \
        "Data is not encrypted in the SG"

    # Verify database doc counts in CBL
    cbl_doc_count = db.getCount(cbl_db)
    assert len(sg_docs) == cbl_doc_count, "Expected number of docs does not exist in sync-gateway after replication"
