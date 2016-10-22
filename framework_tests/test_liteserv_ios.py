import os
import datetime
import shutil

import pytest

from keywords.constants import RESULTS_DIR
from keywords.constants import BINARY_DIR
from keywords.LiteServFactory import LiteServFactory
from keywords.MobileRestClient import MobileRestClient
from keywords.utils import version_and_build


@pytest.fixture(scope="function")
def setup_liteserv_ios_no_launch(request):

    ios_version = request.config.getoption("--ios-version")
    ios_host = request.config.getoption("--ios-host")

    liteserv = LiteServFactory.create("ios",
                                      version_build=ios_version,
                                      host=ios_host,
                                      port=59840,
                                      storage_engine="SQLite")
    liteserv.download()
    liteserv.install()

    yield liteserv

    liteserv.remove()


@pytest.fixture(scope="function")
def setup_liteserv_ios_sqlite(request):

    ios_version = request.config.getoption("--ios-version")
    ios_host = request.config.getoption("--ios-host")

    liteserv = LiteServFactory.create("ios",
                                      version_build=ios_version,
                                      host=ios_host,
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
def setup_liteserv_ios_sqlcipher(request):

    ios_version = request.config.getoption("--ios-version")
    ios_host = request.config.getoption("--ios-host")

    liteserv = LiteServFactory.create("ios",
                                      version_build=ios_version,
                                      host=ios_host,
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
def setup_liteserv_ios_forestdb(request):

    ios_version = request.config.getoption("--ios-version")
    ios_host = request.config.getoption("--ios-host")

    liteserv = LiteServFactory.create("ios",
                                      version_build=ios_version,
                                      host=ios_host,
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
def setup_liteserv_ios_forestdb_encryption(request):

    ios_version = request.config.getoption("--ios-version")
    ios_host = request.config.getoption("--ios-host")

    liteserv = LiteServFactory.create("ios",
                                      version_build=ios_version,
                                      host=ios_host,
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


@pytest.mark.skip(reason="Need to wait until build is setup")
def test_ios_download(request):

    ios_version = request.config.getoption("--ios-version")
    ios_host = request.config.getoption("--ios-host")

    shutil.rmtree("{}/".format(BINARY_DIR))
    os.makedirs("{}".format(BINARY_DIR))

    liteserv = LiteServFactory.create("ios",
                                      version_build=ios_version,
                                      host=ios_host,
                                      port=59840,
                                      storage_engine="SQLite")

    liteserv.download()


@pytest.mark.skip(reason="Need to wait until build is setup")
def test_ios_install_uninstall(setup_liteserv_ios_no_launch):
    liteserv = setup_liteserv_ios_no_launch
    # launch verification in the install method
    liteserv.install()


@pytest.mark.skip(reason="Need to wait until build is setup")
def test_ios_logging(request, setup_liteserv_ios_logging):

    liteserv = setup_liteserv_ios_logging

    test_name = request.node.name

    logfile = "{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now())
    liteserv.start(logfile)

    liteserv.stop()

    version, build = version_and_build(liteserv.version_build)

    with open(logfile, "r") as f:
        contents = f.read()
        assert "LiteServ {} (build {}) is listening at".format(version, build) in contents


@pytest.mark.skip(reason="Need to wait until build is setup")
def test_ios_full_life_cycle(setup_liteserv_ios_sqlite):
    ls_url = setup_liteserv_ios_sqlite

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")
    docs = client.add_docs(ls_url, db="ls_db", number=10, id_prefix="test_doc")
    assert len(docs) == 10

    client.delete_databases(ls_url)


@pytest.mark.skip(reason="Need to wait until build is setup")
def test_ios_sqlite(setup_liteserv_ios_sqlite):
    ls_url = setup_liteserv_ios_sqlite

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    # TODO: find a way to verify this


@pytest.mark.skip(reason="Need to wait until build is setup")
def test_ios_sqlcipher(setup_liteserv_ios_sqlcipher):
    ls_url = setup_liteserv_ios_sqlcipher

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    # TODO: find a way to verify this


@pytest.mark.skip(reason="Need to wait until build is setup")
def test_ios_forestdb(setup_liteserv_ios_forestdb):
    ls_url = setup_liteserv_ios_forestdb

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    # TODO: find a way to verify this


@pytest.mark.skip(reason="Need to wait until build is setup")
def test_ios_forestdb_enc(setup_liteserv_ios_forestdb_encryption):
    ls_url = setup_liteserv_ios_forestdb_encryption

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    # TODO: find a way to verify this
