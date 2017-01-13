import datetime
import os
import shutil

import pytest

from keywords.constants import RESULTS_DIR
from keywords.constants import BINARY_DIR
from keywords.LiteServFactory import LiteServFactory
from keywords.MobileRestClient import MobileRestClient
from keywords.utils import log_info


@pytest.fixture(scope="function",
                params=["SQLite", "SQLCipher", "ForestDB", "ForestDB+Encryption"])
def liteserv_with_storage_engine_from_fixture(request):

    net_version = request.config.getoption("--net-version")

    liteserv = LiteServFactory.create("net-mono",
                                      version_build=net_version,
                                      host="localhost",
                                      port=59840,
                                      storage_engine=request.param)
    liteserv.download()
    liteserv.install()

    yield liteserv

    liteserv.remove()


def test_net_mono_download(request):

    shutil.rmtree("{}/".format(BINARY_DIR))
    os.makedirs("{}".format(BINARY_DIR))

    net_version = request.config.getoption("--net-version")

    liteserv = LiteServFactory.create("net-mono",
                                      version_build=net_version,
                                      host="localhost",
                                      port=59840,
                                      storage_engine="SQLite")

    liteserv.download()

    assert os.path.isdir("deps/binaries/couchbase-lite-net-mono-{}-liteserv".format(net_version))
    assert os.path.isfile("deps/binaries/couchbase-lite-net-mono-{}-liteserv/net45/LiteServ.exe".format(net_version))
    assert not os.path.isfile("deps/binaries/couchbase-lite-net-mono-{}-liteserv.zip".format(net_version))


def test_net_mono_install():
    # No install step for net-mono since it is a commandline utility
    pass


def test_net_mono_remove():
    # No install step for net-mono since it is a commandline utility
    pass


def test_net_mono_logging(request, liteserv_with_storage_engine_from_fixture):

    liteserv = liteserv_with_storage_engine_from_fixture

    test_name = request.node.name
    logfile = "{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now())
    liteserv.start(logfile)
    liteserv.stop()

    with open(logfile, "r") as f:
        contents = f.read()
        assert "Starting Manager version: .NET OS X" in contents


def test_net_mono_full_life_cycle(request, liteserv_with_storage_engine_from_fixture):

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


def test_net_mono_storage_engine(request, liteserv_with_storage_engine_from_fixture):

    liteserv = liteserv_with_storage_engine_from_fixture

    test_name = request.node.name
    logfile = "{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now())
    ls_url = liteserv.start(logfile)

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    storage_engine = liteserv.storage_engine
    log_info("Testing storage_engine: {}".format(storage_engine))

    if storage_engine == "SQLite":

        db_files = os.listdir("results/dbs/net-mono/ls_db.cblite2")
        assert "db.sqlite3" in db_files
        assert "db.sqlite3-shm" in db_files
        assert "db.sqlite3-wal" in db_files

        att_files = os.listdir("results/dbs/net-mono/ls_db.cblite2/attachments")
        assert att_files == []

        client.delete_databases(ls_url)
        assert not os.path.isdir("results/dbs/net-mono/ls_db.cblite2/")

    elif storage_engine == "SQLCipher":

        db_files = os.listdir("results/dbs/net-mono/ls_db.cblite2")
        assert "db.sqlite3" in db_files
        assert "db.sqlite3-shm" in db_files
        assert "db.sqlite3-wal" in db_files

        att_files = os.listdir("results/dbs/net-mono/ls_db.cblite2/attachments")
        assert att_files == ["_encryption"]

        client.delete_databases(ls_url)
        assert not os.path.isdir("results/dbs/net-mono/ls_db.cblite2/")

    elif storage_engine == "ForestDB":

        db_files = os.listdir("results/dbs/net-mono/ls_db.cblite2")
        assert "db.forest.0" in db_files
        assert "db.forest.meta" in db_files

        att_files = os.listdir("results/dbs/net-mono/ls_db.cblite2/attachments")
        assert att_files == []

        client.delete_databases(ls_url)
        assert not os.path.isdir("results/dbs/net-mono/ls_db.cblite2/")

    elif storage_engine == "ForestDB+Encryption":

        db_files = os.listdir("results/dbs/net-mono/ls_db.cblite2")
        assert "db.forest.0" in db_files
        assert "db.forest.meta" in db_files

        att_files = os.listdir("results/dbs/net-mono/ls_db.cblite2/attachments")
        assert att_files == ["_encryption"]

        client.delete_databases(ls_url)
        assert not os.path.isdir("results/dbs/net-mono/ls_db.cblite2/")

    else:
        pytest.xfail("Invalid Storage Engine")

    liteserv.stop()
