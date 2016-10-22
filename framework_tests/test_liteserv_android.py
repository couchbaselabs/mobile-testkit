import os

import pytest
import shutil
import subprocess
import datetime

from keywords.constants import RESULTS_DIR
from keywords.constants import BINARY_DIR
from keywords.LiteServFactory import LiteServFactory
from keywords.MobileRestClient import MobileRestClient


@pytest.fixture(scope="function")
def setup_liteserv_android_sqlite(request):

    android_version = request.config.getoption("--android-version")
    android_host = request.config.getoption("--android-host")

    liteserv = LiteServFactory.create("android",
                                      version_build=android_version,
                                      host=android_host,
                                      port=59840,
                                      storage_engine="SQLite")
    liteserv.download()
    liteserv.install()

    yield liteserv

    liteserv.remove()


@pytest.fixture(scope="function")
def setup_liteserv_android_sqlcipher(request):

    android_version = request.config.getoption("--android-version")
    android_host = request.config.getoption("--android-host")

    liteserv = LiteServFactory.create("android",
                                      version_build=android_version,
                                      host=android_host,
                                      port=59840,
                                      storage_engine="SQLCipher")
    liteserv.download()
    liteserv.install()

    yield liteserv

    liteserv.remove()


@pytest.fixture(scope="function")
def setup_liteserv_android_forestdb(request):

    android_version = request.config.getoption("--android-version")
    android_host = request.config.getoption("--android-host")

    liteserv = LiteServFactory.create("android",
                                      version_build=android_version,
                                      host=android_host,
                                      port=59840,
                                      storage_engine="ForestDB")

    liteserv.download()
    liteserv.install()

    yield liteserv

    liteserv.remove()


@pytest.fixture(scope="function")
def setup_liteserv_android_forestdb_encryption(request):

    android_version = request.config.getoption("--android-version")
    android_host = request.config.getoption("--android-host")

    liteserv = LiteServFactory.create("android",
                                      version_build=android_version,
                                      host=android_host,
                                      port=59840,
                                      storage_engine="ForestDB+Encryption")
    liteserv.download()
    liteserv.install()

    yield liteserv

    liteserv.remove()


def test_android_download(request):

    android_version = request.config.getoption("--android-version")
    android_host = request.config.getoption("--android-host")

    shutil.rmtree("{}/".format(BINARY_DIR))
    os.makedirs("{}".format(BINARY_DIR))

    liteserv = LiteServFactory.create("android",
                                      version_build=android_version,
                                      host=android_host,
                                      port=59840,
                                      storage_engine="SQLite")

    liteserv.download()

    assert len(os.listdir("deps/binaries")) == 1
    assert os.path.isfile("deps/binaries/couchbase-lite-android-liteserv-SQLite-{}-debug.apk".format(android_version))

    liteserv_two = LiteServFactory.create("android",
                                          version_build=android_version,
                                          host=android_host,
                                          port=59840,
                                          storage_engine="SQLCipher")

    liteserv_two.download()

    assert len(os.listdir("deps/binaries")) == 2
    assert os.path.isfile("deps/binaries/couchbase-lite-android-liteserv-SQLCipher-ForestDB-Encryption-{}-debug.apk".format(android_version))


def test_android_install_and_remove(request):

    android_version = request.config.getoption("--android-version")
    android_host = request.config.getoption("--android-host")

    liteserv = LiteServFactory.create("android",
                                      version_build=android_version,
                                      host=android_host,
                                      port=59840,
                                      storage_engine="SQLite")

    liteserv.download()
    liteserv.install()

    output = subprocess.check_output(["adb", "shell", "pm", "list", "packages"])
    assert "com.couchbase.liteservandroid" in output

    liteserv.remove()

    output = subprocess.check_output(["adb", "shell", "pm", "list", "packages"])
    assert "com.couchbase.liteservandroid" not in output


def test_android_full_life_cycle(request, setup_liteserv_android_sqlite):
    liteserv = setup_liteserv_android_sqlite

    test_name = request.node.name

    logfile = "{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now())
    ls_url = liteserv.start(logfile)

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")
    docs = client.add_docs(ls_url, db="ls_db", number=10, id_prefix="test_doc")
    assert len(docs) == 10

    client.delete_databases(ls_url)

    liteserv.stop()


def test_android_sqlite(request, setup_liteserv_android_sqlite):
    liteserv = setup_liteserv_android_sqlite

    test_name = request.node.name

    logfile = "{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now())
    ls_url = liteserv.start(logfile)

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    liteserv.stop()

    # Look in adb logcat to see if output match platform / storage engine expectation
    # We can't look at the database files directly to my knowledge without a rooted device
    liteserv_output = []
    with open(logfile, "r") as f:
        lines = f.readlines()
        for line in lines:
            if "LiteServ" in line:
                line = line.strip()
                liteserv_output.append(line)

    assert len(liteserv_output) == 4
    assert liteserv_output[0].endswith("storageType=SQLite")
    assert liteserv_output[1].endswith("dbpassword=")


def test_android_sqlcipher(request, setup_liteserv_android_sqlcipher):
    liteserv = setup_liteserv_android_sqlcipher

    test_name = request.node.name

    logfile = "{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now())
    ls_url = liteserv.start(logfile)

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    liteserv.stop()

    # Look in adb logcat to see if output match platform / storage engine expectation
    # We can't look at the database files directly to my knowledge without a rooted device
    liteserv_output = []
    with open(logfile, "r") as f:
        lines = f.readlines()
        for line in lines:
            if "LiteServ" in line:
                line = line.strip()
                liteserv_output.append(line)

    assert len(liteserv_output) == 4
    assert liteserv_output[0].endswith("storageType=SQLite")
    assert liteserv_output[1].endswith("dbpassword=ls_db:pass,ls_db1:pass,ls_db2:pass")


def test_android_forestdb(request, setup_liteserv_android_forestdb):
    liteserv = setup_liteserv_android_forestdb

    test_name = request.node.name

    logfile = "{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now())
    ls_url = liteserv.start(logfile)

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    liteserv.stop()

    # Look in adb logcat to see if output match platform / storage engine expectation
    # We can't look at the database files directly to my knowledge without a rooted device
    liteserv_output = []
    with open(logfile, "r") as f:
        lines = f.readlines()
        for line in lines:
            if "LiteServ" in line:
                line = line.strip()
                liteserv_output.append(line)

    assert len(liteserv_output) == 4
    assert liteserv_output[0].endswith("storageType=ForestDB")
    assert liteserv_output[1].endswith("dbpassword=")


def test_android_forestdb_enc(request, setup_liteserv_android_forestdb_encryption):
    liteserv = setup_liteserv_android_forestdb_encryption

    test_name = request.node.name

    logfile = "{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now())
    ls_url = liteserv.start(logfile)

    client = MobileRestClient()
    client.create_database(ls_url, "ls_db")

    liteserv.stop()

    # Look in adb logcat to see if output match platform / storage engine expectation
    # We can't look at the database files directly to my knowledge without a rooted device
    liteserv_output = []
    with open(logfile, "r") as f:
        lines = f.readlines()
        for line in lines:
            if "LiteServ" in line:
                line = line.strip()
                liteserv_output.append(line)

    assert len(liteserv_output) == 4
    assert liteserv_output[0].endswith("storageType=ForestDB")
    assert liteserv_output[1].endswith("dbpassword=ls_db:pass,ls_db1:pass,ls_db2:pass")
