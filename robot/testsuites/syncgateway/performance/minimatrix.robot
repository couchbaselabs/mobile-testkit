*** Settings ***
Resource    resources/common.robot

Library     Process
Library     OperatingSystem
Library     ${Libraries}/ClusterKeywords.py
Library     ${Libraries}/LoggingKeywords.py

Library     run_tests.py

Suite Setup     Suite Setup
Suite Teardown  Suite Teardown

Test Teardown   Test Teardown

*** Variables ***
${CBS_NUM}                  3
${CBS_TYPE}                 c3.2xlarge
${SG_NUM}                   2
${SG_TYPE}                  c3.2xlarge
${GATELOAD_NUM}             1
${GATELOAD_TYPE}            c3.2xlarge
${SERVER_VERSION}           4.1.0
${SYNC_GATEWAY_VERSION}     1.2.0-79
${CLUSTER_CONFIG}           ${CLUSTER_CONFIGS}/aws_perf_config
${SYNC_GATEWAY_CONFIG}      ${SYNC_GATEWAY_CONFIGS}/performance/sync_gateway_default_performance.json

*** Test Cases ***
# Cluster has been setup

# test_bulk_get_compression (channel cache mode)
Run perf test



*** Keywords ***
Suite Setup
    Log To Console      Setting up ...
    # TODO Create Cloudformation template and block until created, then generate ${CLUSTER_CONFIGS}/aws_perf_config
    # Create AWS Cluster    ${CBS_NUM}  ${CBS_TYPE}  ${SG_NUM}  ${SG_TYPE}  ${GATELOAD_NUM}  ${GATELOAD_TYPE}
    Set Environment Variable    CLUSTER_CONFIG    ${cluster_config}
    Provision Cluster   ${SERVER_VERSION}   ${SYNC_GATEWAY_VERSION}    ${SYNC_GATEWAY_CONFIG}

Suite Teardown
    Log To Console      Tearing down ...

Test Teardown
    Run Keyword If Test Failed      Fetch And Analyze Logs