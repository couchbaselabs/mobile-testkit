import os
import shutil
import time
import subprocess
import re
import pytest

from subprocess import Popen, PIPE
from keywords.ClusterKeywords import ClusterKeywords
from keywords.exceptions import LogScanningError, CollectionError
from keywords.SyncGateway import sync_gateway_config_path_for_mode, get_sync_gateway_version
from keywords.SyncGateway import SyncGateway
from keywords.utils import log_info, host_for_url
from libraries.testkit.cluster import Cluster
from utilities.cluster_config_utils import load_cluster_config_json
from utilities.cluster_config_utils import persist_cluster_config_environment_prop, copy_to_temp_conf
from utilities.scan_logs import scan_for_pattern, unzip_log_files
from keywords.MobileRestClient import MobileRestClient
from keywords import document, attachment
from libraries.provision.ansible_runner import AnsibleRunner
from keywords.remoteexecutor import RemoteExecutor


@pytest.mark.syncgateway
@pytest.mark.logredaction
@pytest.mark.logging
@pytest.mark.oscertify
@pytest.mark.parametrize("sg_conf_name, redaction_level, x509_cert_auth", [
    pytest.param("log_redaction", "partial", False, marks=pytest.mark.sanity),
    ("log_redaction", "none", True)
])
def test_log_redaction_config(params_from_base_test_setup, remove_tmp_sg_redaction_logs,
                              sg_conf_name, redaction_level, x509_cert_auth):
    """
    @summary
    1. Have sync_gateway config file with logging level as partial/none
    2. Restart sync_gateway
    3. Create user in sync_gateway
    4. Create docs with xattrs
    5. Verify data which is partial sensitive is tagged with 'ud' tags for partial
    and no ud tags if it is configured with None
    """
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    cluster_helper = ClusterKeywords(cluster_config)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_config)
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    sg_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_ip = host_for_url(sg_admin_url)
    sg_db = "db"
    num_of_docs = 10
    cbs_ce_version = params_from_base_test_setup["cbs_ce"]

    if get_sync_gateway_version(sg_ip)[0] < "2.1":
        pytest.skip("log redaction feature not available for version < 2.1 ")

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    log_info("Using cluster_conf: {}".format(cluster_config))
    log_info("Using sg_conf: {}".format(sg_conf))

    # Modifying log redaction level to partial
    temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'redactlevel', redaction_level,
                                            property_name_check=False)

    if x509_cert_auth and not cbs_ce_version:
        persist_cluster_config_environment_prop(temp_cluster_config, 'x509_certs', True)

    cluster = Cluster(config=temp_cluster_config)
    cluster.reset(sg_config_path=sg_conf)

    # Create user in sync_gateway
    sg_client = MobileRestClient()
    channels = ["log-redaction"]
    sg_client.create_user(url=sg_admin_url, db=sg_db, name='autotest', password='validkey', channels=channels)
    autouser_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name='autotest')

    # Create docs with xattrs
    sgdoc_bodies = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs,
                                        attachments_generator=attachment.generate_2_png_10_10, channels=channels)
    sg_docs = sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sgdoc_bodies, auth=autouser_session)
    assert len(sg_docs) == num_of_docs

    # Verify log_redaction in the logs
    verify_log_redaction(temp_cluster_config, redaction_level, mode)


@pytest.mark.syncgateway
@pytest.mark.logredaction
@pytest.mark.logging
@pytest.mark.oscertify
@pytest.mark.parametrize("sg_conf_name, redaction_level, redaction_salt, x509_cert_auth", [
    ("log_redaction", "partial", False, True),
    pytest.param("log_redaction", "none", False, False, marks=pytest.mark.sanity),
    ("log_redaction", "partial", True, True)
])
def test_sgCollect1(params_from_base_test_setup, remove_tmp_sg_redaction_logs, sg_conf_name,
                    redaction_level, redaction_salt, x509_cert_auth):
    """
    @summary
    1. Have sync_gateway config file with logging level as partial/None
    2. Restart sync_gateway
    3. Create user in sync_gateway
    4. Create docs with xattrs
    5. Verify redacted files are hashed for partial , but not for None
    """
    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    cluster_helper = ClusterKeywords(cluster_config)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_config)
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    sg_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_ip = host_for_url(sg_admin_url)

    sg_db = "db"
    num_of_docs = 10
    user_name = "autotest"
    password = "validkey"

    if get_sync_gateway_version(sg_ip)[0] < "2.1":
        pytest.skip("log redaction feature not available for version < 2.1 ")

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    # Modifying log redaction level to partial
    temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'redactlevel', "partial", property_name_check=False)
    cbs_ce_version = params_from_base_test_setup["cbs_ce"]

    if x509_cert_auth and not cbs_ce_version:
        persist_cluster_config_environment_prop(temp_cluster_config, 'x509_certs', True)

    cluster = Cluster(config=temp_cluster_config)
    cluster.reset(sg_config_path=sg_conf)

    # Create user in sync_gateway
    sg_client = MobileRestClient()
    channels = ["log-redaction"]
    sg_client.create_user(url=sg_admin_url, db=sg_db, name=user_name, password=password, channels=channels)
    autouser_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name=user_name)

    # Create docs with xattrs
    sgdoc_bodies = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs,
                                        attachments_generator=attachment.generate_2_png_10_10, channels=channels)
    sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sgdoc_bodies, auth=autouser_session)
    assert len(sgdoc_bodies) == num_of_docs

    # Verify redacted files are hashed for partial , but not for None
    zip_file_name = sgcollect_redact(temp_cluster_config, redaction_level, redaction_salt)
    # verify redacted zip file exists for partial and non redacted file for none
    log_verification_withsgCollect(redaction_level, user_name, password, zip_file_name)


@pytest.mark.syncgateway
@pytest.mark.logredaction
@pytest.mark.logging
@pytest.mark.parametrize("sg_conf_name, redaction_level, redaction_salt, output_dir, x509_cert_auth", [
    ("log_redaction", "partial", False, False, True),
    pytest.param("log_redaction", None, False, False, False, marks=pytest.mark.oscertify),
    ("log_redaction", "partial", True, False, False),
    pytest.param("log_redaction", "partial", True, True, True, marks=pytest.mark.oscertify)
])
def test_sgCollect_restApi(params_from_base_test_setup, remove_tmp_sg_redaction_logs, sg_conf_name, redaction_level,
                           redaction_salt, output_dir, x509_cert_auth):
    """
    @summary
    1. Have sync_gateway config file with logging level as partial/None
    2. Restart sync_gateway
    3. Create user in sync_gateway
    4. Create docs with xattrs
    5. Do a post call for sgCollect With Rest Api and verify rest API works
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    cluster_helper = ClusterKeywords(cluster_config)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_config)
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    sg_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_ip = host_for_url(sg_admin_url)
    sg_platform = params_from_base_test_setup["sg_platform"]
    sg_db = "db"
    num_of_docs = 10
    user_name = 'autotest'
    password = 'validkey'
    sa_directory = None
    sa_host = None
    salt_value = None
    cbs_ce_version = params_from_base_test_setup["cbs_ce"]
    if get_sync_gateway_version(sg_ip)[0] < "2.1":
        pytest.skip("log redaction feature not available for version < 2.1 ")

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    # Modifying log redaction level to partial
    temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'redactlevel', "partial", property_name_check=False)

    if x509_cert_auth and not cbs_ce_version:
        persist_cluster_config_environment_prop(temp_cluster_config, 'x509_certs', True)

    cluster = Cluster(config=temp_cluster_config)
    cluster.reset(sg_config_path=sg_conf)

    # Get sync_gateway host and sa accel host
    cluster = load_cluster_config_json(cluster_config)
    sg_host = cluster["sync_gateways"][0]["ip"]
    if cluster["environment"]["ipv6_enabled"]:
        sg_host = "[{}]".format(sg_host)
    if mode == "di":
        sa_host_list = []
        sa_host = cluster["sg_accels"][0]["ip"]
        if cluster["environment"]["ipv6_enabled"]:
            for accel in cluster["sg_accels"]:
                sa_host_list.append("[{}]".format(accel["ip"]))
        else:
            for accel in cluster["sg_accels"]:
                sa_host_list.append(accel["ip"])

    # 3. Create user in sync_gateway
    sg_client = MobileRestClient()
    channels = ["log-redaction"]
    sg_client.create_user(url=sg_admin_url, db=sg_db, name=user_name, password=password, channels=channels)
    autouser_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name=user_name)

    # 4. Create docs with xattrs
    sgdoc_bodies = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs,
                                        attachments_generator=attachment.generate_2_png_10_10, channels=channels)
    png_a = next(iter(sgdoc_bodies[0]['_attachments']))
    binary_data = sgdoc_bodies[0]["_attachments"][png_a]["data"]
    sgdoc_bodies[0]["_attachments"][png_a]["data"] = str(binary_data, encoding='utf-8')
    sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sgdoc_bodies, auth=autouser_session)
    assert len(sgdoc_bodies) == num_of_docs
    if output_dir:
        if sg_platform == "windows":
            directory = "c{}\\test".format(":")
        elif sg_platform == "macos":
            directory = "/Users/sync_gateway/data"
        else:
            directory = "/home/sync_gateway/data"
            if mode == "di":
                sa_directory = "/home/sg_accel/data"
        sg_helper = SyncGateway()
        sg_helper.create_directory(cluster_config=cluster_config, url=sg_url, dir_name=directory)
    else:
        directory = None
    if redaction_salt:
        salt_value = "customized-redaction-salt-value"
        resp = sg_client.sgCollect_info(sg_host, redact_level=redaction_level, redact_salt=salt_value, output_directory=directory)
        if mode == "di":
            for sa_host in sa_host_list:
                sa_resp = sg_client.sgCollect_info(sa_host, redact_level=redaction_level, redact_salt=salt_value, output_directory=sa_directory)
    else:
        resp = sg_client.sgCollect_info(sg_host, redact_level=redaction_level, output_directory=directory)
        if mode == "di":
            for sa_host in sa_host_list:
                sa_resp = sg_client.sgCollect_info(sa_host, redact_level=redaction_level, output_directory=sa_directory)
    if resp["status"] != "started":
        assert False, "sg collect did not started"
    if mode == "di":
        if sa_resp["status"] != "started":
            assert False, "sga collect did not started"

    count = 0
    log_info("sg collect is running ........")
    # Minimum of 5 minute sleep time is recommended
    # Refer https://github.com/couchbase/sync_gateway/issues/3669
    if sg_platform == "windows":
        max_count = 200
    else:
        max_count = 60
    while sg_client.get_sgCollect_status(sg_host) == "running" and count < max_count:
        time.sleep(5)
        count += 1
    time.sleep(5)  # sleep until zip files created with sg collect rest end point

    pull_redacted_zip_file(temp_cluster_config, sg_platform, directory, sa_directory)
    # Verify files got redacted in sg collected files
    log_verification_withsgCollect(redaction_level, user_name, password, redaction_salt=salt_value)


@pytest.mark.syncgateway
@pytest.mark.logredaction
@pytest.mark.logging
@pytest.mark.oscertify
@pytest.mark.parametrize("sg_conf_name, x509_cert_auth", [
    ("log_redaction", False)
])
def test_sgCollectRestApi_errorMessages(params_from_base_test_setup, remove_tmp_sg_redaction_logs, sg_conf_name, x509_cert_auth):
    """
    @summary
    1. Have sync_gateway config file with logging level as partial/None
    2. Restart sync_gateway
    3. Create user in sync_gateway
    4. Create docs with xattrs
    5. Do a post call for sgCollect With Rest Api to test upload feature with negative values
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    cluster_helper = ClusterKeywords(cluster_config)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_config)
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    sg_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_ip = host_for_url(sg_admin_url)
    sg_db = "db"
    num_of_docs = 10
    cbs_ce_version = params_from_base_test_setup["cbs_ce"]
    if get_sync_gateway_version(sg_ip)[0] < "2.1":
        pytest.skip("log redaction feature not available for version < 2.1 ")

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    # Modifying log redaction level to partial
    temp_cluster_config = copy_to_temp_conf(cluster_config, mode)
    persist_cluster_config_environment_prop(temp_cluster_config, 'redactlevel', "partial", property_name_check=False)

    if x509_cert_auth and not cbs_ce_version:
        persist_cluster_config_environment_prop(temp_cluster_config, 'x509_certs', True)

    cluster = Cluster(config=temp_cluster_config)
    cluster.reset(sg_config_path=sg_conf)

    # Get sync_gateway host
    cluster = load_cluster_config_json(cluster_config)
    sg_host = cluster["sync_gateways"][0]["ip"]
    if cluster["environment"]["ipv6_enabled"]:
        sg_host = "[{}]".format(sg_host)

    # 3. Create user in sync_gateway
    sg_client = MobileRestClient()
    channels = ["log-redaction"]
    sg_client.create_user(url=sg_admin_url, db=sg_db, name='autotest', password='validkey', channels=channels)
    autouser_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name='autotest')

    # 4. Create docs with xattrs
    sgdoc_bodies = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs,
                                        attachments_generator=attachment.generate_2_png_10_10, channels=channels)
    sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sgdoc_bodies, auth=autouser_session)
    assert len(sgdoc_bodies) == num_of_docs

    # should throw an error when trying with upload host without upload
    upload_host = "https://s3.amazonaws.com/cb-customers"
    resp = sg_client.sgCollect_restCall(sg_host, redact_level="partial", upload_host=upload_host)
    log_info("Response Content", resp.content.decode('ascii'))
    assert "Invalid options used for sgcollect_info" in resp.content.decode('ascii'), "assert message for invalid options for sgcollect_info did not match"
    assert "upload_host" in resp.content.decode('ascii'), "did not get upload_host message in error content"
    customer = "customer-name"
    ticket = "123"

    # should throw an error when trying with customer without upload parameter
    resp = sg_client.sgCollect_restCall(sg_host, redact_level="partial", customer=customer)
    assert "Invalid options used for sgcollect_info:" in resp.content.decode('ascii')
    assert "customer" in resp.content.decode('ascii')

    # should throw an error when trying ticket without upload
    resp = sg_client.sgCollect_restCall(sg_host, redact_level="partial", ticket=ticket)
    assert "Invalid options used for sgcollect_info:" in resp.content.decode('ascii')
    assert "ticket" in resp.content.decode('ascii')

    # should throw an error when trying with upload_host, customer and ticket without upload
    resp = sg_client.sgCollect_restCall(sg_host, redact_level="partial", upload_host=upload_host, customer=customer, ticket=ticket)
    assert "Invalid options used for sgcollect_info:" in resp.content.decode('ascii')
    assert "upload_host" in resp.content.decode('ascii')

    # should throw an error when trying with output dir which does not exist
    output_dir = "/abc"
    resp = sg_client.sgCollect_restCall(sg_host, redact_level="partial", output_directory=output_dir)

    assert "Invalid options used for sgcollect_info:" in resp.content.decode('ascii')
    assert "no such file or directory:" in resp.content.decode('ascii')


@pytest.mark.syncgateway
@pytest.mark.logredaction
@pytest.mark.logging
def test_log_content_verification(params_from_base_test_setup, remove_tmp_sg_redaction_logs):
    """
    @summary
    1. Verify all the log files on sgcollect zip file exist after unzip
    2. Verify content of sync_gateway.log
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    cluster_helper = ClusterKeywords(cluster_config)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_config)
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    sg_url = cluster_hosts["sync_gateways"][0]["public"]
    sg_platform = params_from_base_test_setup["sg_platform"]
    sg_ip = host_for_url(sg_admin_url)
    sg_conf_name = "sync_gateway_default"
    sg_db = "db"
    num_of_docs = 10
    if get_sync_gateway_version(sg_ip)[0] < "2.8.1":
        pytest.skip("This feature is not available for version below 2.8.1 ")

    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    cluster = Cluster(config=cluster_config)
    cluster.reset(sg_config_path=sg_conf)

    # Get sync_gateway host
    cluster = load_cluster_config_json(cluster_config)
    sg_host = cluster["sync_gateways"][0]["ip"]
    if cluster["environment"]["ipv6_enabled"]:
        sg_host = "[{}]".format(sg_host)

    # Create user in sync_gateway
    sg_client = MobileRestClient()
    channels = ["logging"]
    sg_client.create_user(url=sg_admin_url, db=sg_db, name='autotest', password='password', channels=channels)
    autouser_session = sg_client.create_session(url=sg_admin_url, db=sg_db, name='autotest')

    # Create docs with xattrs
    sgdoc_bodies = document.create_docs(doc_id_prefix='sg_docs', number=num_of_docs,
                                        attachments_generator=attachment.generate_2_png_10_10, channels=channels)
    sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=sgdoc_bodies, auth=autouser_session)
    assert len(sgdoc_bodies) == num_of_docs

    resp = sg_client.sgCollect_info(sg_host)
    assert resp["status"] == "started", "sg collect did not started"
    count = 0
    log_info("sg collect is running ........")
    # Minimum of 5 minute sleep time is recommended
    # Refer https://github.com/couchbase/sync_gateway/issues/3669
    if sg_platform == "windows":
        max_count = 120
    else:
        max_count = 60
    while sg_client.get_sgCollect_status(sg_host) == "running" and count < max_count:
        time.sleep(5)
        count += 1
    time.sleep(5)  # sleep until zip files created with sg collect rest end point
    pull_redacted_zip_file(cluster_config, sg_platform)
    if sg_platform == "windows":
        json_cluster = load_cluster_config_json(cluster_config)
        sghost_username = json_cluster["sync_gateways:vars"]["ansible_user"]
        sghost_password = json_cluster["sync_gateways:vars"]["ansible_password"]
        remote_executor = RemoteExecutor(cluster.sync_gateways[0].ip, sg_platform, sghost_username, sghost_password)
    else:
        remote_executor = RemoteExecutor(cluster["sync_gateways"][0]["ip"])
    verify_all_logs_in_sgcollectzip(remote_executor)


def verify_log_redaction(cluster_config, log_redaction_level, mode):
    ansible_runner = AnsibleRunner(cluster_config)

    log_info("Pulling sync_gateway / sg_accel logs")
    # fetch logs from sync_gateway instances
    status = ansible_runner.run_ansible_playbook("fetch-sync-gateway-logs.yml")
    if status != 0:
        raise CollectionError("Could not pull logs")
    temp_log_path = ""
    # zip logs and timestamp
    if os.path.isdir("/tmp/sg_logs"):
        date_time = time.strftime("%Y-%m-%d-%H-%M-%S")
        temp_log_path = "/tmp/{}-{}-sglogs".format("log-redaction", date_time)
        shutil.copytree("/tmp/sg_logs", temp_log_path)
        temp_log_path1 = "{}/sg1".format(temp_log_path)
        temp_log_path_list = [temp_log_path1 + "/sg_info.log", temp_log_path1 + "/sg_debug.log"]
        if mode.lower() == "di":
            temp_log_path_list.append(temp_log_path + "/ac1/sg_accel_error.log")
            temp_log_path_list.append(temp_log_path + "/ac1/sg_debug.log")
            temp_log_path_list.append(temp_log_path + "/ac1/sg_info.log")
        for item in temp_log_path_list:
            try:
                scan_for_pattern(item, ["<ud>", "</ud>"])
            except LogScanningError as le:
                if log_redaction_level == "none":
                    continue
                else:
                    assert False, str(le)

    # verify starting and ending ud tags are equal
    num_ud_tags = subprocess.check_output("find {} -name '*.log' | xargs grep '<ud>' | wc -l".format(temp_log_path), shell=True)
    num_end_ud_tags = subprocess.check_output("find {} -name '*.log' | xargs grep '</ud>' | wc -l".format(temp_log_path), shell=True)
    assert num_ud_tags == num_end_ud_tags, "There is a mismatch of ud tags"
    shutil.rmtree(temp_log_path)


def sgcollect_redact(cluster_config, log_redaction_level, redaction_salt):
    ansible_runner = AnsibleRunner(cluster_config)

    log_info("started sg collect info")
    # fetch logs from sync_gateway instances
    date_time = time.strftime("%Y-%m-%d-%H-%M-%S")
    zip_file_name = "sgcollect-{}".format(date_time)
    salt_value = ""
    if redaction_salt:
        salt_value = "--log-redaction-salt='sg_collect test'"
    status = ansible_runner.run_ansible_playbook(
        "sgcollect-info.yml",
        extra_vars={
            "redact_level": log_redaction_level,
            "zip_file_name": zip_file_name,
            "salt_value": salt_value
        }
    )
    if status != 0:
        raise CollectionError("Could not pull logs")
    return zip_file_name


def pull_redacted_zip_file(cluster_config, sg_platform, output_dir=None, sa_output_dir=None):
    ansible_runner = AnsibleRunner(cluster_config)
    sg_logs_dir = output_dir
    sa_logs_dir = sa_output_dir
    if output_dir is None:
        if sg_platform == "macos":
            sg_logs_dir = "/Users/sync_gateway/logs"
            sa_logs_dir = "/Users/sg_accel/logs"
        elif sg_platform == "windows":
            sg_logs_dir = "C:{}".format(r"\PROGRA~1\Couchbase\\Sync Gateway\\var\\lib\\couchbase\\logs")
            sa_logs_dir = "C:{}".format(r"\PROGRA~1\Couchbase\\var\\logs")
        else:
            sg_logs_dir = "/home/sync_gateway/logs"
            sa_logs_dir = "/home/sg_accel/logs"

    status = ansible_runner.run_ansible_playbook(
        "pull-sgcollect-zip.yml",
        extra_vars={
            "sg_logs_dir": sg_logs_dir,
            "sa_logs_dir": sa_logs_dir
        }
    )
    if status != 0:
        raise CollectionError("Could not pull logs")


def verify_pattern_redacted(zip_file_name, pattern):
    if os.path.isdir("/tmp/sg_redaction_logs"):
        redacted_zip_file = zip_file_name
        command = "zipgrep -h -o \"" + pattern + "\" " + redacted_zip_file
        p = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
        output, error = p.communicate()
        assert len(output) == 0, pattern + " did not redacted "


def verify_udTags_in_zippedFile(zip_file_name):
    if os.path.isdir("/tmp/sg_redaction_logs"):
        non_redacted_zip_file = "/tmp/sg_redaction_logs/sg1/{}.zip".format(zip_file_name)
        command = "zipgrep -n -o \"<ud>.+</ud>\" " + non_redacted_zip_file + r" | cut -f2 -d/ | cut -f1 -d\<"
        line_num_output = subprocess.check_output(command, shell=True)
        ln_output_list = line_num_output.splitlines()
        command = "zipgrep -h -o \"<ud>.+</ud>\" " + non_redacted_zip_file
        ud_output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        ud_output_list = ud_output.splitlines()
        if len(line_num_output) == 0 and len(ud_output) == 0:
            assert False, "No user data tags found in " + non_redacted_zip_file
        nonredact_dict = dict(list(zip(ln_output_list, ud_output_list)))

        redacted_zip_file = "/tmp/sg_redaction_logs/sg1/{}-redacted.zip".format(zip_file_name)
        command = "zipgrep -n -o \"<ud>.+</ud>\" " + redacted_zip_file + r" | cut -f2 -d/ | cut -f1 -d\<"

        line_num_output = subprocess.check_output(command, shell=True)
        ln_output_list = line_num_output.splitlines()
        command = "zipgrep -h -o \"<ud>.+</ud>\" " + redacted_zip_file
        ud_output = subprocess.check_output(command, shell=True)
        ud_output_list = ud_output.splitlines()
        if len(line_num_output) == 0 and len(ud_output) == 0:
            assert False, "No user data tags found in " + redacted_zip_file
        redact_dict = dict(list(zip(ln_output_list, ud_output_list)))
        if len(list(nonredact_dict.items())) != len(list(redact_dict.items())):
            assert False, "User tags count mismatch between redacted and non-redacted files"

        for key, value in list(redact_dict.items()):
            redact_match = re.search("<ud>.+</ud>", value.decode('ascii'))
            if redact_match:
                redact_content = redact_match.group(0)
            else:
                assert False, "Line: " + key + "Value: " + value + " did not match <ud>.+</ud> regex"
            if re.search("[a-f0-9]{40}", redact_content):
                continue
            else:
                assert False, "Hashing failed for Line: " + key


def verify_saltvalue_in_redacted_zip_file(zip_file_name, salt_value):
    if os.path.isdir("/tmp/sg_redaction_logs"):

        redacted_zip_file = "/tmp/sg_redaction_logs/sg1/{}-redacted.zip".format(zip_file_name)
        zipgrep_command = "zipgrep -n -o \"{}\" ".format(salt_value)
        command = zipgrep_command + redacted_zip_file + r" | cut -f2 -d/ | cut -f1 -d\<"

        line_num_output = subprocess.check_output(command, shell=True)
        ln_output_list = line_num_output.splitlines()
        assert len(ln_output_list) == 0, "salt value shows up in the log files{}".format(line_num_output)


def log_verification_withsgCollect(redaction_level, user, password, zip_file_name=None, redaction_salt=None):
    if zip_file_name is None:
        if redaction_level is None:
            command = "ls /tmp/sg_redaction_logs/sg1/*.zip | awk -F'.zip' '{print $1}' | grep -o '[^/]*$'"
        else:
            command = "ls /tmp/sg_redaction_logs/sg1/*-redacted.zip | awk -F'-redacted.zip' '{print $1}' | grep -o '[^/]*$'"
        zip_file_name = subprocess.check_output(command, shell=True)
        zip_file_name = zip_file_name.rstrip()
        if isinstance(zip_file_name, (bytes, bytearray)):
            zip_file_name = zip_file_name.decode()
    redacted_file_name = "/tmp/sg_redaction_logs/sg1/{}-redacted.zip".format(zip_file_name)
    nonredacted_file_name = "/tmp/sg_redaction_logs/sg1/{}.zip".format(zip_file_name)
    if redaction_level == "partial":
        assert os.path.isfile(redacted_file_name), "redacted file is not generated"
        verify_udTags_in_zippedFile(zip_file_name)
        verify_pattern_redacted(redacted_file_name, user)
        verify_pattern_redacted(redacted_file_name, password)
        if redaction_salt is not None:
            verify_saltvalue_in_redacted_zip_file(zip_file_name, redaction_salt)
    else:
        assert not os.path.isfile(redacted_file_name), "redacted file is generated for redaction level None"
    assert os.path.isfile(nonredacted_file_name), "non redacted zip file is not generated"


def verify_all_logs_in_sgcollectzip(remote_executor, zip_file_name=None):
    if zip_file_name is None:
        command = "ls /tmp/sg_redaction_logs/sg1/*.zip | awk -F'.zip' '{print $1}' | grep -o '[^/]*$'"
        zip_file_name = subprocess.check_output(command, shell=True)
        zip_file_name = zip_file_name.rstrip()
        if isinstance(zip_file_name, (bytes, bytearray)):
            zip_file_name = zip_file_name.decode()
    sgcollect_zip_filename = "/tmp/sg_redaction_logs/sg1/{}.zip".format(zip_file_name)
    file_list_sgcollect_zip = ['expvars.json', 'pprof_block.pb.gz', 'pprof_goroutine.pb.gz', 'pprof_heap.pb.gz', 'pprof_mutex.pb.gz', 'pprof_profile.pb.gz',
                               'sg_debug.log', 'sg_error.log', 'sg_info.log', 'sg_stats.log', 'sg_warn.log', 'sgcollect_info_options.log', 'sync_gateway', 'sync_gateway.json',
                               'sync_gateway.log', 'syslog.tar.gz', 'systemd_journal.gz']
    for file in file_list_sgcollect_zip:
        bracket_command = "\"{}\""
        find_command = "find {} -type f -exec sh -c 'unzip -l {} | grep -q {}' \\; -print | wc -l".format(sgcollect_zip_filename, bracket_command, file)
        result_command = subprocess.check_output(find_command, shell=True)
        assert int(result_command.decode('utf-8').strip()) == 1, "{} do not exist".format(file)

    # unzip file
    unzip_log_files(sgcollect_zip_filename)
    sgcollect_zip_directory = sgcollect_zip_filename.split(".zip")[0]
    grep_command = "grep -E '(?:hostname: |hostname = |Host Name:(?:\s)*)(.*)' {}/*/sync_gateway.log".format(sgcollect_zip_directory)
    result_command = subprocess.check_output(grep_command, shell=True)
    _, stdout, _ = remote_executor.execute("hostname")
    assert_hostname = result_command.decode('utf-8').strip() == "kernel.hostname = {}".format(stdout[0].rstrip())
    assert (result_command.decode('utf-8').strip() == "kernel.hostname = localhost.localdomain" or assert_hostname), "did not get the right string from sync_gateway log file"


@pytest.fixture(scope="function")
def remove_tmp_sg_redaction_logs():
    if os.path.isdir("/tmp/sg_redaction_logs/"):
        shutil.rmtree("/tmp/sg_redaction_logs/")  # This is needed for log redaction tests
