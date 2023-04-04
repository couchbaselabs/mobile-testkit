import time
import pytest
import datetime
import zipfile
import os
import io

from keywords.utils import log_info
from keywords.utils import clear_resources_pngs
from keywords.MobileRestClient import MobileRestClient
from keywords.TestServerFactory import TestServerFactory
from keywords.constants import RESULTS_DIR

from CBLClient.FileLogging import FileLogging
from CBLClient.Replication import Replication
from CBLClient.Collection import Collection
from CBLClient.Scope import Scope
from CBLClient.BasicAuthenticator import BasicAuthenticator
from CBLClient.Database import Database
from CBLClient.Document import Document
from CBLClient.Array import Array
from CBLClient.Dictionary import Dictionary
from CBLClient.DataTypeInitiator import DataTypeInitiator
from CBLClient.SessionAuthenticator import SessionAuthenticator
from CBLClient.Utils import Utils
from CBLClient.ReplicatorConfiguration import ReplicatorConfiguration


def pytest_addoption(parser):

    parser.addoption("--use-local-testserver",
                     action="store_true",
                     help="Skip download and launch TestServer, use local debug build",
                     default=False)
    
    parser.addoption("--appService-url",
                     action="store",
                     help="liteserv-platform: the platform to assign to the liteserv")

    parser.addoption("--liteserv-platform",
                     action="store",
                     help="liteserv-platform: the platform to assign to the liteserv")

    parser.addoption("--liteserv-version",
                     action="store",
                     help="liteserv-version: the version to download / install for the liteserv")

    parser.addoption("--liteserv-host",
                     action="store",
                     help="liteserv-host: the host to start liteserv on")

    parser.addoption("--liteserv-port",
                     action="store",
                     help="liteserv-port: the port to assign to liteserv")

    parser.addoption("--create-db-per-test",
                     action="store",
                     help="create-db-per-test: Creates/deletes client DB for every test")

    parser.addoption("--create-db-per-suite",
                     action="store",
                     help="create-db-per-suite: Creates/deletes client DB per suite")

    parser.addoption("--device", action="store_true",
                     help="Enable device if you want to run it on device", default=False)

    parser.addoption("--cbl-ce", action="store_true",
                     help="If set, community edition will get picked up , default is enterprise", default=False)

    parser.addoption("--flush-memory-per-test",
                     action="store_true",
                     help="If set, will flush server memory per test")

    parser.addoption("--debug-mode", action="store_true",
                     help="Enable debug mode for the app ", default=False)


    parser.addoption("--enable-file-logging",
                     action="store_true",
                     help="If set, CBL file logging would enable. Supported only cbl2.5 onwards")

    parser.addoption("--cbl-log-decoder-platform",
                     action="store",
                     help="cbl-log-decoder-platform: the platform to assign to the cbl-log-decoder platform")

    parser.addoption("--cbl-log-decoder-build",
                     action="store",
                     help="cbl-log-decoder-build: the platform to assign to the cbl-log-decoder build")

    parser.addoption("--hide-product-version",
                     action="store_true",
                     help="Hides SGW product version when you hit SGW url",
                     default=False)

    parser.addoption("--liteserv-android-serial-number",
                     action="store",
                     help="liteserv-android-serial-number: the serial number of the android device to be used")

# This will get called once before the first test that
# runs with this as input parameters in this file
# This setup will be called once for all tests in the
# testsuites/CBLTester/CBL_Functional_tests/ directory
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
@pytest.fixture(scope="session")
def params_from_base_suite_setup(request):
    liteserv_platform = request.config.getoption("--liteserv-platform")
    liteserv_version = request.config.getoption("--liteserv-version")
    liteserv_host = request.config.getoption("--liteserv-host")
    liteserv_port = request.config.getoption("--liteserv-port")

    use_local_testserver = request.config.getoption("--use-local-testserver")
    create_db_per_test = request.config.getoption("--create-db-per-test")
    create_db_per_suite = request.config.getoption("--create-db-per-suite")
    device_enabled = request.config.getoption("--device")
    cbl_ce = request.config.getoption("--cbl-ce")
    flush_memory_per_test = request.config.getoption("--flush-memory-per-test")
    debug_mode = request.config.getoption("--debug-mode")
    delta_sync_enabled = request.config.getoption("--delta-sync")
    enable_file_logging = request.config.getoption("--enable-file-logging")
    cbl_log_decoder_platform = request.config.getoption("--cbl-log-decoder-platform")
    cbl_log_decoder_build = request.config.getoption("--cbl-log-decoder-build")
    hide_product_version = request.config.getoption("--hide-product-version")
    liteserv_android_serial_number = request.config.getoption("--liteserv-android-serial-number")

    test_name = request.node.name

    testserver = TestServerFactory.create(platform=liteserv_platform,
                                          version_build=liteserv_version,
                                          host=liteserv_host,
                                          port=liteserv_port,
                                          community_enabled=cbl_ce,
                                          debug_mode=debug_mode)

    if not use_local_testserver:
        log_info("Downloading TestServer ...")
        # Download TestServer app
        testserver.download()

        # Install TestServer app
        if device_enabled:
            if "android" in liteserv_platform and liteserv_android_serial_number:
                testserver.serial_number = liteserv_android_serial_number
            testserver.install_device()
        else:
            testserver.install()

    base_url = "http://{}:{}".format(liteserv_host, liteserv_port)
    suite_cbl_db = None

    # Start Test server which needed for suite level set up like query tests
    if not use_local_testserver and create_db_per_suite:
        log_info("Starting TestServer...")
        testserver.stop()
        test_name_cp = test_name.replace("/", "-")
        log_filename = "{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(testserver).__name__, test_name_cp, datetime.datetime.now())
        if device_enabled:
            testserver.start_device(log_filename)
        else:
            testserver.start(log_filename)
        time.sleep(2)

    suite_source_db = None
    suite_db = None
    suite_db_log_files = None
    suite_cbllog = FileLogging(base_url)
    if create_db_per_suite:
        if enable_file_logging and liteserv_version >= "2.5.0":
            suite_cbllog.configure(log_level="verbose", max_rotate_count=2,
                                   max_size=1000000 * 512, plain_text=True)
            suite_db_log_files = suite_cbllog.get_directory()
            log_info("Log files available at - {}".format(suite_db_log_files))
        # Create CBL database
        suite_cbl_db = create_db_per_suite
        suite_db = Database(base_url)

        log_info("Creating a Database {} at the suite setup".format(suite_cbl_db))
        db_config = suite_db.configure()
        suite_source_db = suite_db.create(suite_cbl_db, db_config)
        log_info("Getting the database name")
        db_name = suite_db.getName(suite_source_db)
        assert db_name == suite_cbl_db

    yield {
        "liteserv_platform": liteserv_platform,
        "liteserv_version": liteserv_version,
        "liteserv_host": liteserv_host,
        "liteserv_port": liteserv_port,
        "create_db_per_test": create_db_per_test,
        "suite_source_db": suite_source_db,
        "suite_cbl_db": suite_cbl_db,
        "suite_db": suite_db,
        "testserver": testserver,
        "device_enabled": device_enabled,
        "flush_memory_per_test": flush_memory_per_test,
        "delta_sync_enabled": delta_sync_enabled,
        "enable_file_logging": enable_file_logging,
        "cbl_log_decoder_platform": cbl_log_decoder_platform,
        "cbl_log_decoder_build": cbl_log_decoder_build,
        "suite_db_log_files": suite_db_log_files,
        "cbl_ce": cbl_ce,
    }

    if request.node.testsfailed != 0 and enable_file_logging and create_db_per_suite is not None:
        tests_list = request.node.items
        failed_test_list = []
        for test in tests_list:
            if test.rep_call.failed:
                failed_test_list.append(test.rep_call.nodeid)
        zip_data = suite_cbllog.get_logs_in_zip()
        suite_log_zip_file = "Suite_test_log.zip"

        if os.path.exists(suite_log_zip_file):
            log_info("Log file for failed Suite tests is: {}".format(suite_log_zip_file))
            target_zip = zipfile.ZipFile(suite_log_zip_file, 'w')
            with zipfile.ZipFile(io.BytesIO(zip_data)) as thezip:
                for zipinfo in thezip.infolist():
                    target_zip.writestr(zipinfo.filename, thezip.read(zipinfo.filename))
            target_zip.close()
        else:
            log_info("Cannot find log file for failed Suite tests")

    if create_db_per_suite:
        # Delete CBL database
        log_info("Deleting the database {} at the suite teardown".format(create_db_per_suite))
        time.sleep(2)
        suite_db.deleteDB(suite_source_db)
        time.sleep(1)
    if create_db_per_suite:
        # Flush all the memory contents on the server app
        log_info("Flushing server memory")
        utils_obj = Utils(base_url)
        utils_obj.flushMemory()
        if not use_local_testserver:
            log_info("Stopping the test server per suite")
            testserver.stop()
    # Delete png files under resources/data
    clear_resources_pngs()


@pytest.fixture(scope="function")
def params_from_base_test_setup(request, params_from_base_suite_setup):
    liteserv_host = params_from_base_suite_setup["liteserv_host"]
    liteserv_port = params_from_base_suite_setup["liteserv_port"]
    create_db_per_test = params_from_base_suite_setup["create_db_per_test"]
    no_conflicts_enabled = params_from_base_suite_setup["no_conflicts_enabled"]
    target_admin_url = params_from_base_suite_setup["target_admin_url"]
    suite_source_db = params_from_base_suite_setup["suite_source_db"]
    suite_cbl_db = params_from_base_suite_setup["suite_cbl_db"]
    test_name = request.node.name
    target_url = params_from_base_suite_setup["target_url"]
    base_url = params_from_base_suite_setup["base_url"]
    sync_gateway_version = params_from_base_suite_setup["sync_gateway_version"]
    sg_config = params_from_base_suite_setup["sg_config"]
    liteserv_platform = params_from_base_suite_setup["liteserv_platform"]
    testserver = params_from_base_suite_setup["testserver"]
    device_enabled = params_from_base_suite_setup["device_enabled"]
    liteserv_version = params_from_base_suite_setup["liteserv_version"]
    delta_sync_enabled = params_from_base_suite_setup["delta_sync_enabled"]
    enable_file_logging = params_from_base_suite_setup["enable_file_logging"]
    cbl_log_decoder_platform = params_from_base_suite_setup["cbl_log_decoder_platform"]
    cbl_log_decoder_build = params_from_base_suite_setup["cbl_log_decoder_build"]
    use_local_testserver = request.config.getoption("--use-local-testserver")
    cbl_ce = params_from_base_suite_setup["cbl_ce"]

    source_db = None
    test_name_cp = test_name.replace("/", "-")
    log_filename = "{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(testserver).__name__,
                                                 test_name_cp,
                                                 datetime.datetime.now())

    if not use_local_testserver and create_db_per_test:
        log_info("Starting TestServer...")
        testserver.stop()
        if device_enabled:
            testserver.start_device(log_filename)
        else:
            testserver.start(log_filename)
        time.sleep(2)

    db_config = None

    db = None
    cbl_db = None
    test_db_log_file = None
    path = None
    test_cbllog = FileLogging(base_url)
    if create_db_per_test:
        if enable_file_logging and liteserv_version >= "2.5.0":
            test_cbllog.configure(log_level="verbose", max_rotate_count=2,
                                  max_size=100000 * 512, plain_text=True)
            test_db_log_file = test_cbllog.get_directory()
            log_info("Log files available at - {}".format(test_db_log_file))
        cbl_db = create_db_per_test + str(time.time())
        # Create CBL database
        db = Database(base_url)

        log_info("Creating a Database {} at test setup".format(cbl_db))
        db_config = db.configure()
        source_db = db.create(cbl_db, db_config)
        log_info("Getting the database name")
        db_name = db.getName(source_db)
        assert db_name == cbl_db
        path = db.getPath(source_db).rstrip("/\\")
        if '\\' in path:
            path = '\\'.join(path.split('\\')[:-1])
        else:
            path = '/'.join(path.split('/')[:-1])

    # This dictionary is passed to each test
    yield {
        "liteserv_host": liteserv_host,
        "liteserv_port": liteserv_port,
        "liteserv_platform": liteserv_platform,
        "target_url": target_url,
        "target_admin_url": target_admin_url,
        "no_conflicts_enabled": no_conflicts_enabled,
        "sync_gateway_version": sync_gateway_version,
        "source_db": source_db,
        "cbl_db": cbl_db,
        "suite_source_db": suite_source_db,
        "suite_cbl_db": suite_cbl_db,
        "base_url": base_url,
        "sg_config": sg_config,
        "db": db,
        "device_enabled": device_enabled,
        "testserver": testserver,
        "db_config": db_config,
        "log_filename": log_filename,
        "test_db_log_file": test_db_log_file,
        "liteserv_version": liteserv_version,
        "delta_sync_enabled": delta_sync_enabled,
        "cbl_log_decoder_platform": cbl_log_decoder_platform,
        "cbl_log_decoder_build": cbl_log_decoder_build,
        "enable_file_logging": enable_file_logging,
        "test_cbllog": test_cbllog,
        "cbl_ce": cbl_ce,
    }

    if request.node.rep_call.failed and enable_file_logging and create_db_per_test is not None:
        test_id = request.node.nodeid
        log_info("\n Collecting logs for failed test: {}".format(test_id))
        zip_data = test_cbllog.get_logs_in_zip()
        log_directory = "results/logs"
        if not os.path.exists(log_directory):
            os.mkdir(log_directory)
        test_log_zip_file = "{}.zip".format(test_id.split("::")[-1])
        test_log = os.path.join(log_directory, test_log_zip_file)
        if not os.path.exists(test_log):
            target_zip = zipfile.ZipFile(test_log, 'w')
            with zipfile.ZipFile(io.BytesIO(zip_data)) as thezip:
                for zipinfo in thezip.infolist():
                    target_zip.writestr(zipinfo.filename, thezip.read(zipinfo.filename))
            target_zip.close()

    log_info("Tearing down test")
    if create_db_per_test:
        # Delete CBL database
        log_info("Deleting the database {} at test teardown".format(create_db_per_test))
        time.sleep(1)
        try:
            if db.exists(cbl_db, path):
                db.deleteDB(source_db)
                log_info("not deleting")
            log_info("Flushing server memory")
            utils_obj = Utils(base_url)
            utils_obj.flushMemory()
            if not use_local_testserver:
                log_info("Stopping the test server per test")
                testserver.stop()
        except Exception as err:
            log_info("Exception occurred: {}".format(err))


@pytest.fixture(scope="class")
def class_init(request, params_from_base_suite_setup):
    base_url = params_from_base_suite_setup["base_url"]
    liteserv_platform = params_from_base_suite_setup["liteserv_platform"]
    liteserv_version = params_from_base_suite_setup["liteserv_version"]
    disable_encryption = params_from_base_suite_setup["disable_encryption"]
    encryption_password = params_from_base_suite_setup["encryption_password"]
    db_obj = Database(base_url)
    scope_obj = Scope(base_url)
    collection_obj = Collection(base_url)
    doc_obj = Document(base_url)
    datatype = DataTypeInitiator(base_url)
    repl_obj = Replication(base_url)
    array_obj = Array(base_url)
    dict_obj = Dictionary(base_url)
    repl_config_obj = ReplicatorConfiguration(base_url)
    scope_obj = Scope(base_url)
    collection_obj = Collection(base_url)
    base_auth_obj = BasicAuthenticator(base_url)
    session_auth_obj = SessionAuthenticator(base_url)
    sg_client = MobileRestClient()

    if disable_encryption:
        db_config = db_obj.configure()
    else:
        db_config = db_obj.configure(password=encryption_password)
    db = db_obj.create("cbl-init-db", db_config)

    request.cls.db_obj = db_obj
    request.cls.collection_obj = collection_obj
    request.cls.doc_obj = doc_obj
    request.cls.scope_obj = scope_obj
    request.cls.dict_obj = dict_obj
    request.cls.datatype = datatype
    request.cls.collection_obj = collection_obj
    request.cls.scope_obj = scope_obj
    request.cls.repl_obj = repl_obj
    request.cls.repl_config_obj = repl_config_obj
    request.cls.array_obj = array_obj
    request.cls.dict_obj = dict_obj
    request.cls.array_obj = array_obj
    request.cls.datatype = datatype
    request.cls.repl_obj = repl_obj
    request.cls.base_auth_obj = base_auth_obj
    request.cls.session_auth_obj = session_auth_obj
    request.cls.sg_client = sg_client
    request.cls.db_obj = db_obj
    request.cls.db = db
    request.cls.liteserv_platform = liteserv_platform
    request.cls.liteserv_version = liteserv_version

    yield
    db_obj.deleteDB(db)


@pytest.fixture(scope="function")
def setup_customized_teardown_test(request, params_from_base_test_setup):
    cbl_db_name1 = "cbl_db1" + str(time.time())
    cbl_db_name2 = "cbl_db2" + str(time.time())
    cbl_db_name3 = "cbl_db3" + str(time.time())
    base_url = params_from_base_test_setup["base_url"]
    disable_encryption = params_from_base_test_setup["disable_encryption"]
    encryption_password = params_from_base_test_setup["encryption_password"]
    db = Database(base_url)
    if disable_encryption:
        db_config = db.configure()
    else:
        db_config = db.configure(password=encryption_password)
    cbl_db1 = db.create(cbl_db_name1, db_config)
    cbl_db2 = db.create(cbl_db_name2, db_config)
    cbl_db3 = db.create(cbl_db_name3, db_config)
    log_info("setting up all 3 dbs")

    yield{
        "db": db,
        "cbl_db_name1": cbl_db_name1,
        "cbl_db_name2": cbl_db_name2,
        "cbl_db_name3": cbl_db_name3,
        "cbl_db1": cbl_db1,
        "cbl_db2": cbl_db2,
        "cbl_db3": cbl_db3,
    }
    log_info("Tearing down test")
    db.deleteDB(cbl_db1)
    db.deleteDB(cbl_db2)
    db.deleteDB(cbl_db3)
