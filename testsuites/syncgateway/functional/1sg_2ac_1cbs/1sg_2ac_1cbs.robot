*** Settings ***
Resource    resources/common.robot

Library     Process
Library     OperatingSystem
Library     ${Libraries}/NetworkUtils.py
Library     ${Libraries}/LoggingKeywords.py

Library     ../test_cbgt_pindex.py
Library     ../test_dcp_reshard.py

Suite Setup     Suite Setup
Suite Teardown  Suite Teardown

Test Teardown   Test Teardown

Test Timeout    10 minutes

*** Variables ***
${CLUSTER_CONFIG}           ${CLUSTER_CONFIGS}/1sg_2ac_1cbs
${SYNC_GATEWAY_CONFIG}      ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json
${PROVISION_CLUSTER}        True

*** Test Cases ***
# Cluster has been setup

# Test TestCbgtPIndex
test_pindex_distribution
    [Tags]   sanity
    test_pindex_distribution

# test_dcp_reshard
test dcp reshard sync gateway goes down
    [Tags]   sanity
    test dcp reshard sync gateway goes down             ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json

test dcp reshard sync_gateway comes up
    [Tags]   sanity
    test dcp reshard sync_gateway comes up              ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json

test dcp reshard single sg accel goes down and up
    [Tags]   nightly
    test dcp reshard single sg accel goes down and up   ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json


*** Keywords ***
Suite Setup
    Log  Setting up suite ...  console=True
    Set Environment Variable  CLUSTER_CONFIG  ${CLUSTER_CONFIG}

    Run Keyword If  ${PROVISION_CLUSTER}
    ...  Provision Cluster
    ...     server_version=${SERVER_VERSION}
    ...     sync_gateway_version=${SYNC_GATEWAY_VERSION}
    ...     sync_gateway_config=${SYNC_GATEWAY_CONFIG}

    Verify Cluster Versions
    ...  cluster_config=%{CLUSTER_CONFIG}
    ...  expected_server_version=${SERVER_VERSION}
    ...  expected_sync_gateway_version=${SYNC_GATEWAY_VERSION}

Suite Teardown
    Log  Tearing down suite ...  console=True

Test Teardown
    Log  Tearing down test ...  console=True
    List Connections
    Run Keyword If Test Failed      Fetch And Analyze Logs  ${TEST_NAME}