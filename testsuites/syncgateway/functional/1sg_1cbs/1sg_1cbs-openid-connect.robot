*** Settings ***
Resource    resources/common.robot

Library     Process
Library     OperatingSystem
Library     ../test_openid_connect.py
Library     DebugLibrary
Library     ${Libraries}/NetworkUtils.py
Library     ${KEYWORDS}/Logging.py

Test Timeout    10 minutes

Test Setup      Setup Test
Test Teardown   Teardown Test

*** Variables ***


*** Test Cases ***
# Cluster has been setup

Test OpenIdConnect Basic Test User Port
    [Tags]   sanity
    Test OpenIdConnect Basic Test  sg_url=${sg_url}  sg_db=${sg_db}  is_admin_port=${False}

Test OpenIdConnect Basic Test Admin Port
    [Tags]   sanity
    Test OpenIdConnect Basic Test  sg_url=${sg_url_admin}  sg_db=${sg_db}  is_admin_port=${True}

Test OpenIDConnect Notauthenticated
    [Tags]   sanity
    Test OpenIDConnect Notauthenticated  sg_url=${sg_url}  sg_db=${sg_db}

Test OpenIDConnect No Session
    [Tags]   sanity
    Test OpenIDConnect No Session  sg_url=${sg_url}  sg_db=${sg_db}

Test OpenIDConnect Oidc Challenge Invalid Provider Name
    [Tags]   sanity
    Test OpenIDConnect Oidc Challenge Invalid Provider Name  sg_url=${sg_url}  sg_db=${sg_db}

Test OpenIDConnect Expired Token
    [Tags]   sanity
    Test OpenIDConnect Expired Token  sg_url=${sg_url}  sg_db=${sg_db}

Test OpenIDConnect Garbage Token
    [Tags]   sanity
    Test OpenIDConnect Garbage Token  sg_url=${sg_url}  sg_db=${sg_db}

Test OpenIDConnect Invalid Scope
    [Tags]   sanity
    Test OpenIDConnect Invalid Scope  sg_url=${sg_url}  sg_db=${sg_db}

Test OpenIDConnect Small Scope
    [Tags]   sanity
    Test OpenIDConnect Small Scope  sg_url=${sg_url}  sg_db=${sg_db}

Test OpenIDConnect Large Scope
    [Tags]   sanity
    Test OpenIDConnect Large Scope  sg_url=${sg_url}  sg_db=${sg_db}

Test OpenIDConnect Public Session Endpoint
    [Tags]   sanity
    Test OpenIDConnect Public Session Endpoint  sg_url=${sg_url}  sg_db=${sg_db}

*** Keywords ***
Setup Test
    Log  Using cluster %{CLUSTER_CONFIG}  console=True
    Set Environment Variable  CLUSTER_CONFIG  ${CLUSTER_CONFIGS}/1sg_1cbs


    Set Test Variable  ${sg_config}  ${SYNC_GATEWAY_CONFIGS}/sync_gateway_openid_connect_cc.json
    Reset Cluster  ${sg_config}

    ${cluster_hosts} =  Get Cluster Topology  %{CLUSTER_CONFIG}
    Set Test Variable  ${cluster_hosts}

    Set Test Variable  ${cbs_url}       ${cluster_hosts["couchbase_servers"][0]}
    Set Test Variable  ${sg_url}        ${cluster_hosts["sync_gateways"][0]["public"]}
    Set Test Variable  ${sg_url_admin}  ${cluster_hosts["sync_gateways"][0]["admin"]}

    Set Test Variable  ${sg_db}  db
    Set Test Variable  ${bucket}  data-

Teardown Test
    Log  Tearing down test ...  console=True
    List Connections
    Run Keyword If Test Failed  Fetch And Analyze Logs  ${TEST_NAME}
