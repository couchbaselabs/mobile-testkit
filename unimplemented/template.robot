*** Settings ***
Documentation     A test suite containing functional tests of the Listener's
...               REST APIs for Design Documents.
...
...               These tests require JavaScript code to be passed in as arguments.
...               For cases where no code is required, like map-only views, just
...               pass in the ${EMPTY} specifier.
...
...               Note also the the use of the pipe-delimiter is not required,
...               but it is recommended on lines where JavaScript is being passed
...               in as using 4 spaces is less readable.
Resource          resources/common.robot
Resource          ./defines.robot
Library           Listener
Suite Setup       Start Listener     ${HOSTNAME}
Test Setup        Create Database    ${DBNAME}
Suite Teardown    Shutdown Listener
Test Timeout      30 seconds     The default test timeout elapsed before the test completed.

*** Test Cases ***
Test Concurrent View Queries Against Stale Index
    Documentation    Creates a JS view and a bunch of test documents. It then
    ...              issues a view query which begins updating the index. While
    ...              the index is being processed, a new view query is issued
    ...              in an attempt to cause concurrent index updates.
    [Tags]           Sanity    CBL    Listener    Views    ObjC    .NET    Java
    [Timeout]        1 minute
  | Create Design Document    test | testDocs | function (doc) { if (doc.test) { emit(doc.test); }} | function (doc) { if (doc.test) { emit(doc.test); }}
    Create Test Documents     10000
    ${query} =       Create View Query        test    testDocs
    Get              ${query}    Async
    Wait             200ms
    ${query2} =      Create View Query        test    testDocs
    Get              ${query2}
    Wait For         ${query}    ${query2}
    Status Equals    ${query}     200
    Status Equals    ${query2}    200
    Ensure No Duplicate Rows In ${query}
    Ensure No Duplicate Rows In ${query2}

*** Keywords ***
Create Design Doc
    Documentation    Creates a new design doc via the REST API.
    [Arguments]      ${DESIGNDOC_NAME}    ${VIEW_NAME}    ${VIEW1_NAME}    ${MAP_FUNCTION}    ${REDUCE_FUNCTION}
    ${request} =     Create Request For Design Doc Named    ${DESIGNDOC_NAME}
    Add View         ${request}    ${VIEW1_NAME}    ${MAP_FUNCTION}    ${REDUCE_FUNCTION}
    Post             ${request}
    Status Equals    ${request}    201
