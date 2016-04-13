*** Settings ***
Resource    resources/common.robot

Library     Process
Library     OperatingSystem
Library     ${Libraries}/ClusterKeywords.py
Library     ${Libraries}/LoggingKeywords.py

Library     test_bucket_shadow.py
Library     test_sg_replicate.py

Suite Setup     Suite Setup
Suite Teardown  Suite Teardown

# Test Teardown   Test Teardown

*** Variables ***
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

Test Sg Replicate Basic Test
    Test Sg Replicate Basic Test

Test Sg Replicate Non Existent Db
    Test Sg Replicate Non Existent Db

Test Sg Replicate Continuous Replication
    Test Sg Replicate Continuous Replication

Test Sg Replicate Delete Db Replication In Progress
    Test Sg Replicate Delete Db Replication In Progress

Test Sg Replicate Basic Test Channels
    Test Sg Replicate Basic Test Channels

Test Sg Replicate Push Async 100 docs
    Test Sg Replicate Push Async    num_docs=${100}

Test Sg Replicate Push Async 250 docs
    Test Sg Replicate Push Async    num_docs=${250}


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