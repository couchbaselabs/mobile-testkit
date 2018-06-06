import subprocess
import pytest

from keywords.MobileRestClient import MobileRestClient
from CBLClient.Replication import Replication
from CBLClient.Authenticator import Authenticator
from libraries.provision.ansible_runner import AnsibleRunner

from libraries.testkit import cluster


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("password", [
    ("auto-password"),
    ("auto password"),
    ("validpassword"),
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
    log_file = params_from_base_test_setup["log_filename"]
    liteserv_platform = params_from_base_test_setup["liteserv_platform"]

    num_cbl_docs = 5
    # Cannot run on iOS as there is no support in xcode to grab cbl logs
    if sync_gateway_version < "2.0.0" or liteserv_platform.lower() == "ios":
        pytest.skip('This test cannnot run with sg version below 2.0 and if platform is iOS')

    channels = ["ABC"]
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)
    # Clean up tmp logs before test runs
    if liteserv_platform == "net-msft":
        delete_tmp_logs()
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)

    sg_client = MobileRestClient()

    db.create_bulk_docs(number=num_cbl_docs, id_prefix="cblid", db=cbl_db, channels=channels)

    # Add docs in SG
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password=password, channels=channels)
    sg_client.create_session(sg_admin_url, sg_db, "autotest")

    replicator_authenticator = authenticator.authentication(username="autotest", password=password, authentication_type="basic")
    repl_config = replicator.configure(cbl_db, target_url=sg_blip_url, continuous=False,
                                       channels=channels, replicator_authenticator=replicator_authenticator)
    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl)

    verify_password_masked(liteserv_platform, log_file, password)


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.replication
@pytest.mark.parametrize("invalid_password", [
    ("auto-password"),
    ("auto password"),
    ("invalidpassword"),
])
def test_verify_invalid_maskPassword_in_logs(params_from_base_test_setup, invalid_password):
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
    log_file = params_from_base_test_setup["log_filename"]
    liteserv_platform = params_from_base_test_setup["liteserv_platform"]

    num_cbl_docs = 5
    # Cannot run on iOS as there is no support in xcode to grab cbl logs
    if sync_gateway_version < "2.0.0" or liteserv_platform.lower() == "ios":
        pytest.skip('This test cannnot run with sg version below 2.0 and if platform is iOS')

    channels = ["ABC"]
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    if liteserv_platform == "net-msft":
        delete_tmp_logs()  # Clean up tmp logs before test runs
    replicator = Replication(base_url)
    authenticator = Authenticator(base_url)

    sg_client = MobileRestClient()
    db.create_bulk_docs(number=num_cbl_docs, id_prefix="cblid", db=cbl_db, channels=channels)

    # Add docs in SG
    sg_client.create_user(sg_admin_url, sg_db, "autotest", password="password", channels=channels)
    sg_client.create_session(sg_admin_url, sg_db, "autotest")

    replicator_authenticator = authenticator.authentication(username="autotest", password=invalid_password, authentication_type="basic")
    repl_config = replicator.configure(cbl_db, target_url=sg_blip_url, continuous=False,
                                       channels=channels, replicator_authenticator=replicator_authenticator)

    repl = replicator.create(repl_config)
    replicator.start(repl)
    replicator.wait_until_replicator_idle(repl, err_check=False)

    verify_password_masked(liteserv_platform, log_file, invalid_password)


def verify_password_masked(liteserv_platform, log_file, password):
    if liteserv_platform.lower() == "android":
        log_file = log_file.replace(" ", "\ ")

    if liteserv_platform == "net-msft":
        log_full_path = "/tmp/cbl-logs/"
        config_location = "resources/liteserv_configs/net-msft"
        ansible_runner = AnsibleRunner(config=config_location)

        status = ansible_runner.run_ansible_playbook(
            "fetch-windows-cbl-logs.yml",
            extra_vars={
                "log_full_path": log_full_path
            }
        )
        if status != 0:
            raise Exception("Could not fetch cbl logs from windows ")

        log_file = subprocess.check_output("ls -t {}* | head -1".format(log_full_path), shell=True)

    password = password.replace(" ", "\ ")
    log_file = log_file.strip()
    command = "grep {} {} | wc -l".format(password, log_file)
    output = subprocess.check_output(command, shell=True)
    output = int(output.strip())
    assert output == 0, "password showed up in clear text in logs"


def delete_tmp_logs():
    del_output = subprocess.check_output("rm -rf /tmp/cbl-logs", shell=True)
    print "delete output is ", del_output
