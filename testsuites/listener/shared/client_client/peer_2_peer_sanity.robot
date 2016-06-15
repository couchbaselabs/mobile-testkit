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

    Log  Using LiteServ: ${ls_url_one}
    Log  Using LiteServ: ${ls_url_two}

    ${ls_db1} =  Create Database  url=${ls_url_one}  name=ls_db1
    ${ls_db2} =  Create Database  url=${ls_url_two}  name=ls_db2

    # Setup continuous push / pull replication from ls_db1 to sg_db
    Start Replication
    ...  url=${ls_url_one}
    ...  continuous=${True}
    ...  from_db=${ls_db1}
    ...  to_url=${ls_url_two}  to_db=${ls_db2}

    Start Replication
    ...  url=${ls_url_one}
    ...  continuous=${True}
    ...  from_url=${ls_url_two}  from_db=${ls_db2}
    ...  to_db=${ls_db1}

    # Setup continuous push / pull replication from ls_db2 to sg_db
    Start Replication
    ...  url=${ls_url_two}
    ...  continuous=${True}
    ...  from_db=${ls_db2}
    ...  to_url=${ls_url_one}  to_db=${ls_db1}

    Start Replication
    ...  url=${ls_url_two}
    ...  continuous=${True}
    ...  from_url=${ls_url_one}  from_db=${ls_db1}
    ...  to_db=${ls_db2}

    ${ls_db1_docs} =  Add Docs  url=${ls_url_one}  db=${ls_db1}  number=${num_docs}  id_prefix=test_ls_db1
    ${ls_db2_docs} =  Add Docs  url=${ls_url_two}  db=${ls_db2}  number=${num_docs}  id_prefix=test_ls_db2

    @{ls_db1_db2_docs} =  Merge  ${ls_db1_docs}  ${ls_db2_docs}

    Verify Docs Present  url=${ls_url_one}       db=${ls_db1}  expected_docs=@{ls_db1_db2_docs}
    Verify Docs Present  url=${ls_url_two}       db=${ls_db2}  expected_docs=@{ls_db1_db2_docs}

    Verify Docs In Changes  url=${ls_url_one}     db=${ls_db1}  expected_docs=@{ls_db1_db2_docs}
    Verify Docs In Changes  url=${ls_url_two}     db=${ls_db2}  expected_docs=@{ls_db1_db2_docs}


*** Keywords ***
Setup Test

    ${ls_url_one} =  Start LiteServ
    ...  platform=${LITESERV_ONE_PLATFORM}
    ...  version=${LITESERV_ONE_VERSION}
    ...  host=${LITESERV_ONE_HOST}
    ...  port=${LITESERV_ONE_PORT}
    ...  storage_engine=${LITESERV_ONE_STORAGE_ENGINE}

     ${ls_url_two} =  Start LiteServ
    ...  platform=${LITESERV_TWO_PLATFORM}
    ...  version=${LITESERV_TWO_VERSION}
    ...  host=${LITESERV_TWO_HOST}
    ...  port=${LITESERV_TWO_PORT}
    ...  storage_engine=${LITESERV_TWO_STORAGE_ENGINE}

    ${num_docs} =  Set Variable If
    ...  "${PROFILE}" == "sanity"   ${10}
    ...  "${PROFILE}" == "nightly"  ${500}
    ...  "${PROFILE}" == "release"  ${10000}
    Set Test Variable  ${num_docs}

    Set Test Variable  ${ls_url_one}
    Set Test Variable  ${ls_url_two}

Teardown Test
    Delete Databases  ${ls_url_one}
    Delete Databases  ${ls_url_two}
    Shutdown LiteServ  platform=${LITESERV_ONE_PLATFORM}
    Shutdown LiteServ  platform=${LITESERV_TWO_PLATFORM}







