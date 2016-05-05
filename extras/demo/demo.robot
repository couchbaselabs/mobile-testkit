*** Settings ***
Documentation     A test suite containing functional tests of the Listener's
...               replication with sync_gateway

Library           CustomLibrary

Suite Setup       Setup Suite
Suite Teardown    Teardown Suite

Test Setup        Setup Test
Test Teardown     Teardown Test

*** Variables ***
# Can be passed in at runtime
${CUSTOM_LOG_MESSAGE}  custom log message

*** Test Cases ***
Simple Test
    [Documentation]  Logs Test and then will log a custom message.
    [Tags]           sanity     simple
    [Timeout]        5 minutes
    Log  Test
    Custom Log  ${CUSTOM_LOG_MESSAGE}

*** Keywords ***
Setup Suite
    [Documentation]  Sets up a test suite.
    Log  Setting up Suite

Teardown Suite
    [Documentation]  Tears up a test suite.
    Log  Tearing Down Suite

Setup Test
    [Documentation]  Sets up a tests.
    Log  Setting up test

Teardown Test
    [Documentation]  Teardown a test.
    Log  Tearing down test







