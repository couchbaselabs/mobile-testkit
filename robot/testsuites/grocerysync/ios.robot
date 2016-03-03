*** Settings ***

Library         Process
Library         AppiumLibrary
Library         DebugLibrary
Library         libraries/SyncGatewayUtils.py

Test Setup      Setup
Test Teardown   Teardown

*** Variables ***
${RESOURCES}                resources
${SYNC_GATEWAY}             ${RESOURCES}/sync_gateway/couchbase-sync-gateway/bin/sync_gateway
${SYNC_GATEWAY_CONFIGS}     ${RESOURCES}/sync_gateway_configurations
${SYNC_GATEWAY_VERSION}     1.2.0-79
${EXECUTION_OS}             OSX

*** Test Cases ***

Add Grocery Items
    [Documentation]     Launch Grocery Sync, add docs, and verify they get pushed to sync_gateway
    [Tags]              sync_gateway    grocery_sync    android     nightly

    # Add 3 grocery items
    @{items}            Create List     Item 1  Item 2  Item 3
    Add Items           @{items}

    # Verify 3 docs pushed to sync_gateway
    ${doc_number} =     Get Sync Gateway Document Count      grocery-sync
    Should Be Equal As Integers     ${doc_number}   3

    # Add 3 more grocery items
    @{items}            Create List     Item 4  Item 5  Item 6
    Add Items           @{items}

    # Verify 6 docs pushed to sync_gateway
    ${doc_number} =     Get Sync Gateway Document Count      grocery-sync
    Should Be Equal As Integers     ${doc_number}   6

*** Keywords ***

Add Items
    [Arguments]     @{items}

    : FOR   ${item}     IN      @{items}
    \   Tap             class=UIATextField
    \   Input Text      class=UIATextField     ${item}
    \   Press Enter

    # Wait for docs to push
    Sleep               2s

Setup
    Install Local Sync Gateway  ${SYNC_GATEWAY_VERSION}    ${EXECUTION_OS}
    Start Process               ${SYNC_GATEWAY}    ${SYNC_GATEWAY_CONFIGS}/grocery_sync_conf.json    alias=sync_gateway
    Process Should Be Running   sync_gateway    alias=sync_gateway

    Start Process               appium    alias=appium
    Process Should Be Running   appium    alias=appium

    # Wait for service to be available on port, need something similar to ansible, wait_for
    Sleep                       2s

    # Need to be able to pass ip in here to resolve connecting to sync_gateway
    Open Application            http://localhost:4723/wd/hub    platformName=iOS    deviceName=iPhone 6s    app=%{GROCERY_SYNC_APP}

Teardown
    Close Application
    Terminate All Processes         kill=True
    Uninstall Local Sync Gateway    ${EXECUTION_OS}

Press Enter
    Hide Keyboard       key_name=Done