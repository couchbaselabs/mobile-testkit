import datetime
import os
import shutil

import pytest

from keywords.constants import RESULTS_DIR
from keywords.constants import BINARY_DIR
from keywords.LiteServFactory import LiteServFactory
from keywords.MobileRestClient import MobileRestClient
from keywords.utils import version_and_build


@pytest.fixture(scope="function")
def setup_liteserv_macosx_logging(request):

    macosx_version = request.config.getoption("--macosx-version")

    liteserv = LiteServFactory.create("macosx",
                                      version_build=macosx_version,
                                      host="localhost",
                                      port=59840,
                                      storage_engine="SQLite")
    liteserv.download()
    liteserv.install()

    yield liteserv

    liteserv.remove()


@pytest.fixture(scope="function")
def setup_liteserv_macosx_sqlite(request):

    macosx_version = request.config.getoption("--macosx-version")

    liteserv = LiteServFactory.create("macosx",
                                      version_build=macosx_version,
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
def setup_liteserv_macosx_sqlcipher(request):

    macosx_version = request.config.getoption("--macosx-version")

    liteserv = LiteServFactory.create("macosx",
                                      version_build=macosx_version,
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
def setup_liteserv_macosx_forestdb(request):

    macosx_version = request.config.getoption("--macosx-version")

    liteserv = LiteServFactory.create("macosx",
                                      version_build=macosx_version,
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
def setup_liteserv_macosx_forestdb_encryption(request):

    macosx_version = request.config.getoption("--macosx-version")

    liteserv = LiteServFactory.create("macosx",
                                      version_build=macosx_version,
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


def test_macosx_download(request):

    shutil.rmtree("{}/".format(BINARY_DIR))
    os.makedirs("{}".format(BINARY_DIR))

    macosx_version = request.config.getoption("--macosx-version")

    liteserv = LiteServFactory.create("macosx",
                                      version_build=macosx_version,
                                      host="localhost",
                                      port=59840,
                                      storage_engine="SQLite")

    liteserv.download()

    assert os.path.isdir("deps/binaries/couchbase-lite-macosx-enterprise_{}".format(macosx_version))
    assert os.path.isfile("deps/binaries/couchbase-lite-macosx-enterprise_{}/LiteServ".format(macosx_version))
    assert not os.path.isfile("deps/binaries/couchbase-lite-macosx-enterprise_{}.zip".format(macosx_version))


def test_macosx_install():
    # No install step for macosx
    pass


def test_macosx_remove():
    # No install step for macosx
    pass


def test_macosx_logging(request, setup_liteserv_macosx_logging):

    macosx_version = request.config.getoption("--macosx-version")

    liteserv = setup_liteserv_macosx_logging

    test_name = request.node.name
    logfile = "{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now())
    liteserv.start(logfile)
    liteserv.stop()

    version, build = version_and_build(macosx_version)

    with open(logfile, "r") as f:
        contents = f.read()
        assert "LiteServ {} (build {}) is listening at".format(version, build) in contents


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
