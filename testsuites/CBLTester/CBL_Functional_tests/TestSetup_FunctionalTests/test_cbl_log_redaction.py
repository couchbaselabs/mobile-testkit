import os
import subprocess
import pytest

from keywords.MobileRestClient import MobileRestClient
from CBLClient.Replication import Replication
from CBLClient.Authenticator import Authenticator
from libraries.provision.ansible_runner import AnsibleRunner

from libraries.testkit import cluster
from keywords.utils import log_info


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("password", [
    "auto-password",
    "auto password",
    "validpassword",
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
    log_filename = params_from_base_test_setup["log_filename"]
    log_file = params_from_base_test_setup["test_db_log_file"]
    liteserv_platform = params_from_base_test_setup["liteserv_platform"]
    testserver = params_from_base_test_setup["testserver"]

    num_cbl_docs = 500
    # Cannot run on iOS as there is no support in xcode to grab cbl logs
    if sync_gateway_version < "2.0.0" and log_file is not None:
        pytest.skip('This test cannot run with sg version below 2.0 and File logging not enabled.')

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

    verify_password_masked(liteserv_platform, log_file, password, testserver, log_filename)


@pytest.mark.sanity
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
    testserver = params_from_base_test_setup["testserver"]
    log_filename = params_from_base_test_setup["log_filename"]

    num_cbl_docs = 50
    # Cannot run on iOS as there is no support in xcode to grab cbl logs
    if sync_gateway_version < "2.0.0" and log_file is not None:
        pytest.skip('This test cannot run with sg version below 2.0 and File logging not enabled.')

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
    verify_password_masked(liteserv_platform, log_file, invalid_password, testserver, log_filename)


def verify_password_masked(liteserv_platform, log_file, password, testserver, log_filename):
    """
    @note: Porting logs for Android, xamarin-android, net-core and net-uwp platform, as the logs reside
           outside runner's file directory
    """
    log_full_path = "/tmp/cbl-logs/"
    os.mkdir(log_full_path)
    if liteserv_platform.lower() == "android" or liteserv_platform.lower() == "xamarin-android":
        log_info("Running Command: 'adb pull {} {}".format(log_file, log_full_path))
        cmd = ["adb", "pull", log_file, log_full_path]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate()
        log_info(out, err)
        log_file = os.path.join(log_full_path, os.path.basename(log_file))
    elif liteserv_platform.lower() == "net-msft" or liteserv_platform.lower() == "net-uwp":
        config_location = "resources/liteserv_configs/net-msft"
        ansible_runner = AnsibleRunner(config=config_location)
        log_file = log_file.replace('\\', '\\\\')
        if liteserv_platform.lower() == "net-uwp":
            testserver.stop()
        status = ansible_runner.run_ansible_playbook(
            "fetch-windows-cbl-logs.yml",
            extra_vars={
                "log_full_path": log_full_path,
                "log_file": log_file
            }
        )
        if status != 0:
            raise Exception("Could not fetch cbl logs from windows ")
        # Restarting Test app
        testserver.start(log_filename)

        log_info("Checking {} for copied log files - {}".format(log_full_path, os.listdir(log_full_path)))
        log_file = subprocess.check_output("ls -t {} | head -1".format(log_full_path), shell=True)
    else:
        log_full_path = log_file
    assert len(os.listdir(log_full_path)) != 0, "Log files are not copied to {}".format(log_full_path)
    command = "grep '{}' {}/*.cbllog | wc -l".format(password, log_file)
    log_info("Running command: {}".format(command))
    output = subprocess.check_output(command, shell=True)
    output = int(output.strip())
    assert output == 0, "password showed up in clear text in logs"


def delete_tmp_logs():
    del_output = subprocess.check_output("rm -rf /tmp/cbl-logs", shell=True)
    log_info("delete output is ", del_output)
