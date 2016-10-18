import os

import pytest
import shutil

from keywords.constants import TEST_DIR
from keywords.constants import BINARY_DIR
from keywords.LiteServFactory import LiteServFactory
from keywords.MobileRestClient import MobileRestClient
from keywords.utils import log_info
from utilities.AndroidUtils import AndroidUtils


@pytest.fixture(scope="function")
def setup_liteserv_android_sqlite(request):

    android_host = request.config.getoption("--android-host")

    liteserv = LiteServFactory.create("android",
                                      version_build="1.3.1-30",
                                      host=android_host,
                                      port=59840,
                                      storage_engine="SQLite")
    liteserv.download()
    liteserv.install()

    yield liteserv


@pytest.fixture(scope="function")
def setup_liteserv_android_sqlcipher(request):

    android_host = request.config.getoption("--android-host")

    liteserv = LiteServFactory.create("android",
                                      version_build="1.3.1-30",
                                      host=android_host,
                                      port=59840,
                                      storage_engine="SQLCipher")
    liteserv.download()
    liteserv.install()

    yield liteserv


@pytest.fixture(scope="function")
def setup_liteserv_android_forestdb(request):

    android_host = request.config.getoption("--android-host")

    liteserv = LiteServFactory.create("android",
                                      version_build="1.3.1-30",
                                      host=android_host,
                                      port=59840,
                                      storage_engine="ForestDB")

    liteserv.download()
    liteserv.install()

    yield liteserv


@pytest.fixture(scope="function")
def setup_liteserv_android_forestdb_encryption(request):

    android_host = request.config.getoption("--android-host")

    liteserv = LiteServFactory.create("android",
                                      version_build="1.3.1-30",
                                      host=android_host,
                                      port=59840,
                                      storage_engine="ForestDB+Encryption")
    liteserv.download()
    liteserv.install()

    yield liteserv


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
    liteserv = setup_liteserv_android_sqlite
    logfile = open("{}/test.txt".format(TEST_DIR), "w")
    ls_url = liteserv.start(logfile)

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    liteserv.stop(logfile)

    # Look in adb logcat to see if output match platform / storage engine expectation
    # We can't look at the database files directly to my knowledge without a rooted device
    liteserv_output = []
    with open("{}/test.txt".format(TEST_DIR), "r") as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith("I/LiteServ"):
                line = line.strip()
                liteserv_output.append(line)

    assert len(liteserv_output) == 2
    assert liteserv_output[0].endswith("storageType=SQLite")
    assert liteserv_output[1].endswith("dbpassword=")


def test_android_sqlcipher(setup_liteserv_android_sqlcipher):
    liteserv = setup_liteserv_android_sqlcipher
    logfile = open("{}/test.txt".format(TEST_DIR), "w")
    ls_url = liteserv.start(logfile)

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    liteserv.stop(logfile)

    # Look in adb logcat to see if output match platform / storage engine expectation
    # We can't look at the database files directly to my knowledge without a rooted device
    liteserv_output = []
    with open("{}/test.txt".format(TEST_DIR), "r") as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith("I/LiteServ"):
                line = line.strip()
                liteserv_output.append(line)

    assert len(liteserv_output) == 2
    assert liteserv_output[0].endswith("storageType=SQLite")
    assert liteserv_output[1].endswith("dbpassword=ls_db:pass,ls_db1:pass,ls_db2:pass")


def test_android_forestdb(setup_liteserv_android_forestdb):
    liteserv = setup_liteserv_android_forestdb
    logfile = open("{}/test.txt".format(TEST_DIR), "w")
    ls_url = liteserv.start(logfile)

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    liteserv.stop(logfile)

    # Look in adb logcat to see if output match platform / storage engine expectation
    # We can't look at the database files directly to my knowledge without a rooted device
    liteserv_output = []
    with open("{}/test.txt".format(TEST_DIR), "r") as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith("I/LiteServ"):
                line = line.strip()
                liteserv_output.append(line)

    assert len(liteserv_output) == 2
    assert liteserv_output[0].endswith("storageType=ForestDB")
    assert liteserv_output[1].endswith("dbpassword=")


def test_android_forestdb_enc(setup_liteserv_android_forestdb_encryption):
    liteserv = setup_liteserv_android_forestdb_encryption
    logfile = open("{}/test.txt".format(TEST_DIR), "w")
    ls_url = liteserv.start(logfile)

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    liteserv.stop(logfile)

    # Look in adb logcat to see if output match platform / storage engine expectation
    # We can't look at the database files directly to my knowledge without a rooted device
    liteserv_output = []
    with open("{}/test.txt".format(TEST_DIR), "r") as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith("I/LiteServ"):
                line = line.strip()
                liteserv_output.append(line)

    assert len(liteserv_output) == 2
    assert liteserv_output[0].endswith("storageType=ForestDB")
    assert liteserv_output[1].endswith("dbpassword=ls_db:pass,ls_db1:pass,ls_db2:pass")

