import os

import pytest
import pdb

from keywords.constants import TEST_DIR
from keywords.LiteServFactory import LiteServFactory
from keywords.MobileRestClient import MobileRestClient


@pytest.fixture(scope="function")
def setup_liteserv_macosx_sqlite():
    liteserv = LiteServFactory.create("macosx",
                                      version_build="1.3.1-6",
                                      host="localhost",
                                      port=59840,
                                      storage_engine="SQLite")

    logfile = open("{}/test.txt".format(TEST_DIR), "w")
    ls_url = liteserv.start(logfile)

    yield ls_url

    liteserv.stop(logfile)


@pytest.fixture(scope="function")
def setup_liteserv_macosx_sqlcipher():
    liteserv = LiteServFactory.create("macosx",
                                      version_build="1.3.1-6",
                                      host="localhost",
                                      port=59840,
                                      storage_engine="SQLCipher")

    logfile = open("{}/test.txt".format(TEST_DIR), "w")
    ls_url = liteserv.start(logfile)

    yield ls_url

    liteserv.stop(logfile)


@pytest.fixture(scope="function")
def setup_liteserv_macosx_forestdb():
    liteserv = LiteServFactory.create("macosx",
                                      version_build="1.3.1-6",
                                      host="localhost",
                                      port=59840,
                                      storage_engine="ForestDB")

    logfile = open("{}/test.txt".format(TEST_DIR), "w")
    ls_url = liteserv.start(logfile)

    yield ls_url

    liteserv.stop(logfile)


@pytest.fixture(scope="function")
def setup_liteserv_macosx_forestdb_encryption():
    liteserv = LiteServFactory.create("macosx",
                                      version_build="1.3.1-6",
                                      host="localhost",
                                      port=59840,
                                      storage_engine="ForestDB+Encryption")

    logfile = open("{}/test.txt".format(TEST_DIR), "w")
    ls_url = liteserv.start(logfile)

    yield ls_url

    liteserv.stop(logfile)


def test_macosx_download():
    LiteServFactory.create("macosx",
                           version_build="1.3.1-6",
                           host="localhost",
                           port=59840,
                           storage_engine="SQLite")

    assert os.path.isdir("deps/binaries/couchbase-lite-macosx-enterprise_1.3.1-6")
    assert os.path.isfile("deps/binaries/couchbase-lite-macosx-enterprise_1.3.1-6/LiteServ")


def test_macosx_install(setup_liteserv_macosx_sqlite):
    # No install step for macosx
    pass


def test_macosx_full_life_cycle(setup_liteserv_macosx_sqlite):
    ls_url = setup_liteserv_macosx_sqlite

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")
    docs = client.add_docs(ls_url, db="ls_db", number=10, id_prefix="test_doc")
    assert len(docs) == 10

    client.delete_databases(ls_url)


def test_macosx_sqlite(setup_liteserv_macosx_sqlite):
    ls_url = setup_liteserv_macosx_sqlite

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    db_files = os.listdir("results/dbs/macosx/ls_db.cblite2")
    assert "db.sqlite3" in db_files
    assert "db.sqlite3-shm" in db_files
    assert "db.sqlite3-wal" in db_files

    att_files = os.listdir("results/dbs/macosx/ls_db.cblite2/attachments")
    assert att_files == []

    client.delete_databases(ls_url)

    assert not os.path.isdir("results/dbs/macosx/ls_db.cblite2/")


def test_macosx_sqlcipher(setup_liteserv_macosx_sqlcipher):
    ls_url = setup_liteserv_macosx_sqlcipher

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    db_files = os.listdir("results/dbs/macosx/ls_db.cblite2")
    assert "db.sqlite3" in db_files
    assert "db.sqlite3-shm" in db_files
    assert "db.sqlite3-wal" in db_files

    att_files = os.listdir("results/dbs/macosx/ls_db.cblite2/attachments")
    assert att_files == ["_encryption"]

    client.delete_databases(ls_url)

    assert not os.path.isdir("results/dbs/macosx/ls_db.cblite2/")


def test_macosx_forestdb(setup_liteserv_macosx_forestdb):
    ls_url = setup_liteserv_macosx_forestdb

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    db_files = os.listdir("results/dbs/macosx/ls_db.cblite2")
    assert "db.forest.0" in db_files
    assert "db.forest.meta" in db_files

    att_files = os.listdir("results/dbs/macosx/ls_db.cblite2/attachments")
    assert att_files == []

    client.delete_databases(ls_url)

    assert not os.path.isdir("results/dbs/macosx/ls_db.cblite2/")


def test_macosx_forestdb_enc(setup_liteserv_macosx_forestdb_encryption):
    ls_url = setup_liteserv_macosx_forestdb_encryption

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    db_files = os.listdir("results/dbs/macosx/ls_db.cblite2")
    assert "db.forest.0" in db_files
    assert "db.forest.meta" in db_files

    att_files = os.listdir("results/dbs/macosx/ls_db.cblite2/attachments")
    assert att_files == ["_encryption"]

    client.delete_databases(ls_url)

    assert not os.path.isdir("results/dbs/macosx/ls_db.cblite2/")
