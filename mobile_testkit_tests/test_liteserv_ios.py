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


@pytest.fixture(scope="function",
                params=["SQLite", "SQLCipher", "ForestDB", "ForestDB+Encryption"])
def liteserv_with_storage_engine_from_fixture(request):

    ios_version = request.config.getoption("--ios-version")
    ios_host = request.config.getoption("--ios-host")

    liteserv = LiteServFactory.create("ios",
                                      version_build=ios_version,
                                      host=ios_host,
                                      port=59840,
                                      storage_engine=request.param)
    liteserv.download()
    liteserv.install()

    yield liteserv

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
def test_ios_full_life_cycle(request, liteserv_with_storage_engine_from_fixture):
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


@pytest.mark.skip(reason="Need to wait until build is setup")
def test_ios_storage_engines(request, liteserv_with_storage_engine_from_fixture):
    liteserv = liteserv_with_storage_engine_from_fixture

    test_name = request.node.name
    logfile = "{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now())
    liteserv.start(logfile)

    # TODO: find a way to verify this

    liteserv.stop()
