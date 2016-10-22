import datetime
import os
import shutil

import pytest

from keywords.constants import RESULTS_DIR
from keywords.constants import BINARY_DIR
from keywords.LiteServFactory import LiteServFactory
from keywords.MobileRestClient import MobileRestClient


@pytest.fixture(scope="function")
def setup_liteserv_net_mono_logging():
    liteserv = LiteServFactory.create("net-mono",
                                      version_build="1.3.1-13",
                                      host="localhost",
                                      port=59840,
                                      storage_engine="SQLite")
    liteserv.download()
    liteserv.install()

    yield liteserv

    liteserv.remove()


@pytest.fixture(scope="function")
def setup_liteserv_net_mono_sqlite(request):
    liteserv = LiteServFactory.create("net-mono",
                                      version_build="1.3.1-13",
                                      host="localhost",
                                      port=59840,
                                      storage_engine="SQLite")
    liteserv.download()
    liteserv.install()

    test_name = request.node.name
    logfile = "{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now())
    ls_url = liteserv.start(logfile)

    yield ls_url

    liteserv.stop()
    liteserv.remove()


@pytest.fixture(scope="function")
def setup_liteserv_net_mono_sqlcipher(request):
    liteserv = LiteServFactory.create("net-mono",
                                      version_build="1.3.1-13",
                                      host="localhost",
                                      port=59840,
                                      storage_engine="SQLCipher")
    liteserv.download()
    liteserv.install()

    test_name = request.node.name
    logfile = "{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now())
    ls_url = liteserv.start(logfile)

    yield ls_url

    liteserv.stop()
    liteserv.remove()


@pytest.fixture(scope="function")
def setup_liteserv_net_mono_forestdb(request):
    liteserv = LiteServFactory.create("net-mono",
                                      version_build="1.3.1-13",
                                      host="localhost",
                                      port=59840,
                                      storage_engine="ForestDB")
    liteserv.download()
    liteserv.install()

    test_name = request.node.name
    logfile = "{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now())
    ls_url = liteserv.start(logfile)

    yield ls_url

    liteserv.stop()
    liteserv.remove()


@pytest.fixture(scope="function")
def setup_liteserv_net_mono_forestdb_encryption(request):
    liteserv = LiteServFactory.create("net-mono",
                                      version_build="1.3.1-13",
                                      host="localhost",
                                      port=59840,
                                      storage_engine="ForestDB+Encryption")
    liteserv.download()
    liteserv.install()

    test_name = request.node.name
    logfile = "{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now())
    ls_url = liteserv.start(logfile)

    yield ls_url

    liteserv.stop()
    liteserv.remove()


def test_net_mono_download():

    shutil.rmtree("{}/".format(BINARY_DIR))
    os.makedirs("{}".format(BINARY_DIR))

    liteserv = LiteServFactory.create("net-mono",
                                      version_build="1.3.1-13",
                                      host="localhost",
                                      port=59840,
                                      storage_engine="SQLite")

    liteserv.download()

    assert os.path.isdir("deps/binaries/couchbase-lite-net-mono-1.3.1-13-liteserv")
    assert os.path.isfile("deps/binaries/couchbase-lite-net-mono-1.3.1-13-liteserv/LiteServ.exe")
    assert not os.path.isfile("deps/binaries/couchbase-lite-net-mono-1.3.1-13-liteserv.zip")


def test_net_mono_install():
    # No install step for net-mono since it is a commandline utility
    pass


def test_net_mono_remove():
    # No install step for net-mono since it is a commandline utility
    pass


def test_net_mono_logging(request, setup_liteserv_net_mono_logging):

    liteserv = setup_liteserv_net_mono_logging

    test_name = request.node.name
    logfile = "{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now())
    liteserv.start(logfile)
    liteserv.stop()

    with open(logfile, "r") as f:
        contents = f.read()
        assert "Starting Manager version: .NET OS X" in contents


def test_net_mono_full_life_cycle(setup_liteserv_net_mono_sqlite):
    ls_url = setup_liteserv_net_mono_sqlite

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")
    docs = client.add_docs(ls_url, db="ls_db", number=10, id_prefix="test_doc")
    assert len(docs) == 10

    client.delete_databases(ls_url)


def test_net_mono_sqlite(setup_liteserv_net_mono_sqlite):
    ls_url = setup_liteserv_net_mono_sqlite

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    db_files = os.listdir("results/dbs/net-mono/ls_db.cblite2")
    assert "db.sqlite3" in db_files
    assert "db.sqlite3-shm" in db_files
    assert "db.sqlite3-wal" in db_files

    att_files = os.listdir("results/dbs/net-mono/ls_db.cblite2/attachments")
    assert att_files == []

    client.delete_databases(ls_url)

    assert not os.path.isdir("results/dbs/net-mono/ls_db.cblite2/")


def test_net_mono_sqlcipher(setup_liteserv_net_mono_sqlcipher):
    ls_url = setup_liteserv_net_mono_sqlcipher

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    db_files = os.listdir("results/dbs/net-mono/ls_db.cblite2")
    assert "db.sqlite3" in db_files
    assert "db.sqlite3-shm" in db_files
    assert "db.sqlite3-wal" in db_files

    att_files = os.listdir("results/dbs/net-mono/ls_db.cblite2/attachments")
    assert att_files == ["_encryption"]

    client.delete_databases(ls_url)

    assert not os.path.isdir("results/dbs/net-mono/ls_db.cblite2/")


def test_net_mono_forestdb(setup_liteserv_net_mono_forestdb):
    ls_url = setup_liteserv_net_mono_forestdb

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    db_files = os.listdir("results/dbs/net-mono/ls_db.cblite2")
    assert "db.forest.0" in db_files
    assert "db.forest.meta" in db_files

    att_files = os.listdir("results/dbs/net-mono/ls_db.cblite2/attachments")
    assert att_files == []

    client.delete_databases(ls_url)

    assert not os.path.isdir("results/dbs/net-mono/ls_db.cblite2/")


def test_net_mono_forestdb_enc(setup_liteserv_net_mono_forestdb_encryption):
    ls_url = setup_liteserv_net_mono_forestdb_encryption

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    db_files = os.listdir("results/dbs/net-mono/ls_db.cblite2")
    assert "db.forest.0" in db_files
    assert "db.forest.meta" in db_files

    att_files = os.listdir("results/dbs/net-mono/ls_db.cblite2/attachments")
    assert att_files == ["_encryption"]

    client.delete_databases(ls_url)

    assert not os.path.isdir("results/dbs/net-mono/ls_db.cblite2/")
