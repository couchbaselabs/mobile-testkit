*** Settings ***
Resource        resources/Paths.robot

Library         Process
Library         AppiumLibrary
Library         DebugLibrary
Library         libraries/SyncGatewayUtils.py

Test Setup      Setup
Test Teardown   Teardown

*** Variables ***

# By default run iOS, use `robot -v PLATFORM:Android grocerysync.robot` to run android
${PLATFORM}                 iOS
${SYNC_GATEWAY}             ${ARTIFACTS}/sync_gateway/couchbase-sync-gateway/bin/sync_gateway
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
    \   Run Keyword If  '${PLATFORM}' == 'Android'  Tap             id=com.couchbase.grocerysync:id/addItemEditText
    \   Run Keyword If  '${PLATFORM}' == 'Android'  Input Text      id=com.couchbase.grocerysync:id/addItemEditText     ${item}
    \   Run Keyword If  '${PLATFORM}' == 'iOS'      Tap             class=UIATextField
    \   Run Keyword If  '${PLATFORM}' == 'iOS'      Input Text      class=UIATextField     ${item}
    \   Press Enter

    # Wait for docs to push
    Sleep               2s

Setup
    # TODO Wait for emulator to start. Need better way to do this
    Run Keyword If  '${PLATFORM}' == 'Android'   Start Process               emulator    @Nexus_5_API_23_x86
    Run Keyword If  '${PLATFORM}' == 'Android'   Sleep                       30s

    Log To Console              ${PLATFORM}

    # Currently assumes Mac OSX install
    Install Local Sync Gateway  ${SYNC_GATEWAY_VERSION}

    Start Process               ${SYNC_GATEWAY}    ${SYNC_GATEWAY_CONFIGS}/grocery_sync_conf.json    alias=sync_gateway
    Process Should Be Running   sync_gateway    alias=sync_gateway

    Start Process               appium    alias=appium
    Process Should Be Running   appium    alias=appium

    # TODO Wait for service to be available on port, need something similar to ansible, wait_for
    Sleep                       5s

    # TODO Need to be able to pass ip in here to resolve connecting to sync_gateway
    Run Keyword If  '${PLATFORM}' == 'Android'   Open Application   http://localhost:4723/wd/hub    platformName=Android    deviceName=emulator-5554    app=%{GROCERY_SYNC_APK}
    Run Keyword If  '${PLATFORM}' == 'iOS'       Open Application   http://localhost:4723/wd/hub    platformName=iOS        deviceName=iPhone 6s        app=%{GROCERY_SYNC_APP}

Teardown
    Close Application
    Terminate All Processes         kill=True
    Uninstall Local Sync Gateway    ${EXECUTION_OS}

Press Enter
    Run Keyword If  '${PLATFORM}' == 'Android'    Press Keycode     66
    Run Keyword If  '${PLATFORM}' == 'iOS'        Hide Keyboard     key_name=Done
