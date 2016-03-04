*** Settings ***
Resource    resources/Paths.robot

Library     Process
#Library     test_users_channels.py

Test Setup      Setup
Test Teardown   Teardown

*** Variables ***
${SERVER_VERSION}           4.1.0
${SYNC_GATEWAY_VERSION}     1.2.0-79
${CLUSTER_CONFIG}           ${CLUSTER_CONFIGS}/1sg_1s
${SYNC_GATEWAY_CONFIG}      ${SYNC_GATEWAY_CONFIGS}/sync_gateway_todolite.json

*** Test Cases ***
# Cluster has been setup

Test Users And Channels
    [Documentation]     Sync Gateway Functional Tests
    [Tags]              sync_gateway    nightly     bimode
    Log To Console      Hello
    # Test Users Channels

*** Keywords ***
Setup
    Log To Console      Setting up ...
    #Provision Cluster   ${CLUSTER_CONFIG}   ${SERVER_VERSION}   ${SYNC_GATEWAY_VERSION}    ${SYNC_GATEWAY_CONFIG}
    Install Sync Gateway   ${CLUSTER_CONFIG}    ${SYNC_GATEWAY_VERSION}    ${SYNC_GATEWAY_CONFIG}

Teardown
    Log To Console      Tearing down ...

Provision Cluster
    [Arguments]     ${cluster_config}   ${server_version}   ${sync_gateway_version}    ${sync_gateway_config}
    ${server_arg}               Catenate  SEPARATOR=  --server-version=            ${server_version}
    ${sync_gateway_arg}         Catenate  SEPARATOR=  --sync-gateway-version=      ${sync_gateway_version}
    ${sync_gateway_config_arg}  Catenate  SEPARATOR=  --sync-gateway-config-file=  ${sync_gateway_config}
    ${cluster_config_arg}       Catenate  SEPARATOR=  --cluster-config=            ${cluster_config}
    ${result} =  Run Process  python  ${LIBRARIES}/provision/provision_cluster.py  ${cluster_config_arg}  ${server_arg}  ${sync_gateway_arg}  ${sync_gateway_config_arg}
    Log To Console  ${result.stderr}
    Log To Console  ${result.stdout}

Install Server
    [Arguments]     ${cluster_config}   ${server_version}
    ${server_arg}               Catenate  SEPARATOR=  --version=          ${server_version}
    ${cluster_config_arg}       Catenate  SEPARATOR=  --cluster-config=   ${cluster_config}
    ${result} =  Run Process  python  ${LIBRARIES}/provision/install_couchbase_server.py  ${cluster_config_arg}  ${server_arg}
    Log To Console  ${result.stderr}
    Log To Console  ${result.stdout}

Install Sync Gateway
    [Arguments]     ${cluster_config}  ${sync_gateway_version}  ${sync_gateway_config}
    ${sync_gateway_arg}         Catenate  SEPARATOR=  --version=      ${sync_gateway_version}
    ${sync_gateway_config_arg}  Catenate  SEPARATOR=  --config-file=  ${sync_gateway_config}
    ${cluster_config_arg}       Catenate  SEPARATOR=  --cluster-config=            ${cluster_config}
    ${result} =  Run Process  python  ${LIBRARIES}/provision/install_sync_gateway.py  ${cluster_config_arg}  ${sync_gateway_arg}  ${sync_gateway_config_arg}
    Log To Console  ${result.stderr}
    Log To Console  ${result.stdout}