*** Settings ***
Resource    resources/common.robot

Library     Process
Library     OperatingSystem
Library     ${Libraries}/NetworkUtils.py
Library     ${KEYWORDS}/Logging.py

Library     ../test_bucket_shadow.py
Library     ../test_sg_replicate.py

Suite Setup     Suite Setup
Suite Teardown  Suite Teardown

Test Setup  Setup Test

Test Teardown   Test Teardown

Test Timeout    10 minutes

*** Variables ***
${CLUSTER_CONFIG}           ${CLUSTER_CONFIGS}/2sg_1cbs
${SYNC_GATEWAY_CONFIG}      ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_cc.json

*** Test Cases ***
# Cluster has been setup

# test bucket shadow
test bucket shadow low_revs limit repeated_deletes
    [Tags]   sanity
    test bucket shadow low_revs limit repeated_deletes

test bucket shadow low_revs limit
    [Tags]   sanity
    test bucket shadow low_revs limit

test bucket shadow multiple sync gateways
    [Tags]   sanity
    test bucket shadow multiple sync gateways

Test Sg Replicate Basic Test
    [Tags]   sanity
    Test Sg Replicate Basic Test

Test Sg Replicate Non Existent Db
    [Tags]   sanity
    Test Sg Replicate Non Existent Db

Test Sg Replicate Continuous Replication
    [Tags]   sanity
    Test Sg Replicate Continuous Replication

# Disable for 1.3 - https://github.com/couchbaselabs/mobile-testkit/issues/582
#Test Sg Replicate Delete Db Replication In Progress
#    [Tags]   sanity
#    Test Sg Replicate Delete Db Replication In Progress

Test Sg Replicate Basic Test Channels
    [Tags]   sanity
    Test Sg Replicate Basic Test Channels

Test Sg Replicate Push Async 100 docs
    [Tags]   sanity
    Test Sg Replicate Push Async    num_docs=${100}

Test Sg Replicate Push Async 250 docs
    [Tags]   sanity
    Test Sg Replicate Push Async    num_docs=${250}

Test Stop Replication Via Replication Id
    [Tags]   sanity
    Test Stop Replication Via Replication Id

Test Replication Config
    [Tags]   sanity
    Test Replication Config


*** Keywords ***
Setup Test
    Start Packet Capture

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
    Stop Packet Capture
    Collect Packet Capture  ${TEST_NAME}
    Run Keyword If Test Failed      Fetch And Analyze Logs  ${TEST_NAME}
