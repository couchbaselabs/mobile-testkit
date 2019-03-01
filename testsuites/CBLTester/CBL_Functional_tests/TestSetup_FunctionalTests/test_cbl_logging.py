import pytest
from time import sleep

from CBLClient.FileLogging import FileLogging
from keywords.MobileRestClient import MobileRestClient
from CBLClient.Replication import Replication
from keywords.utils import log_info
from libraries.testkit import cluster
from CBLClient.Authenticator import Authenticator

log_level_dict = {
    "debug": 0,
    "verbose": 1,
    "info": 2,
    "warning": 3,
    "error": 4,
}


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.database
@pytest.mark.parametrize("log_level, plain_text, max_size, max_rotate_count", [
#     ("debug", False, 0, 0),
#     ("verbose", False, 0, 0),
#     ("info", False, 0, 0),
#     ("warning", False, 0, 0),
#     ("error", False, 0, 0),
#     ("debug", True, 3 * 512 * 1000, 3),
    ("verbose", True, 4 * 512 * 1000, 4),
#     ("info", True, 5 * 512 * 1000, 5),
#     ("warning", True, 6 * 512 * 1000, 6),
#     ("error", True, 7 * 512 * 1000, 7),
])
def test_file_logging(params_from_base_test_setup, log_level, plain_text, max_size, max_rotate_count):
    base_url = params_from_base_test_setup["base_url"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]
    channels = ["ABC"]
    log_obj = FileLogging(base_url)
    sg_db = "db"
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]

    log_directory = log_obj.configure(log_level=log_level, plain_text=plain_text, max_rotate_count=max_rotate_count, max_size=max_size)
    log_info("logs are enabled at: {}".format(log_directory))
    if liteserv_version < "2.5.0":
        pytest.skip('This test cannnot run with CBL version below 2.5.0')

    cbl_log_level = log_obj.get_log_level()
    cbl_plain_text = log_obj.get_plain_text_status()
    cbl_max_size = log_obj.get_max_size()
    cbl_max_rotate_count = log_obj.get_max_rotate_count()
    log_info("log_level {}, max_size {}, max_rotate_count {}, plain_text_status {}".format(cbl_log_level, cbl_max_size,
                                                                                           cbl_max_rotate_count,
                                                                                           cbl_plain_text))

    if max_size == 0:
        max_size = 512000

    if max_rotate_count == 0:
        max_rotate_count = 1

    assert log_level_dict[log_level] == cbl_log_level, "Actual log levels is not matching with the set log level"
    assert plain_text == cbl_plain_text, "Actual plain text status is not matching with set plain text status"
    assert max_size == cbl_max_size, "Actual max_size is not matching with set max_size"
    assert max_rotate_count == cbl_max_rotate_count, "Actual max_rotate_count is not matching with set max_rotate_count"

    # filling logfile for rotation to kick in
    sg_client = MobileRestClient()

    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    username = "autotest"
    password = "password"
    number_of_updates = 20

    db.create_bulk_docs(number=100, id_prefix="cbl_docs", db=cbl_db, channels=channels)

    sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels)
    cookie, session = sg_client.create_session(url=sg_admin_url, db=sg_db, name=username)
    authenticator = Authenticator(base_url)
    replicator_authenticator = authenticator.authentication(session, cookie, authentication_type="session")

    replicator = Replication(base_url)
    repl = replicator.configure_and_replicate(source_db=cbl_db, target_url=sg_blip_url, continuous=True,
                                              replicator_authenticator=replicator_authenticator)
    doc_ids = db.getDocIds(database=cbl_db)
    for _ in range(10):
        db.update_bulk_docs(database=cbl_db, number_of_updates=number_of_updates, doc_ids=doc_ids)
        replicator.wait_until_replicator_idle(repl)
    replicator.stop(repl)