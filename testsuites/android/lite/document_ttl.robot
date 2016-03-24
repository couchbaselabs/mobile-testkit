*** Settings ***
Resource    resources/common.robot

Test Setup      Setup
Test Teardown   Teardown

# Tags      ios      android     net

*** Variables ***


*** Test Cases ***
Verify TTL Docs Purged
    # Implementation option 1: pyobjc, jython, ironpython
    # Implementation option 2: rest API proxy (RPC), SOAP listener, http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#remote-protocol
    # Implementation option 3: Native app for each platform
    Create Client Db
    Create Client Docs with ttl
    Wait ttl + 100ms
    Check client docs purged


*** Keywords ***
Setup
   Log To Console      Setting up ...


Teardown
   Log To Console  Tearing down ...
   Terminate All Processes
