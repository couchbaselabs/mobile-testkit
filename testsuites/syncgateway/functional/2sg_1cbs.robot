*** Settings ***
Resource    resources/common.robot

Library     Process
Library     OperatingSystem
Library     ${Libraries}/NetworkUtils.py
Library     ${Libraries}/ClusterKeywords.py
Library     ${Libraries}/LoggingKeywords.py

Library     test_bucket_shadow.py
Library     test_sg_replicate.py

Suite Setup     Suite Setup
Suite Teardown  Suite Teardown

Test Teardown   Test Teardown

*** Variables ***
${CLUSTER_CONFIG}           ${CLUSTER_CONFIGS}/2sg_1cbs
${SYNC_GATEWAY_VERSION}     None
${SYNC_GATEWAY_BRANCH}      None
${SYNC_GATEWAY_CONFIG}      ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_functional_tests_cc.json
${PROVISION_CLUSTER}        True

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

Test Sg Replicate Delete Db Replication In Progress
    [Tags]   sanity
    Test Sg Replicate Delete Db Replication In Progress

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
Suite Setup
    Set Environment Variable          CLUSTER_CONFIG  ${CLUSTER_CONFIG}
    Log                               Using cluster ${CLUSTER_CONFIG}
    Run Keyword If  ${PROVISION_CLUSTER} and '${SYNC_GATEWAY_VERSION}' != 'None'
    ...  Provision Cluster With Sync Gateway Build
    ...     server_version=${SERVER_VERSION}
    ...     sync_gateway_version=${SYNC_GATEWAY_VERSION}
    ...     sync_gateway_config=${SYNC_GATEWAY_CONFIG}

    Run Keyword If  ${PROVISION_CLUSTER} and '${SYNC_GATEWAY_BRANCH}' != 'None'
    ...  Provision Cluster With Sync Gateway Source
    ...     server_version=${SERVER_VERSION}
    ...     sync_gateway_branch=${SYNC_GATEWAY_BRANCH}
    ...     sync_gateway_config=${SYNC_GATEWAY_CONFIG}

Suite Teardown
    Log To Console      Tearing down ...

Test Teardown
    List Connections
    Run Keyword If Test Failed      Fetch And Analyze Logs