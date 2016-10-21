import os

import pytest
import shutil

from keywords.constants import TEST_DIR
from keywords.constants import BINARY_DIR
from keywords.LiteServFactory import LiteServFactory
from keywords.MobileRestClient import MobileRestClient


@pytest.fixture(scope="function")
def setup_liteserv_net_msft_no_launch(request):

    net_msft_host = request.config.getoption("--net-msft-host")

    liteserv = LiteServFactory.create("net-msft",
                                      version_build="1.3.1-13",
                                      host=net_msft_host,
                                      port=59840,
                                      storage_engine="SQLite")
    liteserv.download()
    liteserv.install()

    yield liteserv

    liteserv.remove()


@pytest.fixture(scope="function")
def setup_liteserv_net_msft_sqlite(request):

    net_msft_host = request.config.getoption("--net-msft-host")

    liteserv = LiteServFactory.create("net-msft",
                                      version_build="1.3.1-13",
                                      host=net_msft_host,
                                      port=59840,
                                      storage_engine="SQLite")
    liteserv.download()
    liteserv.install()

    yield liteserv

    liteserv.remove()


@pytest.fixture(scope="function")
def setup_liteserv_net_msft_sqlcipher(request):

    net_msft_host = request.config.getoption("--net-msft-host")

    liteserv = LiteServFactory.create("net-msft",
                                      version_build="1.3.1-13",
                                      host=net_msft_host,
                                      port=59840,
                                      storage_engine="SQLCipher")
    liteserv.download()
    liteserv.install()

    yield liteserv

    liteserv.remove()


@pytest.fixture(scope="function")
def setup_liteserv_net_msft_forestdb(request):

    net_msft_host = request.config.getoption("--net-msft-host")

    liteserv = LiteServFactory.create("net-msft",
                                      version_build="1.3.1-13",
                                      host=net_msft_host,
                                      port=59840,
                                      storage_engine="ForestDB")
    liteserv.download()
    liteserv.install()

    yield liteserv

    liteserv.remove()


@pytest.fixture(scope="function")
def setup_liteserv_net_msft_forestdb_encryption(request):

    net_msft_host = request.config.getoption("--net-msft-host")

    liteserv = LiteServFactory.create("net-msft",
                                      version_build="1.3.1-13",
                                      host=net_msft_host,
                                      port=59840,
                                      storage_engine="ForestDB+Encryption")
    liteserv.download()
    liteserv.install()

    yield liteserv

    liteserv.remove()


def test_net_msft_download(request):

    shutil.rmtree("{}/".format(BINARY_DIR))
    os.makedirs("{}".format(BINARY_DIR))

    net_msft_host = request.config.getoption("--net-msft-host")

    liteserv = LiteServFactory.create("net-msft",
                                      version_build="1.3.1-13",
                                      host=net_msft_host,
                                      port=59840,
                                      storage_engine="SQLite")

    liteserv.download()

    # TODO - using winrm
    pass


def test_net_msft_install():
    # TODO - using winrm
    pass


def test_net_msft_remove():
    # TODO - using winrm
    pass


def test_net_msft_logging(setup_liteserv_net_msft_no_launch):
    liteserv = setup_liteserv_net_msft_no_launch

    logfile = "{}/test.txt".format(TEST_DIR)
    _ = liteserv.start(logfile)
    liteserv.stop()

    with open("{}/test.txt".format(TEST_DIR), "r") as f:
        contents = f.read()
        assert "Starting Manager version: .NET Microsoft Windows" in contents


def test_net_msft_full_life_cycle(setup_liteserv_net_msft_sqlite):

    liteserv = setup_liteserv_net_msft_sqlite

    logfile = "{}/test.txt".format(TEST_DIR)
    ls_url = liteserv.start(logfile)

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")
    docs = client.add_docs(ls_url, db="ls_db", number=10, id_prefix="test_doc")
    assert len(docs) == 10

    client.delete_databases(ls_url)

    liteserv.stop()


def test_net_msft_sqlite(setup_liteserv_net_msft_sqlite):
    liteserv = setup_liteserv_net_msft_sqlite

    logfile = "{}/test.txt".format(TEST_DIR)
    ls_url = liteserv.start(logfile)

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    liteserv.stop()

    with open("{}/test.txt".format(TEST_DIR), "r") as f:
        contents = f.read()
        # Note: SQLite mode uses SQLCipher by default
        assert "Using Couchbase.Lite.Storage.SQLCipher.SqliteCouchStore for db at C:\Users\user\Desktop\LiteServ\ls_db.cblite2" in contents
        assert "encryption key given" not in contents


def test_net_msft_sqlcipher(setup_liteserv_net_msft_sqlcipher):
    liteserv = setup_liteserv_net_msft_sqlcipher

    logfile = "{}/test.txt".format(TEST_DIR)
    ls_url = liteserv.start(logfile)

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    liteserv.stop()

    with open("{}/test.txt".format(TEST_DIR), "r") as f:
        contents = f.read()
        assert "Using Couchbase.Lite.Storage.SQLCipher.SqliteCouchStore for db at C:\Users\user\Desktop\LiteServ\ls_db.cblite2" in contents
        assert "Open C:\Users\user\Desktop\LiteServ\ls_db.cblite2\db.sqlite3" in contents
        assert "encryption key given"


def test_net_msft_forestdb_noenc(setup_liteserv_net_msft_forestdb):
    liteserv = setup_liteserv_net_msft_forestdb

    logfile = "{}/test.txt".format(TEST_DIR)
    ls_url = liteserv.start(logfile)

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    liteserv.stop()

    with open("{}/test.txt".format(TEST_DIR), "r") as f:
        contents = f.read()
        assert "Using Couchbase.Lite.Storage.ForestDB.ForestDBCouchStore for db at C:\Users\user\Desktop\LiteServ\ls_db.cblite2" in contents
        assert "Database is encrypted; setting CBForest encryption key" not in contents


def test_net_msft_forestdb_enc(setup_liteserv_net_msft_forestdb_encryption):
    liteserv = setup_liteserv_net_msft_forestdb_encryption

    logfile = "{}/test.txt".format(TEST_DIR)
    ls_url = liteserv.start(logfile)

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    liteserv.stop()

    with open("{}/test.txt".format(TEST_DIR), "r") as f:
        contents = f.read()
        assert "Using Couchbase.Lite.Storage.ForestDB.ForestDBCouchStore for db at C:\Users\user\Desktop\LiteServ\ls_db.cblite2" in contents
        assert "Database is encrypted; setting CBForest encryption key" in contents
