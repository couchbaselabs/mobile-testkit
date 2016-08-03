*** Settings ***
Resource    resources/common.robot

Library     Process
Library     ${Libraries}/NetworkUtils.py
Library     ${KEYWORDS}/Logging.py
Library     load_balancer_scenarios.py

Test Setup  Setup Test
Test Teardown  Teardown Test

Test Timeout    10 minutes

*** Variables ***
${CLUSTER_CONFIG}           ${CLUSTER_CONFIGS}/2sg_1cbs_1lbs

*** Test Cases ***
# Cluster has been setup

# test bucket shadow
Test Load Balance Sanity
    [Tags]   sanity
    Test Load Balance Sanity  ${cluster_hosts}


*** Keywords ***
Setup Test

    Log  Using cluster %{CLUSTER_CONFIG}  console=True

    Set Test Variable  ${sg_config}  ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_cc.json
    Reset Cluster  ${sg_config}

    ${cluster_hosts} =  Get Cluster Topology  %{CLUSTER_CONFIG}
    Set Test Variable  ${cluster_hosts}

Teardown Test
    Log  Tearing down test ...  console=True
    List Connections
    Run Keyword If Test Failed  Fetch And Analyze Logs  ${TEST_NAME}