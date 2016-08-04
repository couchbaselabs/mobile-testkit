
# This will not get run if the test is run with a direct reference to the test robot
# file, unless you define a keyword to explicitly run the Suite Setup in your robot test.

*** Settings ***
Resource    resources/common.robot

Library     Process
Library     OperatingSystem

Suite Setup     Suite Setup
Suite Teardown  Suite Teardown

Test Timeout    30 minutes

*** Variables ***
${SYNC_GATEWAY_CONFIG}      ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_di.json

*** Keywords ***
Suite Setup
    Log  Setting up suite ...  console=True
    Set Environment Variable  CLUSTER_CONFIG  ${CLUSTER_CONFIGS}/1sg_1ac_2cbs

    Provision Cluster
    ...  server_version=${SERVER_VERSION}
    ...  sync_gateway_version=${SYNC_GATEWAY_VERSION}
    ...  sync_gateway_config=${SYNC_GATEWAY_CONFIG}

Suite Teardown
    Log  Tearing down suite ...  console=True
