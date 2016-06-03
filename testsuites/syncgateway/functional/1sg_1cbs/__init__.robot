*** Settings ***
Resource    resources/common.robot

Library     Process
Library     OperatingSystem

Suite Setup     Suite Setup
Suite Teardown  Suite Teardown

Test Timeout    10 minutes

*** Variables ***
${SYNC_GATEWAY_CONFIG}      ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_cc.json
${PROVISION_CLUSTER}        True

*** Keywords ***
Suite Setup
    Log  Setting up suite ...  console=True
    Set Environment Variable  CLUSTER_CONFIG  ${CLUSTER_CONFIGS}/1sg_1cbs

    Run Keyword If  ${PROVISION_CLUSTER}
    ...  Provision Cluster
    ...     server_version=${SERVER_VERSION}
    ...     sync_gateway_version=${SYNC_GATEWAY_VERSION}
    ...     sync_gateway_config=${SYNC_GATEWAY_CONFIG}


Suite Teardown
    Log  Tearing down suite ...  console=True
