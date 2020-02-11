import pytest
import time

from CBLClient.Database import Database
from CBLClient.DatabaseConfiguration import DatabaseConfiguration


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
    print "cbl doc ids are {}", cbl_doc_ids
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
    else:
        with pytest.raises(Exception) as he:
            db.create(cbl_db_name, db_config)
        assert he.value.args[0].startswith('400 Client Error: Bad Request for url:')

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
    else:
        with pytest.raises(Exception) as he:
            db.create(cbl_db_name, db_config_without_password)
        assert he.value.args[0].startswith('400 Client Error: Bad Request for url:')

    # 4. access database with invalid password
    # 5. Verify database cannot be accessed
    if liteserv_platform.lower() == "ios":
        invalid_key_db_config = db_configure.setEncryptionKey(db_config, password=password)
        cbl_db2 = db.create(cbl_db_name, invalid_key_db_config)
        assert "file is not a database" in cbl_db2
    else:
        with pytest.raises(Exception) as he:
            invalid_key_db_config = db_configure.setEncryptionKey(db_config, password=password)
            db.create(cbl_db_name, invalid_key_db_config)
        assert he.value.args[0].startswith('400 Client Error: Bad Request for url:')


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
    else:
        with pytest.raises(Exception) as he:
            db.create(cbl_db_name, db_config)
        assert he.value.args[0].startswith('400 Client Error: Bad Request for url:')


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
    else:
        with pytest.raises(Exception) as he:
            db.create(cbl_db_name, db_config)
        assert he.value.args[0].startswith('400 Client Error: Bad Request for url:')

    # 5. Verify database can be accessed without password.
    print "starting the database access without password"
    db_config1 = db.configure()
    cbl_db4 = db.create(cbl_db_name, db_config1)
    print "Trying to get doc ids"
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
    if liteserv_platform == "android":
        prebuilt_db_path = "/assets/{}.cblite2.zip".format(db_prefix)
    elif liteserv_platform in ["xamarin-android", "java-macosx", "java-msft", "java-ubuntu", "java-centos",
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
