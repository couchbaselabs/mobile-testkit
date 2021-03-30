import pytest
import time
import os
# import multiprocessing
import subprocess
# from threading import Thread
# from threading import Event
from requests.exceptions import HTTPError

# from keywords.utils import log_info, get_local_ip
from keywords.utils import log_info
from keywords.ClusterKeywords import ClusterKeywords
from keywords.MobileRestClient import MobileRestClient
# from keywords.SyncGateway import SyncGateway
from keywords.SyncGateway import sync_gateway_config_path_for_mode

from keywords import document
from libraries.testkit.cluster import Cluster
from utilities.copy_files_to_nodes import create_files_with_content
from utilities.cluster_config_utils import copy_sgconf_to_temp, replace_string_on_sgw_config
from libraries.testkit.syncgateway import get_buckets_from_sync_gateway_config
from keywords.couchbaseserver import get_sdk_client_with_bucket
from libraries.provision.ansible_runner import AnsibleRunner
from keywords.constants import ENVIRONMENT_FILE
from libraries.testkit.admin import Admin


@pytest.mark.syncgateway
@pytest.mark.sync
@pytest.mark.oscertify
@pytest.mark.parametrize("sg_conf_name, js_type", [
    ("custom_sync/sync_gateway_externalize_js", "sync_function"),
    ("custom_sync/sync_gateway_externalize_js", "import_filter")
])
def test_local_jsfunc_path(params_from_base_test_setup, sg_conf_name, js_type):
    """
    1. Create valid js function in the file which sgw can read and save it locally on the node where SGw is
    2. Create a sync config file and point the sync gateway filter/sync function to the file where it is located
    3 .Start sync gateway
    4. Verify SGW starts sucessfully
    5. Write a test which documents can process the sgw config
    6. Verify the documents are process and worked based on js sync function/import filter
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    sg_platform = params_from_base_test_setup["sg_platform"]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]

    if sync_gateway_version < "3.0.0":
        pytest.skip("this feature not available below 3.0.0")
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    cluster_helper = ClusterKeywords(cluster_config)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_config)
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    sg_url = cluster_hosts["sync_gateways"][0]["public"]
    username = "autotest"
    password = "password"
    doc_id = "doc_1"
    sg_db = "db"
    channel = ["sgw-env-var"]
    num_docs = 10
    sdk_non_mobile = "sdk_non_mobile"
    sdk_mobile = "sdk_mobile"
    sg_client = MobileRestClient()

    cluster = Cluster(config=cluster_config)

    sg_ip = cluster.sync_gateways[0].ip

    # Create and set up sdk client
    cbs_ip = cluster.servers[0].host
    bucket = cluster.servers[0].get_bucket_names()[0]
    sdk_client = get_sdk_client_with_bucket(ssl_enabled, cluster, cbs_ip, bucket)
    if js_type == "sync_function":
        # content = "function\(doc, oldDoc\)\{\
        #            throw\(\{forbidden: \\\"read only!\\\"\}\)\
        #            }"
        content = """function(doc, oldDoc){
                    throw({forbidden: "read only!"})
                }"""
        js_func_key = "\"sync\":\""
    elif js_type == "import_filter":
        content = "function\(doc\)\{ return doc.type == \\\"mobile\\\"\}"
        js_func_key = "\"import_filter\":\""
    file_name = "jsfile.js"
    path = create_files_with_content(content, sg_platform, sg_ip, file_name, cluster_config)
    path = js_func_key + path + "\","
    temp_sg_config, _ = copy_sgconf_to_temp(sg_conf, mode)
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ replace_with_js }}", path)
    cluster.reset(sg_config_path=temp_sg_config)

    topology = cluster_helper.get_cluster_topology(cluster_config)

    cbs_url = topology["couchbase_servers"][0]
    sg_url = topology["sync_gateways"][0]["public"]
    sg_url_admin = topology["sync_gateways"][0]["admin"]
    sg_db = "db"

    log_info("Running 'test_attachment_revpos_when_ancestor_unavailable'")
    log_info("Using cbs_url: {}".format(cbs_url))
    log_info("Using sg_url: {}".format(sg_url))
    log_info("Using sg_url_admin: {}".format(sg_url_admin))
    log_info("Using sg_db: {}".format(sg_db))
    log_info("Using bucket: {}".format(bucket))

    sg_client.create_user(sg_admin_url, sg_db, username, password=password, channels=channel)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, username)
    user_session = cookie, session_id

    # sync_function verification
    if js_type == "sync_function":
        sg_doc_body = document.create_doc(doc_id=doc_id, channels=channel)
        # document.add_doc(doc_id="access_doc", content={"grant_access": "true"})
        with pytest.raises(HTTPError) as he:
            sg_client.add_doc(url=sg_url, db=sg_db, doc=sg_doc_body, auth=user_session)
        assert str(he.value).startswith("403 Client Error: Forbidden for url:")

    # import_filter verification
    if js_type == "import_filter":
        def update_mobile_prop():
            return {
                'updates': 0,
                'type': 'mobile',
            }

        def update_non_mobile_prop():
            return {
                'updates': 0,
                'test': 'true',
                'type': 'mobile opt out',
            }
        sdk_doc_bodies = document.create_docs(sdk_mobile, number=num_docs, channels=channel, prop_generator=update_mobile_prop)
        sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
        sdk_docs_resp = sdk_client.upsert_multi(sdk_docs)

        sdk_doc_bodies = document.create_docs(sdk_non_mobile, number=num_docs, channels=channel, prop_generator=update_non_mobile_prop)
        sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
        sdk_docs_resp = sdk_client.upsert_multi(sdk_docs)
        assert len(sdk_docs_resp) == num_docs
        retry_count = 0
        while retry_count < 5:
            sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=user_session)["rows"]
            count = sum(sdk_mobile in doc["id"] for doc in sg_docs)
            if count == num_docs:
                break
            retry_count += 1
            time.sleep(1)
        assert count == num_docs, "docs with mobile type is not imported sgw"
        count = sum(sdk_non_mobile in doc["id"] for doc in sg_docs)
        assert count == 0, "docs with non mobile type is imported sgw which did not accepted sgw function"


@pytest.mark.syncgateway
@pytest.mark.sync
@pytest.mark.oscertify
@pytest.mark.parametrize("invalid_js_code, invalid_jsfile_path", [
    (True, False),
    (False, True)
])
def test_invalid_jsfunc(params_from_base_test_setup, invalid_js_code, invalid_jsfile_path):
    """
    "1. Create valid js function in the file which sgw can read
    2. provide valid sync gateyway function
    3. Provide invalid js path/jscode for sync key in sgw config
    4. Start sync gateway, it should start successfully
    5. Verify sync gateway fails to create a doc as jscode/jsfilepath is invalid
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    sg_platform = params_from_base_test_setup["sg_platform"]
    sg_conf_name = "custom_sync/sync_gateway_externalize_js"

    if sync_gateway_version < "3.0.0":
        pytest.skip("this feature not available below 3.0.0")
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    cluster_helper = ClusterKeywords(cluster_config)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_config)
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    sg_url = cluster_hosts["sync_gateways"][0]["public"]
    username = "autotest"
    password = "password"
    doc_id = "doc_1"
    sg_db = "db"
    channel = ["sgw-env-var"]
    sg_client = MobileRestClient()
    cluster = Cluster(config=cluster_config)
    sg_ip = cluster.sync_gateways[0].ip

    if invalid_js_code:
        content = "function\(doc, oldDoc\;\;\)\{\
                throw\(\{forbidden: \\\"read only!\\\"\}\)\
                }"
    else:
        content = "function\(doc, oldDoc\)\{\
                throw\(\{forbidden: \\\"read only!\\\"\}\)\
                }"
    if invalid_jsfile_path:
        file_name = "jsfile2.js"
    else:
        file_name = "jsfile.js"
    path = create_files_with_content(content, sg_platform, sg_ip, file_name, cluster_config)
    path = "\"sync\":\"" + path + "\","
    temp_sg_config, _ = copy_sgconf_to_temp(sg_conf, mode)
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ replace_with_js }}", path)
    cluster.reset(sg_config_path=temp_sg_config)

    topology = cluster_helper.get_cluster_topology(cluster_config)

    cbs_url = topology["couchbase_servers"][0]
    sg_url = topology["sync_gateways"][0]["public"]
    sg_url_admin = topology["sync_gateways"][0]["admin"]
    sg_db = "db"
    bucket = "data-bucket"

    log_info("Running 'test_attachment_revpos_when_ancestor_unavailable'")
    log_info("Using cbs_url: {}".format(cbs_url))
    log_info("Using sg_url: {}".format(sg_url))
    log_info("Using sg_url_admin: {}".format(sg_url_admin))
    log_info("Using sg_db: {}".format(sg_db))
    log_info("Using bucket: {}".format(bucket))

    sg_client.create_user(sg_admin_url, sg_db, username, password=password, channels=channel)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, username)
    session1 = cookie, session_id

    # 1. Create a doc
    sg_doc_body = document.create_doc(doc_id=doc_id, channels=channel)
    with pytest.raises(HTTPError) as he:
        sg_client.add_doc(url=sg_url, db=sg_db, doc=sg_doc_body, auth=session1)
    assert str(he.value).startswith("500 Server Error: Internal Server Error for url:")


"""
@pytest.mark.syncgateway
@pytest.mark.sync
def test_invalid_external_jspath(params_from_base_test_setup, setup_jsserver):
    """ """
    1. Create valid js function in the file which sgw can read
    2. Start sync gateway
    3. Verify SGW starts sucessfully
    4. Write a test which documents can process the sgw config
    5. Verify the documents are process and worked based on js sync function
    """ """

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    sg_platform = params_from_base_test_setup["sg_platform"]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    orig_sg_conf = "sync_gateway_default_functional_tests"
    sg_conf_name = "custom_sync/sync_gateway_externalize_js"

    if sync_gateway_version < "3.0.0":
        pytest.skip("this feature not available below 3.0.0")
    orig_sg_conf = sync_gateway_config_path_for_mode(orig_sg_conf, mode)
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    cluster_helper = ClusterKeywords(cluster_config)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_config)
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    sg_url = cluster_hosts["sync_gateways"][0]["public"]
    username = "autotest"
    password = "password"
    sg_db = "db"
    channel = ["sgw-env-var"]
    sdk_non_webhook = "sdk_non_webhook"
    sdk_webhook = "sdk_webhook"
    sdk_webhook_docs = 7
    sdk_non_webhook_docs = 4
    sg_client = MobileRestClient()

    cluster = Cluster(config=cluster_config)
    cluster.reset(sg_config_path=orig_sg_conf)

    # Create and set up sdk client
    sg = cluster.sync_gateways[0]
    js_func_key = "\"import_filter\":\""
    path = "http://{}:5007/invalid_jsfunc".format(get_local_ip())
    path = js_func_key + path + "\","
    temp_sg_config, _ = copy_sgconf_to_temp(sg_conf, mode)
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ replace_with_js }}", path)
    Stop = Event()
    p = Thread(target=sg.restart, args=(temp_sg_config, cluster_config))
    p.start()
    # p = multiprocessing.Process(target=sg.restart(config=temp_sg_config, cluster_config=cluster_config))
    # p.start()

    # Wait for 60 seconds or until process finishes
    print("waiting for 60 seconds")
    print(time.time())
    p.join(60)
    print("after 60 seconds")
    print(time.time())
    print("is p alive", p.is_alive())
    if not p.is_alive():
        assert False, "Sync gateway started successfully"
    Stop.set()
    print(time.time())
    # If thread is still active
    """ """
    if p.is_alive():
        print("running... let's kill it...")

        # Terminate - may not work if process is stuck for good
        # p.terminate()
        # OR Kill - will work for sure, no chance for process to finish nicely however
        # p.kill()

        p.join()
     """ """
    try:
        sg.verify_launched(30)
        assert False, "Sync gateway started successfully with invalid external jsfile "
    except ConnectionError:
        log_info("Expected to have sync gateway fail to start")
    # assert False, "sync gateway started successfully with invalid jscode path"

"""


@pytest.mark.syncgateway
@pytest.mark.sync
@pytest.mark.oscertify
@pytest.mark.parametrize("sg_conf_name, default_values, filter_type", [
    ("custom_sync/sync_gateway_externalize_js", False, "sync_function"),
    ("custom_sync/sync_gateway_externalize_js", True, "import_filter"),
])
def test_envVariables_on_sgw_config(params_from_base_test_setup, setup_env_variables, sg_conf_name, default_values, filter_type):
    """
    1. Create SGW config with environment variables created for sync function/import filter
    2. Define environment variables/default values for each OS for js code and username
    3. Start SGW and verify it start successfully
    4. Verify  that username and jscode got substituted with environment variables/default values(for the ones which does not have environment variables)
        - verify by retrieving the docs and see docs imported
    """

    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    sg_platform = params_from_base_test_setup["sg_platform"]
    cluster_config = setup_env_variables["cluster_config"]
    cluster = setup_env_variables["cluster"]
    ansible_runner = setup_env_variables["ansible_runner"]
    sg_hostname = setup_env_variables["sg_hostname"]

    if sync_gateway_version < "3.0.0":
        pytest.skip("this feature not available below 3.0.0")
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    cluster_helper = ClusterKeywords(cluster_config)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_config)
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    sg_url = cluster_hosts["sync_gateways"][0]["public"]
    username = "autotest"
    password = "password"
    doc_id = "doc_1"
    sg_db = "db"
    channel = ["sgw-env-var"]
    sg_client = MobileRestClient()
    bucket_names = get_buckets_from_sync_gateway_config(sg_conf)
    # set up environment variables on sync gateway

    if filter_type == "sync_function":
        js_content = """function(doc, oldDoc){throw({forbidden: 'read only!'})}"""
        jsfunc = "\"sync\":" + "\"$jsfunc\","
    elif filter_type == "import_filter":
        js_content = """function(doc){ return doc.type == 'mobile'}"""
        jsfunc = "\"import_filter\":" + "\"$jsfunc\","

    if sg_platform == "windows":
        environment_string = """[String[]] $v = @("bucketuser=""" + bucket_names[0] + """", "jsfunc=\"""" + js_content + """\")
        Set-ItemProperty HKLM:SYSTEM\CurrentControlSet\Services\SyncGateway -Name Environment -Value $v
        """
    elif sg_platform == "macos":
        environment_string = """launchctl setenv bucketuser """ + bucket_names[0] + """
        launchctl setenv jsfunc \"""" + js_content + """\"
        """
    else:
        environment_string = """[Service]
        Environment="bucketuser=""" + bucket_names[0] + """"
        Environment="jsfunc=""" + js_content

    environment_file = os.path.abspath(ENVIRONMENT_FILE)
    environmentFileWriter = open(environment_file, "w")
    environmentFileWriter.write(environment_string)
    environmentFileWriter.close()
    playbook_vars = {
        "environment_file": environment_file
    }
    ansible_runner.run_ansible_playbook(
        "setup-env-variables-for-service.yml",
        extra_vars=playbook_vars,
        subset=sg_hostname
    )
    username_sub = "\"username\":" + "\"$bucketuser\","
    if default_values:
        password = "\"password\":" + "\"${password:-password}\","

    temp_sg_config, _ = copy_sgconf_to_temp(sg_conf, mode)

    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ replace_with_js }}", jsfunc)
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ username }}", username_sub)
    if default_values:
        temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ password }}", password)
    cluster.reset(sg_config_path=temp_sg_config)
    topology = cluster_helper.get_cluster_topology(cluster_config)

    cbs_url = topology["couchbase_servers"][0]
    sg_url = topology["sync_gateways"][0]["public"]
    sg_url_admin = topology["sync_gateways"][0]["admin"]
    sg_db = "db"
    bucket = "data-bucket"

    log_info("Running 'test_envVariables_withoutvalues'")
    log_info("Using cbs_url: {}".format(cbs_url))
    log_info("Using sg_url: {}".format(sg_url))
    log_info("Using sg_url_admin: {}".format(sg_url_admin))
    log_info("Using sg_db: {}".format(sg_db))
    log_info("Using bucket: {}".format(bucket))

    sg_client.create_user(sg_admin_url, sg_db, username, password=password, channels=channel)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, username)
    user_session = cookie, session_id

    if filter_type == "sync_function":
        sg_doc_body = document.create_doc(doc_id=doc_id, channels=channel)
        with pytest.raises(HTTPError) as he:
            sg_client.add_doc(url=sg_url, db=sg_db, doc=sg_doc_body, auth=user_session)
        assert str(he.value).startswith("403 Client Error: Forbidden for url:")

    # import_filter verification
    if filter_type == "import_filter":
        ssl_enabled = params_from_base_test_setup["ssl_enabled"]
        cbs_ip = cluster.servers[0].host
        num_docs = 10
        sdk_mobile = "sdk_mobile"
        sdk_non_mobile = "sdk_non_mobile"
        sdk_client = get_sdk_client_with_bucket(ssl_enabled, cluster, cbs_ip, bucket)

        def update_mobile_prop():
            return {
                'updates': 0,
                'type': 'mobile',
            }

        def update_non_mobile_prop():
            return {
                'updates': 0,
                'test': 'true',
                'type': 'mobile opt out',
            }
        sdk_doc_bodies = document.create_docs(sdk_mobile, number=num_docs, channels=channel, prop_generator=update_mobile_prop)
        sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
        sdk_docs_resp = sdk_client.upsert_multi(sdk_docs)

        sdk_doc_bodies = document.create_docs(sdk_non_mobile, number=num_docs, channels=channel, prop_generator=update_non_mobile_prop)
        sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
        sdk_docs_resp = sdk_client.upsert_multi(sdk_docs)
        assert len(sdk_docs_resp) == num_docs

        retry_count = 0
        while retry_count < 5:
            sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=user_session)["rows"]
            count = sum(sdk_mobile in doc["id"] for doc in sg_docs)
            if count == num_docs:
                break
            retry_count += 1
            time.sleep(1)
        assert count == num_docs, "docs with mobile type is not imported sgw"
        count = sum(sdk_non_mobile in doc["id"] for doc in sg_docs)
        assert count == 0, "docs with non mobile type is imported sgw which did not accepted sgw function"


@pytest.mark.syncgateway
@pytest.mark.sync
@pytest.mark.oscertify
@pytest.mark.parametrize("sg_conf_name", [
    "custom_sync/sync_gateway_externalize_js"
])
def test_envVariables_withoutvalues(params_from_base_test_setup, sg_conf_name):
    """
    1. Create SGW config with variables mentioned
    2. Do not create default values
    3. Do not set environment variables when starting SGW
    4. Verify environment variables are replaced with empty value
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]

    if sync_gateway_version < "3.0.0":
        pytest.skip("this feature not available below 3.0.0")
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    sg_db = "db"
    cluster = Cluster(config=cluster_config)
    admin = Admin(cluster.sync_gateways[0])

    jsfunc = "\"sync\":" + "\"$jsfunc\","
    username = "\"username\":" + "\"$bucketuser\","
    temp_sg_config, _ = copy_sgconf_to_temp(sg_conf, mode)
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ replace_with_js }}", jsfunc)
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ username }}", username)
    cluster.reset(sg_config_path=temp_sg_config)
    cluster.reset(sg_config_path=temp_sg_config)
    db_resp = admin.get_db_config(sg_db)
    # if environment variables are not set, it should set to empty value on the config
    assert db_resp['sync'] == "", "Sync gateway service getting wrong environment variables"
    assert db_resp['username'] == "", "Sync gateway service getting wrong environment variables"


@pytest.mark.syncgateway
@pytest.mark.sync
@pytest.mark.oscertify
def test_jscode_envvariables_path(params_from_base_test_setup, setup_env_variables):
    """
    This test is combination of expternal jscode(local file) with environment varibles set up
    1. Create valid js function in the file which sgw can read
    2. Have a SGW config by pointing the jsfile for import_filter function
    3. For the jsfile path, add a variable to substitute with environment variables
    4. Define the environment variables
    2. Start sync gateway
    3. Verify SGW starts sucessfully
    4. Write a test which documents can process based on import_filter function
    5. Verify the documents are process and worked based on import_filter function
    """

    cluster_config = params_from_base_test_setup["cluster_config"]
    mode = params_from_base_test_setup["mode"]
    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    sg_platform = params_from_base_test_setup["sg_platform"]
    ssl_enabled = params_from_base_test_setup["ssl_enabled"]
    ansible_runner = setup_env_variables["ansible_runner"]
    sg_hostname = setup_env_variables["sg_hostname"]
    sg_conf_name = "custom_sync/sync_gateway_externalize_js"

    if sync_gateway_version < "3.0.0":
        pytest.skip("this feature not available below 3.0.0")
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)
    cluster_helper = ClusterKeywords(cluster_config)
    cluster_hosts = cluster_helper.get_cluster_topology(cluster_config)
    sg_admin_url = cluster_hosts["sync_gateways"][0]["admin"]
    sg_url = cluster_hosts["sync_gateways"][0]["public"]
    username = "autotest"
    password = "password"
    sg_db = "db"
    channel = ["sgw-env-var"]
    num_docs = 10
    sdk_non_mobile = "sdk_non_mobile"
    sdk_mobile = "sdk_mobile"
    sg_client = MobileRestClient()

    cluster = Cluster(config=cluster_config)

    sg_ip = cluster.sync_gateways[0].ip
    # Set up environment variables
    tempjs = "jsfile.js"
    tempjs_str = "$tempjs"
    if sg_platform == "windows":
        environment_string = """[String[]] $v = @("tempjs=""" + tempjs + """\")
        Set-ItemProperty HKLM:SYSTEM\CurrentControlSet\Services\SyncGateway -Name Environment -Value $v
        """
    elif sg_platform == "macos":
        environment_string = """launchctl setenv tempjs """ + tempjs + """
        """
    else:
        environment_string = """[Service]
        Environment="tempjs=""" + tempjs

    environment_file = os.path.abspath(ENVIRONMENT_FILE)
    environmentFileWriter = open(environment_file, "w")
    environmentFileWriter.write(environment_string)
    environmentFileWriter.close()
    playbook_vars = {
        "environment_file": environment_file
    }
    ansible_runner.run_ansible_playbook(
        "setup-env-variables-for-service.yml",
        extra_vars=playbook_vars,
        subset=sg_hostname
    )
    # Create and set up sdk client
    cbs_ip = cluster.servers[0].host
    bucket = cluster.servers[0].get_bucket_names()[0]
    sdk_client = get_sdk_client_with_bucket(ssl_enabled, cluster, cbs_ip, bucket)
    content = "function\(doc\)\{ return doc.type == \\\"mobile\\\"\}"
    js_func_key = "\"import_filter\":\""
    file_name = "jsfile.js"
    path = create_files_with_content(content, sg_platform, sg_ip, file_name, cluster_config)
    path = js_func_key + path + "\","
    sgw_config_js_path = path.replace(file_name, tempjs_str)
    temp_sg_config, _ = copy_sgconf_to_temp(sg_conf, mode)
    temp_sg_config = replace_string_on_sgw_config(temp_sg_config, "{{ replace_with_js }}", sgw_config_js_path)
    cluster.reset(sg_config_path=temp_sg_config)

    topology = cluster_helper.get_cluster_topology(cluster_config)

    cbs_url = topology["couchbase_servers"][0]
    sg_url = topology["sync_gateways"][0]["public"]
    sg_url_admin = topology["sync_gateways"][0]["admin"]
    sg_db = "db"

    log_info("Running 'test_attachment_revpos_when_ancestor_unavailable'")
    log_info("Using cbs_url: {}".format(cbs_url))
    log_info("Using sg_url: {}".format(sg_url))
    log_info("Using sg_url_admin: {}".format(sg_url_admin))
    log_info("Using sg_db: {}".format(sg_db))
    log_info("Using bucket: {}".format(bucket))

    sg_client.create_user(sg_admin_url, sg_db, username, password=password, channels=channel)
    cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, username)
    user_session = cookie, session_id

    # import_filter verification
    def update_mobile_prop():
        return {
            'updates': 0,
            'type': 'mobile',
        }

    def update_non_mobile_prop():
        return {
            'updates': 0,
            'test': 'true',
            'type': 'mobile opt out',
        }
    sdk_doc_bodies = document.create_docs(sdk_mobile, number=num_docs, channels=channel, prop_generator=update_mobile_prop)
    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    sdk_docs_resp = sdk_client.upsert_multi(sdk_docs)

    sdk_doc_bodies = document.create_docs(sdk_non_mobile, number=num_docs, channels=channel, prop_generator=update_non_mobile_prop)
    sdk_docs = {doc['_id']: doc for doc in sdk_doc_bodies}
    sdk_docs_resp = sdk_client.upsert_multi(sdk_docs)
    assert len(sdk_docs_resp) == num_docs
    retry_count = 0
    while retry_count < 5:
        sg_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=user_session)["rows"]
        count = sum(sdk_mobile in doc["id"] for doc in sg_docs)
        if count == num_docs:
            break
        retry_count += 1
        time.sleep(1)
    assert count == num_docs, "docs with mobile type is not imported sgw"
    count = sum(sdk_non_mobile in doc["id"] for doc in sg_docs)
    assert count == 0, "docs with non mobile type is imported sgw which did not accepted sgw function"


@pytest.fixture(scope="function")
def setup_jsserver():
    process = subprocess.Popen(args=["nohup", "python", "libraries/utilities/host_sgw_jscode.py", "--start", "&"], stdout=subprocess.PIPE)
    yield{
        "process": process
    }

    process.kill()


@pytest.fixture(scope="function")
def setup_env_variables(params_from_base_test_setup):
    cluster_config = params_from_base_test_setup["cluster_config"]
    ansible_runner = AnsibleRunner(cluster_config)
    cluster = Cluster(config=cluster_config)
    sg_hostname = cluster.sync_gateways[0].hostname
    yield{
        "cluster_config": cluster_config,
        "cluster": cluster,
        "sg_hostname": sg_hostname,
        "ansible_runner": ansible_runner
    }
    status = ansible_runner.run_ansible_playbook(
        "remove-env-variables-for-service.yml",
        subset=sg_hostname
    )
    assert status == 0, "ansible failed to remove systemd environment variables directory"


def construct_env_variables_string(sg_platform, sg_conf):
    bucket_names = get_buckets_from_sync_gateway_config(sg_conf)
    if sg_platform == "windows":
        environment_string = """[String[]] $v = @("bucketuser=""" + bucket_names[0] + """", "jsfunc=function(doc, oldDoc){throw({forbidden: 'read only!'})}")
        Set-ItemProperty HKLM:SYSTEM\CurrentControlSet\Services\SyncGateway -Name Environment -Value $v
        """
    elif sg_platform == "macos":
        environment_string = """export bucketuser=""" + bucket_names[0] + """
        export jsfunc=function(doc, oldDoc){throw({forbidden: 'read only!'})}")
        """
    else:
        environment_string = """[Service]
        Environment="bucketuser=""" + bucket_names[0] + """"
        Environment="jsfunc=function(doc, oldDoc){throw({forbidden: 'read only!'})}"
        """

    return environment_string
