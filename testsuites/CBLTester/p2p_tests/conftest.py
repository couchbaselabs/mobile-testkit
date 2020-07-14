import time
import datetime
import pytest

from keywords.utils import log_info, clear_resources_pngs
from keywords.TestServerFactory import TestServerFactory
from CBLClient.Database import Database
from CBLClient.Query import Query
from CBLClient.Utils import Utils
from keywords.constants import RESULTS_DIR
from CBLClient.PeerToPeer import PeerToPeer
from CBLClient.FileLogging import FileLogging


def pytest_addoption(parser):
    parser.addoption("--use-local-testserver",
                     action="store_true",
                     help="Skip installing testserver at setup",
                     default=False)

    parser.addoption("--liteserv-platforms",
                     action="store",
                     help="liteserv-platforms: the platforms to assign to the liteserv")

    parser.addoption("--liteserv-versions",
                     action="store",
                     help="liteserv-versions: the versions to download / install for the liteserv")

    parser.addoption("--liteserv-hosts",
                     action="store",
                     help="liteserv-hosts: the hosts to start liteserv on")

    parser.addoption("--liteserv-ports",
                     action="store",
                     help="liteserv-ports: the ports to assign to liteserv")

    parser.addoption("--enable-sample-bucket",
                     action="store",
                     help="enable-sample-bucket: Enable a sample server bucket")

    parser.addoption("--create-db-per-suite",
                     action="store",
                     help="create-db-per-suite: Creates/deletes client DB per suite")

    parser.addoption("--doc-generator",
                     action="store",
                     help="Provide the doc generator type. Valid values are - simple, four_k, simple_user and"
                          " complex_doc",
                     default="simple")

    parser.addoption("--no-db-delete", action="store_true",
                     help="Enable System test to start without reseting cluster", default=False)

    parser.addoption("--device", action="store_true",
                     help="Enable device if you want to run it on device", default=False)

    parser.addoption("--community", action="store_true",
                     help="If set, community edition will get picked up , default is enterprise", default=False)

    parser.addoption("--create-db-per-test",
                     action="store",
                     help="create-db-per-test: Creates/deletes client DB for every test")

    parser.addoption("--enable-file-logging",
                     action="store_true",
                     help="If set, CBL file logging would enable. Supported only cbl2.5 onwards")

    parser.addoption("--enable-encryption",
                     action="store_true",
                     help="Encryption will be enabled for CBL db",
                     default=True)

    parser.addoption("--encryption-password",
                     action="store",
                     help="Encryption will be enabled for CBL db",
                     default="password")


# This will get called once before the first test that
# runs with this as input parameters in this file
# This setup will be called once for all tests in the
# testsuites/CBLTester/CBL_Functional_tests/ directory
@pytest.fixture(scope="session")
def params_from_base_suite_setup(request):
    use_local_testserver = request.config.getoption("--use-local-testserver")

    liteserv_platforms = request.config.getoption("--liteserv-platforms")
    liteserv_versions = request.config.getoption("--liteserv-versions")
    liteserv_hosts = request.config.getoption("--liteserv-hosts")
    liteserv_ports = request.config.getoption("--liteserv-ports")

    platform_list = liteserv_platforms.split(',')
    version_list = liteserv_versions.split(',')
    host_list = liteserv_hosts.split(',')
    port_list = liteserv_ports.split(',')

    if len(platform_list) != len(version_list) != len(host_list) != len(port_list):
        raise Exception("Provide equal no. of Parameters for host, port, version and platforms")

    enable_sample_bucket = request.config.getoption("--enable-sample-bucket")
    device_enabled = request.config.getoption("--device")
    generator = request.config.getoption("--doc-generator")
    no_db_delete = request.config.getoption("--no-db-delete")
    create_db_per_test = request.config.getoption("--create-db-per-test")
    create_db_per_suite = request.config.getoption("--create-db-per-suite")
    enable_file_logging = request.config.getoption("--enable-file-logging")

    community_enabled = request.config.getoption("--community")

    enable_encryption = request.config.getoption("--enable-encryption")
    encryption_password = request.config.getoption("--encryption-password")

    test_name = request.node.name
    testserver_list = []
    for platform, version, host, port in zip(platform_list,
                                             version_list,
                                             host_list,
                                             port_list):
        testserver = TestServerFactory.create(platform=platform,
                                              version_build=version,
                                              host=host,
                                              port=port,
                                              community_enabled=community_enabled)
        if not use_local_testserver:
            log_info("Downloading TestServer ...")
            # Download TestServer app
            testserver.download()

            # Install TestServer app
            if device_enabled and (platform == "ios" or platform == "android"):
                testserver.install_device()
            else:
                testserver.install()

        testserver_list.append(testserver)
    base_url_list = []
    for host, port in zip(host_list, port_list):
        base_url_list.append("http://{}:{}".format(host, port))

    # Create CBL databases on all devices
    db_name_list = []
    cbl_db_list = []
    db_obj_list = []
    db_path_list = []
    query_obj_list = []
    if create_db_per_suite:
        # Start Test server which needed for suite level set up like query tests
        for testserver in testserver_list:
            if not use_local_testserver:
                log_info("Starting TestServer...")
                test_name_cp = test_name.replace("/", "-")
                if device_enabled:
                    testserver.start_device("{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(testserver).__name__,
                                                                          test_name_cp, datetime.datetime.now()))
                else:
                    testserver.start("{}/logs/{}-{}-{}.txt".format(RESULTS_DIR, type(testserver).__name__, test_name_cp,
                                                                   datetime.datetime.now()))
        for base_url, i in zip(base_url_list, list(range(len(base_url_list)))):
            if enable_file_logging and version_list[0] >= "2.5.0":
                cbllog = FileLogging(base_url)
                cbllog.configure(log_level="verbose", max_rotate_count=2,
                                 max_size=1000 * 512 * 4, plain_text=True)
                log_info("Log files available at - {}".format(cbllog.get_directory()))
            db_name = "{}-{}".format(create_db_per_suite, i + 1)
            log_info("db name for {} is {}".format(base_url, db_name))
            db_name_list.append(db_name)
            db = Database(base_url)
            query_obj_list.append(Query(base_url))
            db_obj_list.append(db)

            log_info("Creating a Database {} at the suite setup".format(db_name))
            if enable_encryption:
                db_config = db.configure(password=encryption_password)
            else:
                db_config = db.configure()
            cbl_db = db.create(db_name, db_config)
            cbl_db_list.append(cbl_db)
            log_info("Getting the database name")
            assert db.getName(cbl_db) == db_name
            path = db.getPath(cbl_db).rstrip("/\\")
            if '\\' in path:
                path = '\\'.join(path.split('\\')[:-1])
            else:
                path = '/'.join(path.split('/')[:-1])
            db_path_list.append(path)

    yield {
        "platform_list": platform_list,
        "version_list": version_list,
        "host_list": host_list,
        "port_list": port_list,
        "enable_sample_bucket": enable_sample_bucket,
        "cbl_db_list": cbl_db_list,
        "db_name_list": db_name_list,
        "base_url_list": base_url_list,
        "query_obj_list": query_obj_list,
        "db_obj_list": db_obj_list,
        "device_enabled": device_enabled,
        "generator": generator,
        "create_db_per_test": create_db_per_test,
        "enable_encryption": enable_encryption,
        "encryption_password": encryption_password,
        "testserver_list": testserver_list,
        "enable_file_logging": enable_file_logging
    }

    if create_db_per_suite:
        for cbl_db, db_obj, base_url, db_name, path in zip(cbl_db_list, db_obj_list, base_url_list, db_name_list, db_path_list):
            if not no_db_delete:
                log_info("Deleting the database {} at the suite teardown".format(db_obj.getName(cbl_db)))
                time.sleep(2)
                if db.exists(db_name, path):
                    db.deleteDB(cbl_db)

        # Flush all the memory contents on the server app
        for base_url, testserver in zip(base_url_list, testserver_list):
            try:
                log_info("Flushing server memory")
                utils_obj = Utils(base_url)
                utils_obj.flushMemory()
                if not use_local_testserver:
                    log_info("Stopping the test server")
                    testserver.stop()
            except Exception as err:
                log_info("Exception occurred: {}".format(err))
    clear_resources_pngs()


@pytest.fixture(scope="function")
def params_from_base_test_setup(request, params_from_base_suite_setup):
    platform_list = params_from_base_suite_setup["platform_list"]
    version_list = params_from_base_suite_setup["version_list"]
    host_list = params_from_base_suite_setup["host_list"]
    port_list = params_from_base_suite_setup["port_list"]
    enable_sample_bucket = params_from_base_suite_setup["enable_sample_bucket"]
    cbl_db_list = params_from_base_suite_setup["cbl_db_list"]
    db_name_list = params_from_base_suite_setup["db_name_list"]
    base_url_list = params_from_base_suite_setup["base_url_list"]
    query_obj_list = params_from_base_suite_setup["query_obj_list"]
    db_obj_list = params_from_base_suite_setup["db_obj_list"]
    device_enabled = params_from_base_suite_setup["device_enabled"]
    generator = params_from_base_suite_setup["generator"]
    create_db_per_test = params_from_base_suite_setup["create_db_per_test"]
    encryption_password = params_from_base_suite_setup["encryption_password"]
    enable_encryption = params_from_base_suite_setup["enable_encryption"]
    testserver_list = params_from_base_suite_setup["testserver_list"]
    enable_file_logging = params_from_base_suite_setup["enable_file_logging"]
    use_local_testserver = request.config.getoption("--use-local-testserver")
    test_name = request.node.name

    if create_db_per_test:
        db_name_list = []
        cbl_db_list = []
        db_obj_list = []
        db_path_list = []
        # Start Test server which needed for per test level
        for testserver in testserver_list:
            if not use_local_testserver:
                log_info("Starting TestServer...")
                test_name_cp = test_name.replace("/", "-")
                log_filename = "{}/logs/{}-{}-{}.txt".format(RESULTS_DIR,
                                                             type(testserver).__name__,
                                                             test_name_cp,
                                                             datetime.datetime.now())
                if device_enabled:
                    testserver.start_device(log_filename)
                else:
                    testserver.start(log_filename)

        for base_url, i in zip(base_url_list, list(range(len(base_url_list)))):
            if enable_file_logging and version_list[0] >= "2.5.0":
                cbllog = FileLogging(base_url)
                cbllog.configure(log_level="verbose", max_rotate_count=2,
                                 max_size=1000 * 512, plain_text=True)
                log_info("Log files available at - {}".format(cbllog.get_directory()))

            db_name = "{}_{}_{}".format(create_db_per_test, str(time.time()), i + 1)
            log_info("db name for {} is {}".format(base_url, db_name))
            db_name_list.append(db_name)
            db = Database(base_url)
            query_obj_list.append(Query(base_url))
            db_obj_list.append(db)

            log_info("Creating a Database {} at the test setup".format(db_name))
            if enable_encryption:
                db_config = db.configure(password=encryption_password)
            else:
                db_config = db.configure()
            cbl_db = db.create(db_name, db_config)
            cbl_db_list.append(cbl_db)
            log_info("Getting the database name")
            assert db.getName(cbl_db) == db_name
            path = db.getPath(cbl_db).rstrip("/\\")
            if '\\' in path:
                path = '\\'.join(path.split('\\')[:-1])
            else:
                path = '/'.join(path.split('/')[:-1])
            db_path_list.append(path)

    yield {
        "platform_list": platform_list,
        "version_list": version_list,
        "host_list": host_list,
        "port_list": port_list,
        "enable_sample_bucket": enable_sample_bucket,
        "cbl_db_list": cbl_db_list,
        "db_name_list": db_name_list,
        "base_url_list": base_url_list,
        "query_obj_list": query_obj_list,
        "db_obj_list": db_obj_list,
        # "testserver_list": testserver_list,
        "device_enabled": device_enabled,
        "generator": generator
    }

    if create_db_per_test:
        for testserver, cbl_db, db_obj, base_url, db_name, path in zip(testserver_list, cbl_db_list, db_obj_list, base_url_list, db_name_list, db_path_list):
            try:
                log_info("Deleting the database {} at the test teardown for base url {}".format(db_obj.getName(cbl_db),
                                                                                                base_url))
                time.sleep(2)
                if db.exists(db_name, path):
                    db.deleteDB(cbl_db)
                log_info("Flushing server memory")
                utils_obj = Utils(base_url)
                utils_obj.flushMemory()
                if not use_local_testserver:
                    log_info("Stopping the test server per test")
                    testserver.stop()
            except Exception as err:
                log_info("Exception occurred: {}".format(err))


@pytest.fixture(scope="function")
def server_setup(params_from_base_test_setup):
    base_url_list = params_from_base_test_setup["base_url_list"]
    cbl_db_list = params_from_base_test_setup["cbl_db_list"]
    base_url_server = base_url_list[0]
    cbl_db_server = cbl_db_list[0]
    peer_to_peer_listener = PeerToPeer(base_url_server)
    # Need to start and stop listener, if test fails in the middle listener will not be closed.
    message_url_tcp_listener = peer_to_peer_listener.message_listener_start(cbl_db_server)
    log_info("server starting .....")
    yield {
        "base_url_list": base_url_list,
        "base_url_server": base_url_server,
        "cbl_db_server": cbl_db_server,
        "cbl_db_list": cbl_db_list,
        "message_url_tcp_listener": message_url_tcp_listener,
        "peer_to_peer_listener": peer_to_peer_listener,
    }
    peer_to_peer_listener.server_stop(message_url_tcp_listener, "MessageEndPoint")

