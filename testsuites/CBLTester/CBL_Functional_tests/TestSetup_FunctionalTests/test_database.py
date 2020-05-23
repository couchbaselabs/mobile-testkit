import pytest
import time

from CBLClient.Database import Database
from CBLClient.DatabaseConfiguration import DatabaseConfiguration
from libraries.testkit import cluster
from CBLClient.Replication import Replication
from keywords.MobileRestClient import MobileRestClient
from CBLClient.Authenticator import Authenticator
from keywords.utils import log_info
from CBLClient.Query import Query


@pytest.mark.listener
@pytest.mark.database
@pytest.mark.parametrize(
    'password',
    [
        pytest.param('encrypting-password', marks=pytest.mark.sanity),
        ('123'),
        ('****&&&'),
        ('1*rt')
    ]
)
def test_databaseEncryption(params_from_base_test_setup, password):
    '''
        @summary:
        1. Create database without password
        2. access database withtout password
        3. Verify database can be accessed successfully
        4. Now add the encryption using the password
        5. Verify that database cannot be accessed without password.
        6. Verify that database can be accessed with password
    '''

    base_url = params_from_base_test_setup["base_url"]
    liteserv_platform = params_from_base_test_setup["liteserv_platform"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    if liteserv_version < "2.1":
        pytest.skip('database encryption feature not available with version < 2.1')
    db = Database(base_url)
    cbl_db_name = "cbl_db_name" + str(time.time())
    db_config = db.configure()
    cbl_db = db.create(cbl_db_name, db_config)
    db.create_bulk_docs(2, "db-encryption", db=cbl_db)
    cbl_doc_ids = db.getDocIds(cbl_db)
    print("cbl doc ids are {}", cbl_doc_ids)
    db.close(cbl_db)

    # 2. Access database withtout password
    # 3. Verify database can be accessed successfully
    cbl_db1 = db.create(cbl_db_name, db_config)
    cbl_doc_ids1 = db.getDocIds(cbl_db1)
    assert len(cbl_doc_ids) == len(cbl_doc_ids1), "docs ids did not match"
    for doc_id in cbl_doc_ids:
        assert doc_id in cbl_doc_ids1, "cbl doc is in first list does not exist in second list"

    # 4. Now add the encryption using the password
    db.changeEncryptionKey(cbl_db1, password)
    db.close(cbl_db1)

    # 5. Verify that database cannot be accessed without password.
    if liteserv_platform == "ios":
        cbl_db2 = db.create(cbl_db_name, db_config)
        assert "file is not a database" in cbl_db2
    elif liteserv_platform in ["javaws-macosx", "javaws-msft", "javaws-ubuntu", "javaws-centos"]:
        with pytest.raises(Exception) as he:
            db.create(cbl_db_name, db_config)
        assert str(he.value).startswith('400 Client Error:')
    else:
        with pytest.raises(Exception) as he:
            db.create(cbl_db_name, db_config)

        assert str(he.value).startswith('400 Client Error: Bad Request for url:')

    # 6. Verify that database can be accessed with password
    db_config1 = db.configure(password=password)
    cbl_db3 = db.create(cbl_db_name, db_config1)
    cbl_doc_ids3 = db.getDocIds(cbl_db3)
    assert len(cbl_doc_ids) == len(cbl_doc_ids3), "docs ids did not match"
    for doc_id in cbl_doc_ids:
        assert doc_id in cbl_doc_ids3, "cbl doc is in first list does not exist in second list"
    db.deleteDB(cbl_db3)


@pytest.mark.listener
@pytest.mark.database
@pytest.mark.parametrize(
    'password',
    [
        ('wrong_password'),
        (None)
    ]
)
def test_invalidEncryption(params_from_base_test_setup, password):
    '''
        @summary:
        1. Create database with password
        2. access database withtout password
        3. Verify database cannot be accessed
        4. access database with invalid password
        5. Verify database cannot be accessed
    '''

    base_url = params_from_base_test_setup["base_url"]
    liteserv_platform = params_from_base_test_setup["liteserv_platform"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    if liteserv_version < "2.1":
        pytest.skip('database encryption feature not available with version < 2.1')
    db = Database(base_url)
    db_configure = DatabaseConfiguration(base_url)

    # 1. Create database with password
    cbl_db_name = "cbl_db_name" + str(time.time())
    db_config = db.configure(password="database-password")
    cbl_db = db.create(cbl_db_name, db_config)
    db.create_bulk_docs(2, "db-encryption", db=cbl_db)
    db.close(cbl_db)

    # 2. Access database withtout password
    # 3. Verify database cannot be accessed
    db_config_without_password = db.configure()
    if liteserv_platform == "ios":
        cbl_db1 = db.create(cbl_db_name, db_config_without_password)
        assert "file is not a database" in cbl_db1
    elif liteserv_platform in ["javaws-macosx", "javaws-msft", "javaws-ubuntu", "javaws-centos"]:
        with pytest.raises(Exception) as he:
            db.create(cbl_db_name, db_config_without_password)
        assert str(he.value).startswith('400 Client Error:  for url:')
    else:
        with pytest.raises(Exception) as he:
            db.create(cbl_db_name, db_config_without_password)
        assert str(he.value).startswith('400 Client Error: Bad Request for url:')

    # 4. access database with invalid password
    # 5. Verify database cannot be accessed
    if liteserv_platform.lower() == "ios":
        invalid_key_db_config = db_configure.setEncryptionKey(db_config, password=password)
        cbl_db2 = db.create(cbl_db_name, invalid_key_db_config)
        assert "file is not a database" in cbl_db2
    elif liteserv_platform in ["javaws-macosx", "javaws-msft", "javaws-ubuntu", "javaws-centos"]:
        with pytest.raises(Exception) as he:
            invalid_key_db_config = db_configure.setEncryptionKey(db_config, password=password)
            db.create(cbl_db_name, invalid_key_db_config)
        assert str(he.value).startswith('400 Client Error:  for url:')
    else:
        with pytest.raises(Exception) as he:
            invalid_key_db_config = db_configure.setEncryptionKey(db_config, password=password)
            db.create(cbl_db_name, invalid_key_db_config)
        assert str(he.value).startswith('400 Client Error: Bad Request for url:')


@pytest.mark.listener
@pytest.mark.database
def test_updateDBEncryptionKey(params_from_base_test_setup):
    '''
        @summary:
        1. Create database with password
        2. Update password with new password
        3. Verify database can be accessed with new password
        4. Verify database cannot be accessed with old password
    '''

    base_url = params_from_base_test_setup["base_url"]
    liteserv_platform = params_from_base_test_setup["liteserv_platform"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    if liteserv_version < "2.1":
        pytest.skip('database encryption feature not available with version < 2.1')
    db = Database(base_url)

    # 1. Create database with password
    cbl_db_name = "cbl_db_name" + str(time.time())
    db_config = db.configure(password="database-password")
    cbl_db = db.create(cbl_db_name, db_config)
    db.create_bulk_docs(2, "db-encryption", db=cbl_db)
    cbl_doc_ids = db.getDocIds(cbl_db)

    # 2.Update password with new password
    db.changeEncryptionKey(cbl_db, password="database-new-password")
    # db.close(cbl_db)

    # 3.Verify database can be accessed with new password
    db_config_withNewKey = db.configure(password="database-new-password")
    cbl_db_withNewKey = db.create(cbl_db_name, db_config_withNewKey)
    cbl_doc_ids_with_newKey = db.getDocIds(cbl_db_withNewKey)
    assert len(cbl_doc_ids) == len(cbl_doc_ids_with_newKey), "docs ids did not match"
    for doc_id in cbl_doc_ids:
        assert doc_id in cbl_doc_ids_with_newKey, "cbl doc is in first list does not exist in second list"

    # 4. Verify database cannot be accessed with old password
    if liteserv_platform == "ios":
        cbl_db1 = db.create(cbl_db_name, db_config)
        assert "file is not a database" in cbl_db1
    elif liteserv_platform in ["javaws-macosx", "javaws-msft", "javaws-ubuntu", "javaws-centos"]:
        with pytest.raises(Exception) as he:
            db.create(cbl_db_name, db_config)

        assert str(he.value).startswith('400 Client Error:  for url:')
    else:
        with pytest.raises(Exception) as he:
            db.create(cbl_db_name, db_config)

        assert str(he.value).startswith('400 Client Error: Bad Request for url:')


@pytest.mark.listener
@pytest.mark.database
def test_DBEncryptionKey_withCompact(params_from_base_test_setup):
    '''
        @summary:
        1. Create database with password
        2. Create documents to the database
        3. Update documents
        4. Compact database
        5. update the document again
        6. Verify database is accessible
    '''

    base_url = params_from_base_test_setup["base_url"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    if liteserv_version < "2.1":
        pytest.skip('database encryption feature not available with version < 2.1')
    db = Database(base_url)

    # 1. Create database with password
    cbl_db_name = "cbl_db_name" + str(time.time())
    db_config = db.configure(password="database-password")
    cbl_db = db.create(cbl_db_name, db_config)

    # 2. Create documents to the database
    db.create_bulk_docs(2, "db-encryption", db=cbl_db)
    cbl_doc_ids = db.getDocIds(cbl_db)
    # db.close(cbl_db)

    # 3. Update documents
    db.update_bulk_docs(database=cbl_db, number_of_updates=1)

    # 4. Compact database
    db.compact(cbl_db)

    # 5. update the document again
    db.update_bulk_docs(database=cbl_db, number_of_updates=1)
    db.close(cbl_db)

    # 6. Verify database is accessible
    cbl_db1 = db.create(cbl_db_name, db_config)
    cbl_doc_ids1 = db.getDocIds(cbl_db1)
    assert len(cbl_doc_ids) == len(cbl_doc_ids1), "docs ids did not match"
    for doc_id in cbl_doc_ids:
        assert doc_id in cbl_doc_ids1, "cbl doc is in first list does not exist in second list"


@pytest.mark.listener
@pytest.mark.database
def test_removeDBEncryptionKey(params_from_base_test_setup):
    '''
        @summary:
        1. Create database with password
        2. Verify database can be access with password.
        3. remove password.
        4. Verify database cannot be accessed with password.
        5. Verify database can be accessed without password.
    '''

    base_url = params_from_base_test_setup["base_url"]
    liteserv_platform = params_from_base_test_setup["liteserv_platform"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    if liteserv_version < "2.1":
        pytest.skip('database encryption feature not available with version < 2.1')
    password = "encryption"
    db = Database(base_url)
    dbConfiguration = DatabaseConfiguration(base_url)

    # 1. Create database with password
    cbl_db_name = "cbl_db_name" + str(time.time())
    db_config = db.configure(password=password)
    cbl_db = db.create(cbl_db_name, db_config)
    db.create_bulk_docs(2, "db-encryption", db=cbl_db)
    cbl_doc_ids = db.getDocIds(cbl_db)
    db.close(cbl_db)

    # 2. Verify database can be accessed with password.
    db_config = dbConfiguration.setEncryptionKey(db_config, password)
    # db_config1 = db.configure(password=password)
    cbl_db3 = db.create(cbl_db_name, db_config)
    cbl_doc_ids3 = db.getDocIds(cbl_db3)
    assert cbl_doc_ids == cbl_doc_ids3, "docs ids did not match when compared with and without password"

    # 3. remove password.
    db.changeEncryptionKey(cbl_db3, "nil")
    db.close(cbl_db3)

    # 4. Verify that database cannot be accessed with password.
    if liteserv_platform == "ios":
        cbl_db2 = db.create(cbl_db_name, db_config)
        assert "file is not a database" in cbl_db2
    elif liteserv_platform in ["javaws-macosx", "javaws-msft", "javaws-ubuntu", "javaws-centos"]:
        with pytest.raises(Exception) as he:
            db.create(cbl_db_name, db_config)
        assert str(he.value).startswith('400 Client Error:  for url:')
    else:
        with pytest.raises(Exception) as he:
            db.create(cbl_db_name, db_config)
        assert str(he.value).startswith('400 Client Error: Bad Request for url:')

    # 5. Verify database can be accessed without password.
    print("starting the database access without password")
    db_config1 = db.configure()
    cbl_db4 = db.create(cbl_db_name, db_config1)
    print("Trying to get doc ids")
    cbl_doc_ids4 = db.getDocIds(cbl_db4)
    assert cbl_doc_ids == cbl_doc_ids4, "docs ids did not match when compared with and without password"
    db.close(cbl_db4)


@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("encrypted", [
    False,
    True
])
def test_copy_prebuilt_database(params_from_base_test_setup, encrypted):
    """
        @summary:
        1. Clean up the database/ Remove any existing database.
        2. Copy the prebuilt database
        3. Verify database is created successfully
        4. Verify docs in prebuilt database are copied over and exits in current app

    """

    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    liteserv_platform = params_from_base_test_setup["liteserv_platform"]

    prebuilt_doc_ids = ['cbl_2', 'cbl_1', 'cbl_3', 'cbl_4', 'cbl_0', 'cbl2_3', 'cbl2_0', 'cbl2_2', 'cbl2_4', 'cbl2_1']

    if sync_gateway_version < "2.0.0":
        pytest.skip('This test cannnot run with sg version below 2.0')

    db_name = db.getName(cbl_db)
    db_path = db.getPath(cbl_db).rstrip("\\")
    db.deleteDB(cbl_db, db_name)
    cbl_db_name = "copiedDB" + str(time.time())
    if encrypted:
        db_config = db.configure(password="password")
        db_prefix = "PrebuiltDB-encrypted"
    else:
        db_config = db.configure()
        db_prefix = "PrebuiltDB"
    if liteserv_platform in ["android", "xamarin-android", "java-macosx", "java-msft", "java-ubuntu", "java-centos",
                             "javaws-macosx", "javaws-msft", "javaws-ubuntu", "javaws-centos"]:
        prebuilt_db_path = "{}.cblite2.zip".format(db_prefix)
    elif liteserv_platform == "net-msft":
        app_dir = "\\".join(db_path.split("\\")[:-2])
        prebuilt_db_path = "{}\\Databases\\{}.cblite2".format(app_dir, db_prefix)
    else:
        prebuilt_db_path = "Databases/{}.cblite2".format(db_prefix)

    old_db_path = db.get_pre_built_db(prebuilt_db_path)
    db.copyDatabase(old_db_path, cbl_db_name, db_config)
    cbl_db1 = db.create(cbl_db_name, db_config)
    cbl_doc_ids = db.getDocIds(cbl_db1)
    assert len(cbl_doc_ids) == 10
    for doc_id in prebuilt_doc_ids:
        assert doc_id in cbl_doc_ids

    # Cleaning the database , tearing down
    db.deleteDB(cbl_db1)


@pytest.mark.listener
@pytest.mark.hydrogen
def test_db_close_on_active_replicators(params_from_base_test_setup):
    """
        @summary:
        1. create a db on cbl, have a sgw available
        2. start 3 replicators with the sgw, ensure one of 
           the replicator is push_pull replicator with continues=true
        3. close the cbl db
        4. verify cbl db is closed closed successfully
    """
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    base_url = params_from_base_test_setup["base_url"]
    sg_db = "db"
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_blip_url = params_from_base_test_setup["target_url"]

    if liteserv_version < "2.8.0":
        pytest.skip('This test supports for a feature from hydrogen(2.8.0)')

    # reset SGW configuration
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 1a. create a db, and add document to the cbl db
    db = Database(base_url)
    db_name = "test_close_db_" + str(time.time())
    log_info("Creating a Database {} at test setup".format(db_name))
    db_config = db.configure()
    cbl_db = db.create(db_name, db_config)

    num_of_docs = 100
    channel1 = ["Replication-1"]
    channel2 = ["Replication-2"]
    channel3 = ["Replication-3"]

    db.create_bulk_docs(num_of_docs, "ch1", db=cbl_db, channels=channel1)
    db.create_bulk_docs(num_of_docs, "ch2", db=cbl_db, channels=channel2)
    db.create_bulk_docs(num_of_docs, "ch3", db=cbl_db, channels=channel3)

    # 1b. prepare SGW, create 3 users on 3 different channels and set up connections
    username1 = "autotest"
    username2 = "autotest2"
    username3 = "autotest3"
    password = "password"

    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, sg_db, username1, password=password, channels=channel1)
    cookie1, session_id1 = sg_client.create_session(sg_admin_url, sg_db, username1)

    sg_client.create_user(sg_admin_url, sg_db, username2, password=password, channels=channel2)
    cookie2, session_id2 = sg_client.create_session(sg_admin_url, sg_db, username2)

    sg_client.create_user(sg_admin_url, sg_db, username3, password=password, channels=channel3)
    cookie3, session_id3 = sg_client.create_session(sg_admin_url, sg_db, username3)

    # 2. start 3 replicators on 3 different channels, set all continous to True
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)

    replicator_authenticator1 = authenticator.authentication(session_id1, cookie1, authentication_type="session")
    repl_config1 = replicator.configure(source_db=cbl_db, replicator_authenticator=replicator_authenticator1, target_url=sg_blip_url,
                                        replication_type="push_pull", continuous=True, channels=channel1)
 
    replicator_authenticator2 = authenticator.authentication(session_id2, cookie2, authentication_type="session")
    repl_config2 = replicator.configure(source_db=cbl_db, replicator_authenticator=replicator_authenticator2, target_url=sg_blip_url,
                                        replication_type="push", continuous=True, channels=channel2)
    replicator_authenticator3 = authenticator.authentication(session_id3, cookie3, authentication_type="session")
    repl_config3 = replicator.configure(source_db=cbl_db, replicator_authenticator=replicator_authenticator3, target_url=sg_blip_url,
                                        replication_type="pull", continuous=True, channels=channel3)

    # start all replicators
    repl1 = replicator.create(repl_config1)
    replicator.start(repl1)
    repl2 = replicator.create(repl_config2)
    replicator.start(repl2)
    repl3 = replicator.create(repl_config3)
    replicator.start(repl3)

    log_info(replicator.getActivitylevel(repl1))
    log_info(replicator.getActivitylevel(repl2))
    log_info(replicator.getActivitylevel(repl3))

    # TODO: need to clarify with dev about close db on replicator state
    # after clarification, this code suppose to be removed
    replicator.wait_until_replicator_idle(repl1)
    replicator.wait_until_replicator_idle(repl2)
    replicator.wait_until_replicator_idle(repl3)

    log_info(replicator.getActivitylevel(repl1))
    log_info(replicator.getActivitylevel(repl2))
    log_info(replicator.getActivitylevel(repl3))

    try:
        log_info("closing database")
        db.close(cbl_db)
        log_info("database closed successfully")
        assert True
    except KeyError:
        assert False, "closing database with active replicators are failed"


@pytest.mark.listener
@pytest.mark.hydrogen
def test_db_close_on_active_replicator_and_live_query(params_from_base_test_setup):
    """
        @summary:
        1. create a db on cbl, have a sgw available
        2. start 2 replicators, ensure one of the replicator is push_pull replicator with continues=true
        3. if live_query_enabled, register a live query to the cbl db, otherwise, skip this step
        4. close the cbl db
        5. verify cbl db is closed closed successfully
    """
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    base_url = params_from_base_test_setup["base_url"]
    sg_db = "db"
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_blip_url = params_from_base_test_setup["target_url"]

    if liteserv_version < "2.8.0":
        pytest.skip('This test supports for a feature from hydrogen(2.8.0)')

    # reset SGW configuration
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 1a. create a db, and add document to the cbl db
    db = Database(base_url)
    db_name = "test_close_db_" + str(time.time())
    log_info("Creating a Database {} at test setup".format(db_name))
    db_config = db.configure()
    cbl_db = db.create(db_name, db_config)

    num_of_docs = 100
    channel1 = ["Replication-1"]
    channel2 = ["Replication-2"]

    db.create_bulk_docs(num_of_docs, "ch1", db=cbl_db, channels=channel1)
    db.create_bulk_docs(num_of_docs, "ch2", db=cbl_db, channels=channel2)

    # 1b. prepare SGW, create 2 users on 2 different channels and set up connections
    username1 = "autotest"
    username2 = "autotest2"
    password = "password"

    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, sg_db, username1, password=password, channels=channel1)
    cookie1, session_id1 = sg_client.create_session(sg_admin_url, sg_db, username1)

    sg_client.create_user(sg_admin_url, sg_db, username2, password=password, channels=channel2)
    cookie2, session_id2 = sg_client.create_session(sg_admin_url, sg_db, username2)

    # 2. start 2 replicators on 2 different channels, set all continous to True
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)

    replicator_authenticator1 = authenticator.authentication(session_id1, cookie1, authentication_type="session")
    repl_config1 = replicator.configure(source_db=cbl_db, replicator_authenticator=replicator_authenticator1, target_url=sg_blip_url,
                                        replication_type="push_pull", continuous=True, channels=channel1)
    replicator_authenticator2 = authenticator.authentication(session_id2, cookie2, authentication_type="session")
    repl_config2 = replicator.configure(source_db=cbl_db, replicator_authenticator=replicator_authenticator2, target_url=sg_blip_url,
                                        replication_type="push_pull", continuous=True, channels=channel2)

    # start all replicators
    repl1 = replicator.create(repl_config1)
    replicator.start(repl1)

    repl2 = replicator.create(repl_config2)
    replicator.start(repl2)

    # 3. register a live query to the cbl db
    qy = Query(base_url)
    query = qy.query_select_all(cbl_db)
    query_listener = qy.addChangeListener(query)

    log_info(replicator.getActivitylevel(repl1))
    log_info(replicator.getActivitylevel(repl2))

    # TODO: need to clarify with dev about close db on replicator state
    # after clarification, this code suppose to be removed
    replicator.wait_until_replicator_idle(repl1)
    replicator.wait_until_replicator_idle(repl2)

    log_info(replicator.getActivitylevel(repl1))
    log_info(replicator.getActivitylevel(repl2))

    # 4. close the database
    # 5. verify the database is closed successfully
    try:
        log_info("closing database")
        db.close(cbl_db)
        log_info("database is closed successfully")
        assert True
    except KeyError:
        qy.removeChangeListener(query_listener)
        assert False, "closing database with active replicators are failed"


@pytest.mark.listener
@pytest.mark.hydrogen
def test_db_delete_on_active_replicators(params_from_base_test_setup):
    """
        @summary:
        1. create a db on cbl, have a sgw available
        2. start 3 replicators with the sgw, ensure one of 
           the replicator is push_pull replicator with continues=true
        3. delete the cbl db
        4. verify cbl db is delete successfully
    """
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    base_url = params_from_base_test_setup["base_url"]
    sg_db = "db"
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_blip_url = params_from_base_test_setup["target_url"]

    if liteserv_version < "2.8.0":
        pytest.skip('This test supports for a feature from hydrogen(2.8.0)')

    # reset SGW configuration
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 1a. create a db, and add document to the cbl db
    db = Database(base_url)
    db_name = "test_delete_db_" + str(time.time())
    log_info("Creating a Database {} at test setup".format(db_name))
    db_config = db.configure()
    cbl_db = db.create(db_name, db_config)

    num_of_docs = 100
    channel1 = ["Replication-1"]
    channel2 = ["Replication-2"]
    channel3 = ["Replication-3"]

    db.create_bulk_docs(num_of_docs, "ch1", db=cbl_db, channels=channel1)
    db.create_bulk_docs(num_of_docs, "ch2", db=cbl_db, channels=channel2)
    db.create_bulk_docs(num_of_docs, "ch3", db=cbl_db, channels=channel3)

    # 1b. prepare SGW, create 3 users on 3 different channels and set up connections
    username1 = "autotest"
    username2 = "autotest2"
    username3 = "autotest3"
    password = "password"

    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, sg_db, username1, password=password, channels=channel1)
    cookie1, session_id1 = sg_client.create_session(sg_admin_url, sg_db, username1)

    sg_client.create_user(sg_admin_url, sg_db, username2, password=password, channels=channel2)
    cookie2, session_id2 = sg_client.create_session(sg_admin_url, sg_db, username2)

    sg_client.create_user(sg_admin_url, sg_db, username3, password=password, channels=channel3)
    cookie3, session_id3 = sg_client.create_session(sg_admin_url, sg_db, username3)

    # 2. start 3 replicators on 3 different channels, set all continous to True
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)

    replicator_authenticator1 = authenticator.authentication(session_id1, cookie1, authentication_type="session")
    repl_config1 = replicator.configure(source_db=cbl_db, replicator_authenticator=replicator_authenticator1, target_url=sg_blip_url,
                                        replication_type="push_pull", continuous=True, channels=channel1)
    replicator_authenticator2 = authenticator.authentication(session_id2, cookie2, authentication_type="session")
    repl_config2 = replicator.configure(source_db=cbl_db, replicator_authenticator=replicator_authenticator2, target_url=sg_blip_url,
                                        replication_type="push", continuous=True, channels=channel2)
    replicator_authenticator3 = authenticator.authentication(session_id3, cookie3, authentication_type="session")
    repl_config3 = replicator.configure(source_db=cbl_db, replicator_authenticator=replicator_authenticator3, target_url=sg_blip_url,
                                        replication_type="pull", continuous=True, channels=channel3)

    # start all replicators
    repl1 = replicator.create(repl_config1)
    replicator.start(repl1)
    repl2 = replicator.create(repl_config2)
    replicator.start(repl2)
    repl3 = replicator.create(repl_config3)
    replicator.start(repl3)

    log_info(replicator.getActivitylevel(repl1))
    log_info(replicator.getActivitylevel(repl2))
    log_info(replicator.getActivitylevel(repl3))

    # TODO: need to clarify with dev about close db on replicator state
    # after clarification, this code suppose to be removed
    replicator.wait_until_replicator_idle(repl1)
    replicator.wait_until_replicator_idle(repl2)
    replicator.wait_until_replicator_idle(repl3)

    log_info(replicator.getActivitylevel(repl1))
    log_info(replicator.getActivitylevel(repl2))
    log_info(replicator.getActivitylevel(repl3))

    try:
        log_info("deleting database")
        db.deleteDB(cbl_db)
        log_info("database deleted successfully")
        assert True
    except KeyError:
        assert False, "deleting database with active replicators are failed"


@pytest.mark.listener
@pytest.mark.hydrogen
def test_db_delete_on_active_replicator_and_live_query(params_from_base_test_setup):
    """
        @summary:
        1. create a db on cbl, have a sgw available
        2. start 2 replicators, ensure one of the replicator is push_pull replicator with continues=true
        3. if live_query_enabled, register a live query to the cbl db, otherwise, skip this step
        4. close the cbl db
        5. verify cbl db is closed closed successfully
    """
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    base_url = params_from_base_test_setup["base_url"]
    sg_db = "db"
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_blip_url = params_from_base_test_setup["target_url"]

    if liteserv_version < "2.8.0":
        pytest.skip('This test supports for a feature from hydrogen(2.8.0)')

    # reset SGW configuration
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # 1a. create a db, and add document to the cbl db
    db = Database(base_url)
    db_name = "test_delete_db_" + str(time.time())
    log_info("Creating a Database {} at test setup".format(db_name))
    db_config = db.configure()
    cbl_db = db.create(db_name, db_config)

    num_of_docs = 100
    channel1 = ["Replication-1"]
    channel2 = ["Replication-2"]

    db.create_bulk_docs(num_of_docs, "ch1", db=cbl_db, channels=channel1)
    db.create_bulk_docs(num_of_docs, "ch2", db=cbl_db, channels=channel2)

    # 1b. prepare SGW, create 2 users on 2 different channels and set up connections
    username1 = "autotest"
    username2 = "autotest2"
    password = "password"

    sg_client = MobileRestClient()
    sg_client.create_user(sg_admin_url, sg_db, username1, password=password, channels=channel1)
    cookie1, session_id1 = sg_client.create_session(sg_admin_url, sg_db, username1)

    sg_client.create_user(sg_admin_url, sg_db, username2, password=password, channels=channel2)
    cookie2, session_id2 = sg_client.create_session(sg_admin_url, sg_db, username2)

    # 2. start 2 replicators on 2 different channels, set all continous to True
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)

    replicator_authenticator1 = authenticator.authentication(session_id1, cookie1, authentication_type="session")
    repl_config1 = replicator.configure(source_db=cbl_db, replicator_authenticator=replicator_authenticator1, target_url=sg_blip_url,
                                        replication_type="push_pull", continuous=True, channels=channel1)
    replicator_authenticator2 = authenticator.authentication(session_id2, cookie2, authentication_type="session")
    repl_config2 = replicator.configure(source_db=cbl_db, replicator_authenticator=replicator_authenticator2, target_url=sg_blip_url,
                                        replication_type="push_pull", continuous=True, channels=channel2)

    # start all replicators
    repl1 = replicator.create(repl_config1)
    replicator.start(repl1)

    repl2 = replicator.create(repl_config2)
    replicator.start(repl2)

    # 3. register a live query to the cbl db
    qy = Query(base_url)
    query = qy.query_select_all(cbl_db)
    query_listener = qy.addChangeListener(query)

    log_info(replicator.getActivitylevel(repl1))
    log_info(replicator.getActivitylevel(repl2))

    # TODO: need to clarify with dev about close db on replicator state
    # after clarification, this code suppose to be removed
    replicator.wait_until_replicator_idle(repl1)
    replicator.wait_until_replicator_idle(repl2)

    log_info(replicator.getActivitylevel(repl1))
    log_info(replicator.getActivitylevel(repl2))

    try:
        log_info("deleting database")
        db.deleteDB(cbl_db)
        log_info("database is deleted successfully")
        assert True
    except KeyError:
        qy.removeChangeListener(query_listener)
        assert False, "deleting database with active replicators are failed"
