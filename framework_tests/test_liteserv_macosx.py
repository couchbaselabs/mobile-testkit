import os

import pytest

from keywords.constants import TEST_DIR
from keywords.LiteServFactory import LiteServFactory
from keywords.MobileRestClient import MobileRestClient


@pytest.fixture(scope="module")
def setup_liteserv_macosx():
    liteserv = LiteServFactory.create("macosx",
                                      version_build="1.3.1-6",
                                      host="localhost",
                                      port=59840,
                                      storage_engine="SQLite")

    yield liteserv


def test_macosx_download(setup_liteserv_macosx):
    liteserv = setup_liteserv_macosx
    liteserv.download()

    assert os.path.isdir("deps/binaries/couchbase-lite-macosx-enterprise_1.3.1-6")
    assert os.path.isfile("deps/binaries/couchbase-lite-macosx-enterprise_1.3.1-6/LiteServ")


def test_macosx_install(setup_liteserv_macosx):
    # No install step for macosx
    pass


def test_macosx_full_life_cycle(setup_liteserv_macosx):
    liteserv = setup_liteserv_macosx

    logfile = open("{}/test.txt".format(TEST_DIR), "w")
    ls_url = liteserv.start(logfile)

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")
    docs = client.add_docs(ls_url, db="ls_db", number=10, id_prefix="test_doc")
    assert len(docs) == 10

    client.delete_databases(ls_url)

    liteserv.stop(logfile)
    # TODO assert logfile


def test_macosx_sqllite(setup_liteserv_macosx):
    # TODO
    pass


def test_macosx_sqlcipher(setup_liteserv_macosx):
    # TODO
    pass


def test_macosx_forestdb(setup_liteserv_macosx):
    # TODO
    pass


def test_macosx_forestdb_enc(setup_liteserv_macosx):
    # TODO
    pass
