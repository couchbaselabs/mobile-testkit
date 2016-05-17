*** Settings ***
Documentation     A test suite containing functional tests of the Listener's
...               replication with sync_gateway using two different flavors of the library
...               on two different platforms

Resource          resources/common.robot
Library           DebugLibrary
Library           Process

Library           ${KEYWORDS}/Async.py
Library           ${KEYWORDS}/MobileRestClient.py

*** !!! Instead of this, the platform should be passed in the keyword I think !!! ***
Library           ${KEYWORDS}/LiteServ.py
...                 platform=${PLATFORM}
...                 version_build=${LITESERV_VERSION}

# Passed in at runtime
Suite Setup       Setup Suite

Test Setup        Setup Test
Test Teardown     Teardown Test

*** Variables ***
${SYNC_GATEWAY_CONFIG}  ${SYNC_GATEWAY_CONFIGS}/walrus.json

*** Test Cases ***
Replication with multiple client dbs and single sync_gateway db
    [Documentation]
    [Tags]           sanity     listener    ${PLATFORM}    syncgateway
    [Timeout]        5 minutes

    Log  Using LiteServ .NET: ${ls_url_net}
    Log  Using LiteServ Android: ${ls_url_droid}

    ${ls_db1} =  Create Database  url=${ls_url_net}  name=ls_db1
    ${ls_db2} =  Create Database  url=${ls_url_droid}  name=ls_db2

    # Setup continuous push / pull replication from ls_db1 to sg_db
    Start Replication
    ...  url=${ls_url_net}
    ...  continuous=${True}
    ...  from_db=${ls_db1}
    ...  to_url=${ls_url_droid}  to_db=${ls_db2}

    Start Replication
    ...  url=${ls_url_net}
    ...  continuous=${True}
    ...  from_url=${ls_url_droid}  from_db=${ls_db2}
    ...  to_db=${ls_db1}

    # Setup continuous push / pull replication from ls_db2 to sg_db
    Start Replication
    ...  url=${ls_url_droid}
    ...  continuous=${True}
    ...  from_db=${ls_db2}
    ...  to_url=${ls_url_net}  to_db=${ls_db1}

    Start Replication
    ...  url=${ls_url_droid}
    ...  continuous=${True}
    ...  from_url=${ls_url_net}  from_db=${ls_db1}
    ...  to_db=${ls_db2}

    ${ls_db1_docs} =  Add Docs  url=${ls_url_net}  db=${ls_db1}  number=${500}  id_prefix=test_ls_db1
    ${ls_db2_docs} =  Add Docs  url=${ls_url_droid}  db=${ls_db2}  number=${500}  id_prefix=test_ls_db2

    @{ls_db1_db2_docs} =  Create List  ${ls_db1_docs}  ${ls_db2_docs}

    Verify Docs Present  url=${ls_url_net}       db=${ls_db1}  expected_docs=@{ls_db1_db2_docs}
    Verify Docs Present  url=${ls_url_droid}       db=${ls_db2}  expected_docs=@{ls_db1_db2_docs}

    Verify Docs In Changes  url=${ls_url_net}      db=${ls_db1}  expected_docs=@{ls_db1_db2_docs}
    Verify Docs In Changes  url=${ls_url_droid}     db=${ls_db2}  expected_docs=@{ls_db1_db2_docs}


*** Keywords ***
Setup Suite
    [Documentation]  Download, install, and launch LiteServ.
    Download LiteServ
    ...  platform=${NET_PLATFORM}
    Download LiteServ
    ...  platform=${DROID_PLATFORM}
    Install LiteServ
    ...  platform=${NET_PLATFORM}
    Install Android Liteserv
    ...  platform=${DROID_PLATFORM}

Setup Test
    ${ls_url_net} =  Start LiteServ  host=${LITESERV_NET_HOST}  port=${LITESERV_NET_PORT} platform=${NET_PLATFORM}
    ${ls_url_droid} =  Start LiteServ host=${LITESERV_DROID_HOST}  port=${LITESERV_DROID_PORT} platform=${DROID_PLATFORM}

    Set Test Variable  ${ls_url_net}
    Set Test Variable  ${ls_url_droid}

Teardown Test
    Delete Databases  ${ls_url_net}
    Delete Databases  ${ls_url_droid}
    Shutdown LiteServ
    ...  platform=${NET_PLATFORM}
    Shutdown LiteServ
    ...  platform=${DROID_PLATFORM}







