# robot -v PLATFORMS:CentOS,Windows,MacOSX -v SYNC_GATEWAY_VERSION:1.2.0-79 sgcollectinfo.robot

*** Settings ***
Resource    resources/common.robot

Library     sgcollectinfo.py

Test Setup      Setup
Test Teardown   Teardown

# Tags      CentOS      Windows     MacOSX

*** Variables ***
${SYNC_GATEWAY_VERSION}
${PLATFORMS}
${OUTPUT_FILE}  sginfo.zip

*** Test Cases ***
Collect Logs
   Start Local Sync Gateway            ${SYNC_GATEWAY_CONFIGS}/sample.json
   Run Process     sgcollectinfo.py    ${OUTPUT_FILE}
   Validate Logs

Check No Arguement
   Start Local Sync Gateway            ${SYNC_GATEWAY_CONFIGS}/sample.json
   ${result} =     Run Process         python  sgcollect_info.py
   Should Contain  ${result.stderr}    error: incorrect number of arguments. Expecting filename to collect diagnostics into
   Should Be True  ${result.rc} > 0

Sync Gateway Not Started
   ${result} =     Run Process    python  sgcollect_info.py   ${OUTPUT_FILE}


*** Keywords ***
Setup
   Log To Console      Setting up ...

Install Local Sync Gateway
   [Arguements]    ${platform}

Teardown
   Log To Console  Tearing down ...
   Terminate All Processes


# Usage: sgcollect_info.py [options] output_file.zip
# - Linux/Windows/OSX:
#     sgcollect_info.py output_file.zip
#     sgcollect_info.py -v output_file.zip
# sgcollect_info.py: error: incorrect number of arguments. Expecting filename to collect diagnostics into
# Test scenarios:
# Panic in sync gateway:
# run sgcollect info on with sync gateway not running
# install sync gateway with non root username. Run sgcollectinfo