import os
import subprocess
import pytest
import zipfile

from keywords.MobileRestClient import MobileRestClient
from CBLClient.Replication import Replication
from CBLClient.Authenticator import Authenticator

from libraries.testkit import cluster
from keywords.utils import log_info


@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("password", [
    pytest.param("auto-password", marks=pytest.mark.sanity),
    ("auto password"),
    pytest.param("validpassword", marks=pytest.mark.ce_sanity),
])
def test_mask_password_in_logs(params_from_base_test_setup, password):
    """
        @summary:
        1. Create CBL DB and create bulk doc in CBL
        2. Configure replication to Sg with basic authentication
        3. Replicate docs to SG
        4. Verify password is masked in cbl logs
    """
    sg_db = "db"

    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    log_file = params_from_base_test_setup["test_db_log_file"]
    liteserv_platform = params_from_base_test_setup["liteserv_platform"]
    enable_file_logging = params_from_base_test_setup["enable_file_logging"]
    test_cbllog = params_from_base_test_setup["test_cbllog"]

    num_cbl_docs = 500
    if sync_gateway_version < "2.0.0" and not enable_file_logging:
        pytest.skip('This test cannot run with sg version below 2.0 or File logging is not enabled.')

    channels = ["ABC"]
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)
    # Clean up tmp logs before test runs
    delete_tmp_logs()
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)

    sg_client = MobileRestClient()
    db.create_bulk_docs(number=num_cbl_docs, id_prefix="cblid", db=cbl_db, channels=channels)

    # Add docs in SG
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password=password, channels=channels)
    sg_client.create_session(sg_admin_url, sg_db, "autotest")

    replicator_authenticator = authenticator.authentication(username="autotest", password=password,
                                                            authentication_type="basic")
    repl_config = replicator.configure(cbl_db, target_url=sg_blip_url, continuous=False,
                                       channels=channels, replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)

    verify_password_masked(liteserv_platform, log_file, password, test_cbllog)


@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("invalid_password", [
    "auto-password",
    "auto password",
    "invalidpassword",
])
def test_verify_invalid_mask_password_in_logs(params_from_base_test_setup, invalid_password):
    """
        @summary:
        1. Create CBL DB and create bulk doc in CBL
        2. Configure replication to Sg with basic authentication
        3. Authenticate in CBL with invalid password
        4. Verify invalid password is masked in cbl logs
    """
    sg_db = "db"

    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    base_url = params_from_base_test_setup["base_url"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_config = params_from_base_test_setup["sg_config"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    log_file = params_from_base_test_setup["test_db_log_file"]
    liteserv_platform = params_from_base_test_setup["liteserv_platform"]
    enable_file_logging = params_from_base_test_setup["enable_file_logging"]
    test_cbllog = params_from_base_test_setup["test_cbllog"]

    num_cbl_docs = 50
    if sync_gateway_version < "2.0.0" and not enable_file_logging:
        pytest.skip('This test cannot run with sg version below 2.0 or File logging is not enabled.')

    channels = ["ABC"]
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    delete_tmp_logs()  # Clean up tmp logs before test runs
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)

    sg_client = MobileRestClient()
    db.create_bulk_docs(number=num_cbl_docs, id_prefix="cblid", db=cbl_db, channels=channels)

    # Add docs in SG
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    sg_client.create_session(sg_admin_url, sg_db, "autotest")

    replicator_authenticator = authenticator.authentication(username="autotest", password=invalid_password,
                                                            authentication_type="basic")
    repl_config = replicator.configure(cbl_db, target_url=sg_blip_url, continuous=False,
                                       channels=channels, replicator_authenticator=replicator_authenticator)

    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl, err_check=False)
    verify_password_masked(liteserv_platform, log_file, invalid_password, test_cbllog)


def verify_password_masked(liteserv_platform, log_file, password, test_cbllog):
    """
       @note: Porting logs for Android, xamarin-android, net-core and net-uwp platform, as the logs reside
           outside runner's file directory
    """
    delimiter = "/"
    if liteserv_platform == "net-msft" or liteserv_platform == "uwp":
        delimiter = "\\"
    log_dir = log_file.split(delimiter)[-1]
    log_full_path_dir = "/tmp/cbl-logs/"
    os.mkdir(log_full_path_dir)
    log_info("\n Collecting logs")
    zip_data = test_cbllog.get_logs_in_zip()
    if zip_data == -1:
        raise Exception("Failed to get zip log files from CBL app")
    test_log_zip_file = "cbl_log.zip"
    test_log = os.path.join(log_full_path_dir, test_log_zip_file)
    log_info("Log file for failed test is: {}".format(test_log_zip_file))
    with open(test_log, 'w+', encoding="utf-8") as fh:
        # encoded data is coming as a string,
        fh.write(zip_data)
        fh.close()

    # unzipping the zipped log files
    log_dir_path = os.path.join(log_full_path_dir, log_dir)
    if zipfile.is_zipfile(test_log):
        with zipfile.ZipFile(test_log, 'r') as zip_ref:
            zip_ref.extractall(log_full_path_dir)
    else:
        log_dir_path = log_full_path_dir

    log_info("Checking {} for copied log files - {}".format(log_dir_path, os.listdir(log_dir_path)))
    log_file = subprocess.check_output("ls -t {} | head -1".format(log_dir_path), shell=True)
    assert len(os.listdir(log_dir_path)) != 0, "Log files are not available at {}".format(log_dir_path)
    command = "grep '{}' {}/*.cbllog | wc -l".format(password, log_dir_path)
    log_info("Running command: {}".format(command))
    output = subprocess.check_output(command, shell=True)
    output = int(output.strip())
    assert output == 0, "password showed up in clear text in logs"


def delete_tmp_logs():
    del_output = subprocess.check_output("rm -rf /tmp/cbl-logs", shell=True)
    log_info("delete output is ", del_output)
