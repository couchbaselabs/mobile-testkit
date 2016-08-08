*** Settings ***
Resource    resources/common.robot

Library     Process
Library     OperatingSystem
Library     ${Libraries}/NetworkUtils.py
Library     ${KEYWORDS}/Logging.py
Library     ${KEYWORDS}/CouchbaseServer.py
Library     rebalance_scenarios.py

Test Setup  Setup Test
Test Teardown  Teardown Test

Test Timeout    15 minutes

*** Variables ***

*** Test Cases ***
# Cluster has been setup

Test Rebalance Distributed Index Sanity
    [Tags]   sanity
    Test Distributed Index Rebalance Sanity  ${cluster_hosts}


*** Keywords ***
Setup Test
    Set Environment Variable  CLUSTER_CONFIG  ${CLUSTER_CONFIGS}/1sg_1ac_2cbs

    Set Test Variable  ${sg_config}  ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json
    Reset Cluster  ${sg_config}

    ${cluster_hosts} =  Get Cluster Topology  %{CLUSTER_CONFIG}
    Set Test Variable  ${cluster_hosts}

Teardown Test
    Log  Tearing down test ...  console=True

    List Connections
    Run Keyword If Test Failed  Fetch And Analyze Logs  ${TEST_NAME}