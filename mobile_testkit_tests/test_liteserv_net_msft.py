import datetime
import os
import shutil

import pytest

from keywords.constants import RESULTS_DIR
from keywords.constants import BINARY_DIR
from keywords.LiteServFactory import LiteServFactory
from keywords.MobileRestClient import MobileRestClient
from keywords.utils import log_info


# Due to the runtime of net MSFT ansible setup, only download and install once for each storage type
@pytest.fixture(scope="module",
                params=["SQLite", "SQLCipher", "ForestDB", "ForestDB+Encryption"])
def liteserv_with_storage_engine_from_fixture(request):

    net_version = request.config.getoption("--net-version")
    net_msft_host = request.config.getoption("--net-msft-host")

    liteserv = LiteServFactory.create("net-msft",
                                      version_build=net_version,
                                      host=net_msft_host,
                                      port=59840,
                                      storage_engine=request.param)
    liteserv.download()
    liteserv.install()

    yield liteserv

    liteserv.remove()


def test_net_msft_install():
    # TODO - using winrm
    pass


def test_net_msft_remove():
    # TODO - using winrm
    pass


# Ansible provisioning fails from time to time
# TODO: Reenable when updating from 2.1.1.0
@pytest.mark.flakey
def test_net_msft_logging(request, liteserv_with_storage_engine_from_fixture):

    liteserv = liteserv_with_storage_engine_from_fixture

    test_name = request.node.name
    logfile = "{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now())
    liteserv.start(logfile)
    liteserv.stop()

    with open(logfile, "r") as f:
        contents = f.read()
        assert "Starting Manager version: .NET Microsoft Windows" in contents


# Ansible provisioning fails from time to time
# TODO: Reenable when updating from 2.1.1.0
@pytest.mark.flakey
def test_net_msft_full_life_cycle(request, liteserv_with_storage_engine_from_fixture):

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


# Ansible provisioning fails from time to time
# TODO: Reenable when updating from 2.1.1.0
@pytest.mark.flakey
def test_net_msft_storage_engine(request, liteserv_with_storage_engine_from_fixture):

    liteserv = liteserv_with_storage_engine_from_fixture

    test_name = request.node.name
    logfile = "{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now())
    ls_url = liteserv.start(logfile)

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    liteserv.stop()

    storage_engine = liteserv.storage_engine
    log_info("Testing storage_engine: {}".format(storage_engine))

    with open(logfile, "r") as f:
        contents = f.read()

        if storage_engine == "SQLite":

            # Note: SQLite mode uses SQLCipher by default
            assert "Using Couchbase.Lite.Storage.SQLCipher.SqliteCouchStore for db at C:\Users\user\Desktop\LiteServ\ls_db.cblite2" in contents
            assert "encryption key given" not in contents

        elif storage_engine == "SQLCipher":

            assert "Using Couchbase.Lite.Storage.SQLCipher.SqliteCouchStore for db at C:\Users\user\Desktop\LiteServ\ls_db.cblite2" in contents
            assert "Open C:\Users\user\Desktop\LiteServ\ls_db.cblite2\db.sqlite3" in contents
            assert "encryption key given"

        elif storage_engine == "ForestDB":

            assert "Using Couchbase.Lite.Storage.ForestDB.ForestDBCouchStore for db at C:\Users\user\Desktop\LiteServ\ls_db.cblite2" in contents
            assert "Database is encrypted; setting CBForest encryption key" not in contents

        elif storage_engine == "ForestDB+Encryption":

            assert "Using Couchbase.Lite.Storage.ForestDB.ForestDBCouchStore for db at C:\Users\user\Desktop\LiteServ\ls_db.cblite2" in contents
            assert "Database is encrypted; setting CBForest encryption key" in contents

        else:
            pytest.xfail("Invalid Storage Engine")
