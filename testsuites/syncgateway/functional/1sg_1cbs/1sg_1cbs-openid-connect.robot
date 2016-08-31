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
    [Documentation]
    ...  Tests the basic OpenIDConnect login flow against the non-admin port
    [Tags]   sanity  syncgateway  oidc
    Reset Cluster  ${SYNC_GATEWAY_CONFIGS}/sync_gateway_openid_connect_cc.json
    Test OpenIdConnect Basic Test  sg_url=${sg_url}  sg_db=${sg_db}  is_admin_port=${False}  expect_signed_id_token=${True}

Test OpenIdConnect Basic Test Admin Port
    [Documentation]
    ...  Tests the basic OpenIDConnect login flow against the admin port
    [Tags]   sanity  syncgateway  oidc
    Reset Cluster  ${SYNC_GATEWAY_CONFIGS}/sync_gateway_openid_connect_cc.json
    Test OpenIdConnect Basic Test  sg_url=${sg_url_admin}  sg_db=${sg_db}  is_admin_port=${True}  expect_signed_id_token=${True}

Test OpenIdConnect Basic Test User Port Unsigned ID Token
    [Documentation]
    ...  Tests the basic OpenIDConnect login flow against the non-admin port
    [Tags]   sanity  syncgateway  oidc
    Reset Cluster  ${SYNC_GATEWAY_CONFIGS}/sync_gateway_openid_connect_unsigned_cc.json
    Test OpenIdConnect Basic Test  sg_url=${sg_url}  sg_db=${sg_db}  is_admin_port=${False}  expect_signed_id_token=${False}

Test OpenIDConnect Notauthenticated
    [Documentation]
    ...  Simulate a failed authentication and make sure no session is created
    [Tags]  sanity  syncgateway  oidc
    Reset Cluster  ${SYNC_GATEWAY_CONFIGS}/sync_gateway_openid_connect_cc.json
    Test OpenIDConnect Notauthenticated  sg_url=${sg_url}  sg_db=${sg_db}

Test OpenIDConnect No Session
    [Documentation]
    ...  Authenticate with a test openid provider that is configured to NOT add a Set-Cookie header
    [Tags]   sanity  syncgateway  oidc
    Reset Cluster  ${SYNC_GATEWAY_CONFIGS}/sync_gateway_openid_connect_cc.json
    Test OpenIDConnect No Session  sg_url=${sg_url}  sg_db=${sg_db}

Test OpenIDConnect Oidc Challenge Invalid Provider Name
    [Documentation]
    ...  Authenticate with a non-default provider using an invalid provider name and expect an error
    [Tags]   sanity  syncgateway  oidc
    Reset Cluster  ${SYNC_GATEWAY_CONFIGS}/sync_gateway_openid_connect_cc.json
    Test OpenIDConnect Oidc Challenge Invalid Provider Name  sg_url=${sg_url}  sg_db=${sg_db}

Test OpenIDConnect Expired Token
    [Documentation]
    ...  Authenticate and create an ID token that only lasts for 5 seconds, wait 10 seconds
    ...  and make sure the token is rejected
    [Tags]   sanity  syncgateway  oidc
    Reset Cluster  ${SYNC_GATEWAY_CONFIGS}/sync_gateway_openid_connect_cc.json
    Test OpenIDConnect Expired Token  sg_url=${sg_url}  sg_db=${sg_db}


Test OpenIDConnect Negative Token Expiry
    [Documentation]
    ...  Create a token with a negative expiry time and expect that authentication
    ...  is not possible
    [Tags]   sanity  syncgateway  oidc
    Reset Cluster  ${SYNC_GATEWAY_CONFIGS}/sync_gateway_openid_connect_cc.json
    Test OpenIDConnect Negative Token Expiry  sg_url=${sg_url}  sg_db=${sg_db}


Test OpenIDConnect Garbage Token
    [Documentation]
    ...  Send a garbage/invalid token and make sure it cannot be used
    [Tags]   sanity  syncgateway  oidc
    Test OpenIDConnect Garbage Token  sg_url=${sg_url}  sg_db=${sg_db}

Test OpenIDConnect Invalid Scope
    [Documentation]
    ...  Try to discover the authenticate endpoint URL with a test provider that has an
    ...  invalid scope, and expect an error
    [Tags]   sanity  syncgateway  oidc
    Reset Cluster  ${SYNC_GATEWAY_CONFIGS}/sync_gateway_openid_connect_cc.json
    Test OpenIDConnect Invalid Scope  sg_url=${sg_url}  sg_db=${sg_db}

Test OpenIDConnect Small Scope
    [Documentation]
    ...  Use the smallest OpenIDConnect scope possible, and make sure
    ...  certain claims like "email" are not present in the JWT returned
    [Tags]   sanity  syncgateway  oidc
    Reset Cluster  ${SYNC_GATEWAY_CONFIGS}/sync_gateway_openid_connect_cc.json
    Test OpenIDConnect Small Scope  sg_url=${sg_url}  sg_db=${sg_db}

Test OpenIDConnect Large Scope
    [Documentation]
    ...  Authenticate against a test provider config that only has a larger scope than the default,
    ...  and make sure things like the nickname are returned in the jwt token returned back
    [Tags]   sanity  syncgateway  oidc
    Reset Cluster  ${SYNC_GATEWAY_CONFIGS}/sync_gateway_openid_connect_cc.json
    Test OpenIDConnect Large Scope  sg_url=${sg_url}  sg_db=${sg_db}

Test OpenIDConnect Public Session Endpoint
    [Documentation]
    ...  Create a new session from the OpenID Connect token returned by hitting
    ...  the public _session endpoint and make sure the response contains the Set-Cookie header.
    [Tags]   sanity  syncgateway  oidc
    Reset Cluster  ${SYNC_GATEWAY_CONFIGS}/sync_gateway_openid_connect_cc.json
    Test OpenIDConnect Public Session Endpoint  sg_url=${sg_url}  sg_db=${sg_db}

*** Keywords ***
Setup Test

    # Provisioning happens in the __init__.robot file

    Log  Using cluster %{CLUSTER_CONFIG}  console=True
    Set Environment Variable  CLUSTER_CONFIG  ${CLUSTER_CONFIGS}/1sg_1cbs

    ${cluster_hosts} =  Get Cluster Topology  %{CLUSTER_CONFIG}

    Set Test Variable  ${sg_url}        ${cluster_hosts["sync_gateways"][0]["public"]}
    Set Test Variable  ${sg_url_admin}  ${cluster_hosts["sync_gateways"][0]["admin"]}

    Set Test Variable  ${sg_db}  db

Teardown Test
    Log  Tearing down test ...  console=True
    List Connections
    Run Keyword If Test Failed  Fetch And Analyze Logs  ${TEST_NAME}
