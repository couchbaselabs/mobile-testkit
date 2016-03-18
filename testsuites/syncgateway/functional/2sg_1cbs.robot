*** Settings ***
Resource    resources/common.robot

Library     Process
Library     OperatingSystem
Library     ${Libraries}/ClusterKeywords.py
Library     ${Libraries}/LoggingKeywords.py

Library     test_bucket_shadow.py

Suite Setup     Suite Setup
Suite Teardown  Suite Teardown

Test Teardown   Test Teardown

*** Variables ***
${SERVER_VERSION}           4.1.0
${SYNC_GATEWAY_VERSION}     1.2.0-79
${CLUSTER_CONFIG}           ${CLUSTER_CONFIGS}/2sg_1cbs
${SYNC_GATEWAY_CONFIG}      ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_cc.json

*** Test Cases ***
# Cluster has been setup

# test bucket shadow
test bucket shadow low_revs limit repeated_deletes
    test bucket shadow low_revs limit repeated_deletes

test bucket shadow low_revs limit
    test bucket shadow low_revs limit

test bucket shadow multiple sync gateways
    test bucket shadow multiple sync gateways


*** Keywords ***
Suite Setup
    Log To Console              Setting up ...
    Set Environment Variable    CLUSTER_CONFIG    ${CLUSTER_CONFIG}
    Log                         Using cluster ${CLUSTER_CONFIG}
    Provision Cluster   ${SERVER_VERSION}   ${SYNC_GATEWAY_VERSION}    ${SYNC_GATEWAY_CONFIG}

Suite Teardown
    Log To Console      Tearing down ...

Test Teardown
    Run Keyword If Test Failed      Fetch And Analyze Logs