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
    Add Items
    ${doc_number} =     Get Sync Gateway Document Count      grocery-sync
    Should Be Equal As Integers     ${doc_number}   3

*** Keywords ***

Add Items
    Tap                 id=com.couchbase.grocerysync:id/addItemEditText
    Input Text          id=com.couchbase.grocerysync:id/addItemEditText     Item 1
    Press Enter
    Tap                 id=com.couchbase.grocerysync:id/addItemEditText
    Input Text          id=com.couchbase.grocerysync:id/addItemEditText     Item 2
    Press Enter
    Tap                 id=com.couchbase.grocerysync:id/addItemEditText
    Input Text          id=com.couchbase.grocerysync:id/addItemEditText     Item 3
    Press Enter

    # Wait for docs to push
    Sleep               2s

Setup
#    Start Process               emulator    @Nexus_5_API_23_x86
#    Wait For Emulator           emulator-5554

    Install Local Sync Gateway  ${SYNC_GATEWAY_VERSION}    ${EXECUTION_OS}
    Start Process               ${SYNC_GATEWAY}    ${SYNC_GATEWAY_CONFIGS}/grocery_sync_conf.json    alias=sync_gateway
    Process Should Be Running   sync_gateway    alias=sync_gateway

    Start Process               appium    alias=appium
    Process Should Be Running   appium    alias=appium

    # Wait for service to be available on port, need something similar to ansible, wait_for
    Sleep                       2s

    # Need to be able to pass ip in here to resolve connecting to sync_gateway
    Open Application            http://localhost:4723/wd/hub    platformName=Android    deviceName=emulator-5554    app=%{GROCERY_SYNC_APK}

Teardown
    Close Application
    Terminate All Processes         kill=True
    Uninstall Local Sync Gateway    ${EXECUTION_OS}

Press Enter
    Press Keycode       66