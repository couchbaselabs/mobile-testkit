import datetime
import os
import shutil

import pytest

from keywords.constants import RESULTS_DIR
from keywords.constants import BINARY_DIR
from keywords.LiteServFactory import LiteServFactory
from keywords.MobileRestClient import MobileRestClient
from keywords.utils import version_and_build
from keywords.utils import log_info


@pytest.fixture(scope="function",
                params=["SQLite", "SQLCipher", "ForestDB", "ForestDB+Encryption"])
def liteserv_with_storage_engine_from_fixture(request):

    macosx_version = request.config.getoption("--macosx-version")

    liteserv = LiteServFactory.create("macosx",
                                      version_build=macosx_version,
                                      host="localhost",
                                      port=59840,
                                      storage_engine=request.param)
    liteserv.download()
    liteserv.install()

    yield liteserv

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


def test_macosx_logging(request, liteserv_with_storage_engine_from_fixture):

    macosx_version = request.config.getoption("--macosx-version")

    liteserv = liteserv_with_storage_engine_from_fixture

    test_name = request.node.name
    logfile = "{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now())
    liteserv.start(logfile)
    liteserv.stop()

    version, build = version_and_build(macosx_version)

    with open(logfile, "r") as f:
        contents = f.read()
        assert "LiteServ {} (build {}) is listening at".format(version, build) in contents


def test_macosx_full_life_cycle(request, liteserv_with_storage_engine_from_fixture):

    liteserv = liteserv_with_storage_engine_from_fixture

    test_name = request.node.name
    logfile = "{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now())
    ls_url = liteserv.start(logfile)

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")
    docs = client.add_docs(ls_url, db="ls_db", number=10, id_prefix="test_doc")
    assert len(docs) == 10

    client.delete_databases(ls_url)

    liteserv.stop()


def test_macosx_storage_engines(request, liteserv_with_storage_engine_from_fixture):

    liteserv = liteserv_with_storage_engine_from_fixture

    test_name = request.node.name
    logfile = "{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now())
    ls_url = liteserv.start(logfile)

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    storage_engine = liteserv.storage_engine
    log_info("Testing storage_engine: {}".format(storage_engine))

    if storage_engine == "SQLite":

        db_files = os.listdir("results/dbs/macosx/ls_db.cblite2")
        assert "db.sqlite3" in db_files
        assert "db.sqlite3-shm" in db_files
        assert "db.sqlite3-wal" in db_files

        att_files = os.listdir("results/dbs/macosx/ls_db.cblite2/attachments")
        assert att_files == []

        client.delete_databases(ls_url)
        assert not os.path.isdir("results/dbs/macosx/ls_db.cblite2/")

    elif storage_engine == "SQLCipher":

        db_files = os.listdir("results/dbs/macosx/ls_db.cblite2")
        assert "db.sqlite3" in db_files
        assert "db.sqlite3-shm" in db_files
        assert "db.sqlite3-wal" in db_files

        att_files = os.listdir("results/dbs/macosx/ls_db.cblite2/attachments")
        assert att_files == ["_encryption"]

        client.delete_databases(ls_url)
        assert not os.path.isdir("results/dbs/macosx/ls_db.cblite2/")

    elif storage_engine == "ForestDB":

        db_files = os.listdir("results/dbs/macosx/ls_db.cblite2")
        assert "db.forest.0" in db_files
        assert "db.forest.meta" in db_files

        att_files = os.listdir("results/dbs/macosx/ls_db.cblite2/attachments")
        assert att_files == []

        client.delete_databases(ls_url)
        assert not os.path.isdir("results/dbs/macosx/ls_db.cblite2/")

    elif storage_engine == "ForestDB+Encryption":

        db_files = os.listdir("results/dbs/macosx/ls_db.cblite2")
        assert "db.forest.0" in db_files
        assert "db.forest.meta" in db_files

        att_files = os.listdir("results/dbs/macosx/ls_db.cblite2/attachments")
        assert att_files == ["_encryption"]

        client.delete_databases(ls_url)

        assert not os.path.isdir("results/dbs/macosx/ls_db.cblite2/")

    else:
        pytest.xfail("Invalid storage engine")

    liteserv.stop()
