*** Settings ***
Resource    resources/common.robot

Library     Process
Library     OperatingSystem
Library     ${Libraries}/ClusterKeywords.py
Library     ${Libraries}/LoggingKeywords.py

Library     test_cbgt_pindex.py
Library     test_dcp_reshard.py

Suite Setup     Suite Setup
Suite Teardown  Suite Teardown

Test Teardown   Test Teardown

*** Variables ***
${SERVER_VERSION}           4.1.0
${SYNC_GATEWAY_VERSION}     1.2.0-79
${CLUSTER_CONFIG}           ${CLUSTER_CONFIGS}/1sg_1ac_1cbs
${SYNC_GATEWAY_CONFIG}      ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json

*** Test Cases ***
# Cluster has been setup

# Test TestCbgtPIndex
test_pindex_distribution
    test_pindex_distribution    ${SYNC_GATEWAY_CONFIGS}/performance/sync_gateway_default_performance.json

# test_dcp_reshard
test dcp reshard sync gateway goes down
    test dcp reshard sync gateway goes down             ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json

test dcp reshard sync_gateway comes up
    test dcp reshard sync_gateway comes up              ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json

test dcp reshard single sg accel goes down and up
    test dcp reshard single sg accel goes down and up   ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json

*** Keywords ***
Suite Setup
    Log To Console      Setting up ...
    Set Environment Variable    CLUSTER_CONFIG    ${CLUSTER_CONFIG}
    Log to Console        Using cluster ${CLUSTER_CONFIG}
    Provision Cluster   ${SERVER_VERSION}   ${SYNC_GATEWAY_VERSION}    ${SYNC_GATEWAY_CONFIG}

Suite Teardown
    Log To Console      Tearing down ...

Test Teardown
    Run Keyword If Test Failed      Fetch And Analyze Logs