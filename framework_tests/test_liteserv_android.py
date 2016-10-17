import os

import pytest
import shutil

from keywords.constants import TEST_DIR
from keywords.constants import BINARY_DIR
from keywords.LiteServFactory import LiteServFactory
from keywords.MobileRestClient import MobileRestClient


@pytest.fixture(scope="function")
def setup_liteserv_android_sqlite(request):

    android_host = request.config.getoption("--android-host")

    liteserv = LiteServFactory.create("android",
                                      version_build="1.3.1-30",
                                      host=android_host,
                                      port=59840,
                                      storage_engine="SQLite")

    logfile = open("{}/test.txt".format(TEST_DIR), "w")
    ls_url = liteserv.start(logfile)

    yield ls_url

    liteserv.stop(logfile)


@pytest.fixture(scope="function")
def setup_liteserv_android_sqlcipher(request):

    android_host = request.config.getoption("--android-host")

    liteserv = LiteServFactory.create("android",
                                      version_build="1.3.1-30",
                                      host=android_host,
                                      port=59840,
                                      storage_engine="SQLCipher")

    logfile = open("{}/test.txt".format(TEST_DIR), "w")
    ls_url = liteserv.start(logfile)

    yield ls_url

    liteserv.stop(logfile)


@pytest.fixture(scope="function")
def setup_liteserv_android_forestdb(request):

    android_host = request.config.getoption("--android-host")

    liteserv = LiteServFactory.create("android",
                                      version_build="1.3.1-30",
                                      host=android_host,
                                      port=59840,
                                      storage_engine="ForestDB")

    logfile = open("{}/test.txt".format(TEST_DIR), "w")
    ls_url = liteserv.start(logfile)

    yield ls_url

    liteserv.stop(logfile)


@pytest.fixture(scope="function")
def setup_liteserv_android_forestdb_encryption(request):

    android_host = request.config.getoption("--android-host")

    liteserv = LiteServFactory.create("android",
                                      version_build="1.3.1-30",
                                      host=android_host,
                                      port=59840,
                                      storage_engine="ForestDB+Encryption")

    logfile = open("{}/test.txt".format(TEST_DIR), "w")
    ls_url = liteserv.start(logfile)

    yield ls_url

    liteserv.stop(logfile)


def test_android_download(request):

    android_host = request.config.getoption("--android-host")

    shutil.rmtree("{}/".format(BINARY_DIR))
    os.makedirs("{}".format(BINARY_DIR))

    liteserv = LiteServFactory.create("android",
                                      version_build="1.3.1-30",
                                      host=android_host,
                                      port=59840,
                                      storage_engine="SQLite")

    liteserv.download()

    assert len(os.listdir("deps/binaries")) == 1
    assert os.path.isfile("deps/binaries/couchbase-lite-android-liteserv-SQLite-1.3.1-30-debug.apk")

    liteserv_two = LiteServFactory.create("android",
                                          version_build="1.3.1-30",
                                          host=android_host,
                                          port=59840,
                                          storage_engine="SQLCipher")

    liteserv_two.download()

    assert len(os.listdir("deps/binaries")) == 2
    assert os.path.isfile("deps/binaries/couchbase-lite-android-liteserv-SQLCipher-ForestDB-Encryption-1.3.1-30-debug.apk")


def test_android_full_life_cycle(setup_liteserv_android_sqlite):
    ls_url = setup_liteserv_android_sqlite

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")
    docs = client.add_docs(ls_url, db="ls_db", number=10, id_prefix="test_doc")
    assert len(docs) == 10

    client.delete_databases(ls_url)


def test_android_sqlite(setup_liteserv_android_sqlite):
    ls_url = setup_liteserv_android_sqlite

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    db_files = os.listdir("results/dbs/android/ls_db.cblite2")
    assert "db.sqlite3" in db_files
    assert "db.sqlite3-shm" in db_files
    assert "db.sqlite3-wal" in db_files

    att_files = os.listdir("results/dbs/android/ls_db.cblite2/attachments")
    assert att_files == []

    client.delete_databases(ls_url)

    assert not os.path.isdir("results/dbs/android/ls_db.cblite2/")


def test_android_sqlcipher(setup_liteserv_android_sqlcipher):
    ls_url = setup_liteserv_android_sqlcipher

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    db_files = os.listdir("results/dbs/android/ls_db.cblite2")
    assert "db.sqlite3" in db_files
    assert "db.sqlite3-shm" in db_files
    assert "db.sqlite3-wal" in db_files

    att_files = os.listdir("results/dbs/android/ls_db.cblite2/attachments")
    assert att_files == ["_encryption"]

    client.delete_databases(ls_url)

    assert not os.path.isdir("results/dbs/android/ls_db.cblite2/")


def test_android_forestdb(setup_liteserv_android_forestdb):
    ls_url = setup_liteserv_android_forestdb

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    db_files = os.listdir("results/dbs/android/ls_db.cblite2")
    assert "db.forest.0" in db_files
    assert "db.forest.meta" in db_files

    att_files = os.listdir("results/dbs/android/ls_db.cblite2/attachments")
    assert att_files == []

    client.delete_databases(ls_url)

    assert not os.path.isdir("results/dbs/android/ls_db.cblite2/")


def test_android_forestdb_enc(setup_liteserv_android_forestdb_encryption):
    ls_url = setup_liteserv_android_forestdb_encryption

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    db_files = os.listdir("results/dbs/android/ls_db.cblite2")
    assert "db.forest.0" in db_files
    assert "db.forest.meta" in db_files

    att_files = os.listdir("results/dbs/android/ls_db.cblite2/attachments")
    assert att_files == ["_encryption"]

    client.delete_databases(ls_url)

    assert not os.path.isdir("results/dbs/android/ls_db.cblite2/")
