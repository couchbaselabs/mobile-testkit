*** Settings ***
Resource    resources/common.robot

Library     Process
Library     OperatingSystem
Library     ${Libraries}/NetworkUtils.py
Library      ${KEYWORDS}/Logging.py

Library     ../test_continuous.py
Library     ../test_db_online_offline.py
Library     ../test_longpoll.py
Library     ../test_multiple_dbs.py
Library     ../test_multiple_users_multiple_channels_multiple_revisions.py
Library     ../test_roles.py
Library     ../test_seq.py
Library     ../test_single_user_single_channel_doc_updates.py
Library     ../test_sync.py
Library     ../test_users_channels.py

Suite Setup     Suite Setup
Suite Teardown  Suite Teardown

Test Teardown   Test Teardown

Test Timeout    30 minutes

*** Variables ***
${CLUSTER_CONFIG}           ${CLUSTER_CONFIGS}/1sg_1ac_1cbs
${SYNC_GATEWAY_CONFIG}      ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json

*** Test Cases ***
# Cluster has been setup






















# test_users_channels (Distributed Index)
test multiple users multiple channels (distributed index)
    [Tags]   sanity  syncgateway
    test multiple users multiple channels   ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json

test muliple users single channel (distributed index)
    [Tags]   sanity  syncgateway
    test muliple users single channel       ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json

test single user multiple channels (distributed index)
    [Tags]   sanity  syncgateway
    test single user multiple channels      ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json

test single user single channel (distributed index)
    [Tags]   sanity  syncgateway
    test single user single channel         ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json

*** Keywords ***
Suite Setup
    Log  Setting up suite ...  console=True
    Set Environment Variable  CLUSTER_CONFIG  ${CLUSTER_CONFIG}

    Provision Cluster
    ...  server_version=${SERVER_VERSION}
    ...  sync_gateway_version=${SYNC_GATEWAY_VERSION}
    ...  sync_gateway_config=${SYNC_GATEWAY_CONFIG}

Suite Teardown
    Log  Tearing down suite ...  console=True

Test Teardown
    Log  Tearing down test ...  console=True
    List Connections
    Run Keyword If Test Failed      Fetch And Analyze Logs  ${TEST_NAME}