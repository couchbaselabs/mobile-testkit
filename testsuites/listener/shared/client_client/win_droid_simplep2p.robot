*** Settings ***
Documentation     A test suite containing functional tests of the Listener's
...               replication with sync_gateway using two different flavors of the library
...               on two different platforms

Resource          resources/common.robot
Library           DebugLibrary
Library           Process

Library           ${KEYWORDS}/Async.py
Library           ${KEYWORDS}/MobileRestClient.py

Library           ${KEYWORDS}/LiteServ.py

Test Setup        Setup Test
Test Teardown     Teardown Test

*** Variables ***

*** Test Cases ***
Replication with multiple client dbs and single sync_gateway db
    [Documentation]
    [Tags]           sanity     listener    ${LITESERV_ONE_PLATFORM}    ${LITESERV_TWO_PLATFORM}
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
Setup Test

    ${ls_url_net} =  Start LiteServ
    ...  platform=${LITESERV_ONE_PLATFORM}
    ...  version=${LITESERV_ONE_VERSION}
    ...  host=${LITESERV_ONE_HOST}
    ...  port=${LITESERV_ONE_PORT}

     ${ls_url_droid} =  Start LiteServ
    ...  platform=${LITESERV_TWO_PLATFORM}
    ...  version=${LITESERV_TWO_VERSION}
    ...  host=${LITESERV_TWO_HOST}
    ...  port=${LITESERV_TWO_PORT}

    Set Test Variable  ${ls_url_net}
    Set Test Variable  ${ls_url_droid}

Teardown Test
    Delete Databases  ${ls_url_net}
    Delete Databases  ${ls_url_droid}
    Shutdown LiteServ  platform=${LITESERV_ONE_PLATFORM}
    Shutdown LiteServ  platform=${LITESERV_TWO_PLATFORM}







