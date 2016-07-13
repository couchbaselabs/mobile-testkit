*** Settings ***
Documentation    Common Variables / Keywords

Library     Process
Library     ${KEYWORDS}/ClusterKeywords.py

*** Variables ***
${LIBRARIES}                libraries
${KEYWORDS}                 keywords

${KEYWORDS}                 keywords
${RESULTS}                  results
${RESOURCES}                resources
${ARTIFACTS}                ${RESOURCES}/artifacts
${SYNC_GATEWAY_CONFIGS}     ${RESOURCES}/sync_gateway_configs
${CLUSTER_CONFIGS}          ${RESOURCES}/cluster_configs


# Suite paths
${SYNC_GATEWAY_SUITE_FUNCTIONAL}  testsuites/syncgateway/functional

*** Keywords ***

Clean Cluster
    Log                         Cluster Config: %{CLUSTER_CONFIG}
    ${result} =  Run Process  python  ${LIBRARIES}/provision/clean_cluster.py
    Log  ${result.stderr}
    Log  ${result.stdout}
    Should Be Equal As Integers  ${result.rc}  0

# LiteServ Keywords
Install LiteServ
    [Documentation]   Bootstraps any installation (deploying apps, etc)
    ...  The LiteServ binaries are located in deps/.
    [Arguments]  ${platform}  ${version}  ${storage_engine}
    [Timeout]       2 minutes
    Run Keyword If  "${platform}" == "android"  Install Apk  ${version}  ELSE  Log  No install need

Start LiteServ
    [Documentation]   Starts LiteServ for a specific platform.
    ...  The LiteServ binaries are located in deps/.
    [Arguments]  ${platform}  ${version}  ${host}  ${port}  ${storage_engine}
    [Timeout]       1 minute

    ${ls_url} =  Run Keyword If  "${platform}" == "macosx"   Start MacOSX LiteServ    version=${version}  host=${host}  port=${port}  storage_engine=${storage_engine}
    ${ls_url} =  Run Keyword If  "${platform}" == "android"  Start Android LiteServ                       host=${host}  port=${port}  storage_engine=${storage_engine}
    ${ls_url} =  Run Keyword If  "${platform}" == "net"      Start Net LiteServ       version=${version}  host=${host}  port=${port}  storage_engine=${storage_engine}

    ${ls_url} =  Verify LiteServ Launched  host=${host}  port=${port}  version_build=${version}
    [return]  ${ls_url}

Shutdown LiteServ
    [Documentation]   Stops LiteServ for a specific platform.
    ...  The LiteServ binaries are located in
    [Arguments]  ${platform}
    [Timeout]       1 minute
    Run Keyword If  "${platform}" == "macosx"   Shutdown MacOSX LiteServ
    Run Keyword If  "${platform}" == "android"  Shutdown Android LiteServ
    Run Keyword If  "${platform}" == "net"      Shutdown Net LiteServ

Start MacOSX LiteServ
    [Documentation]   Starts LiteServ for MacOSX platform.
    ...  The LiteServ binaries are located in deps/.
    [Arguments]  ${version}  ${host}  ${port}  ${storage_engine}
    [Timeout]       1 minute

    ${binary_path} =  Get LiteServ Binary Path  platform=macosx  version=${version}

     # Get a list of db names / password for running LiteServ with encrypted databases
    @{db_name_passwords} =  Run Keyword If  '${storage_engine}' == 'ForestDB+Encryption' or '${storage_engine}' == 'SQLCipher'
    ...  Build Name Passwords For Registered Dbs  platform=macosx

    Run Keyword If  '${storage_engine}' == 'ForestDB+Encryption' or '${storage_engine}' == 'SQLCipher'
    ...  Log  Using ENCRYPTION: ${db_name_passwords}  console=yes

    Run Keyword If  '${storage_engine}' == 'ForestDB+Encryption'
    ...  Start Process  ${binary_path}
    ...    --port  ${port}
    ...    --storage  ForestDB
    ...    --dir  ${RESULTS}/dbs
    ...    @{db_name_passwords}
    ...    -Log  YES  -LogSync  YES  -LogCBLRouter  YES  -LogSyncVerbose  YES  -LogRemoteRequest  YES
    ...    alias=liteserv-ios
    ...    shell=True
    ...    stdout=${RESULTS}/logs/${TEST_NAME}-macosx-liteserv-stdout.log
    ...    stderr=${RESULTS}/logs/${TEST_NAME}-macosx-liteserv-stderr.log
    ...  ELSE IF  '${storage_engine}' == 'SQLCipher'
    ...  Start Process  ${binary_path}
    ...    --port  ${port}
    ...    --storage  SQLite
    ...    --dir  ${RESULTS}/dbs
    ...    @{db_name_passwords}
    ...    -Log  YES  -LogSync  YES  -LogCBLRouter  YES  -LogSyncVerbose  YES  -LogRemoteRequest  YES
    ...    alias=liteserv-ios
    ...    shell=True
    ...    stdout=${RESULTS}/logs/${TEST_NAME}-macosx-liteserv-stdout.log
    ...    stderr=${RESULTS}/logs/${TEST_NAME}-macosx-liteserv-stderr.log
    ...  ELSE
    ...  Start Process  ${binary_path}
    ...    --port  ${port}
    ...    --storage  ${storage_engine}
    ...    --dir  ${RESULTS}/dbs
    ...    -Log  YES  -LogSync  YES  -LogCBLRouter  YES  -LogSyncVerbose  YES  -LogRemoteRequest  YES
    ...    alias=liteserv-ios
    ...    shell=True
    ...    stdout=${RESULTS}/logs/${TEST_NAME}-macosx-liteserv-stdout.log
    ...    stderr=${RESULTS}/logs/${TEST_NAME}-macosx-liteserv-stderr.log

    Process Should Be Running   handle=liteserv-ios

Start Android LiteServ
    [Documentation]   Starts LiteServ Activity on Running on port.
    ...  The LiteServ binaries are located in deps/.
    [Arguments]  ${host}  ${port}  ${storage_engine}
    [Timeout]       1 minute

    # Clear logcat
    Run Process  adb  logcat  -c

    Start Process   adb  logcat
    ...             alias=adb-logcat
    ...             stdout=${RESULTS}/logs/${TEST_NAME}-android-logcat-stdout.log
    ...             stderr=${RESULTS}/logs/${TEST_NAME}-android-logcat-stderr.log
    Process Should Be Running   handle=adb-logcat

    Launch Activity  ${port}  ${storage_engine}

Start Net LiteServ
    [Documentation]   Starts a .net LiteServ on a port.
    ...  The LiteServ binaries are located in deps/.
    [Arguments]  ${version}  ${host}  ${port}  ${storage_engine}
    [Timeout]       1 minute
    ${binary_path} =  Get LiteServ Binary Path  platform=net  version=${version}

    # Get a list of db names / password for running LiteServ with encrypted databases
    @{db_name_passwords} =  Run Keyword If  '${storage_engine}' == 'ForestDB+Encryption' or '${storage_engine}' == 'SQLCipher'
    ...  Build Name Passwords For Registered Dbs  platform=net

    Run Keyword If  '${storage_engine}' == 'ForestDB+Encryption' or '${storage_engine}' == 'SQLCipher'
    ...  Log  Using ENCRYPTION: ${db_name_passwords}  console=yes

    Run Keyword If  '${storage_engine}' == 'ForestDB+Encryption'
    ...  Start Process  mono  ${binary_path}
    ...    --port  ${port}
    ...    --storage  ForestDB
    ...    --dir  ${RESULTS}/dbs
    ...    @{db_name_passwords}
    ...    alias=liteserv-net
    ...    shell=True
    ...    stdout=${RESULTS}/logs/${TEST_NAME}-net-liteserv-stdout.log
    ...    stderr=${RESULTS}/logs/${TEST_NAME}-net-liteserv-stderr.log
    ...  ELSE IF  '${storage_engine}' == 'SQLCipher'
    ...  Start Process  mono  ${binary_path}
    ...    --port  ${port}
    ...    --storage  SQLite
    ...    --dir  ${RESULTS}/dbs
    ...    @{db_name_passwords}
    ...    alias=liteserv-net
    ...    shell=True
    ...    stdout=${RESULTS}/logs/${TEST_NAME}-net-liteserv-stdout.log
    ...    stderr=${RESULTS}/logs/${TEST_NAME}-net-liteserv-stderr.log
    ...  ELSE
    ...  Start Process  mono  ${binary_path}
    ...    --port  ${port}
    ...    --storage  ${storage_engine}
    ...    --dir  ${RESULTS}/dbs
    ...    alias=liteserv-net
    ...    shell=True
    ...    stdout=${RESULTS}/logs/${TEST_NAME}-net-liteserv-stdout.log
    ...    stderr=${RESULTS}/logs/${TEST_NAME}-net-liteserv-stderr.log

    Process Should Be Running   handle=liteserv-net

Shutdown MacOSX LiteServ
    [Documentation]   Stops Mac OSX LiteServ.
    ...  The LiteServ binaries are located in deps/binaries.
    [Timeout]       1 minute
    Terminate Process          handle=liteserv-ios
    Process Should Be Stopped  handle=liteserv-ios

Shutdown Android LiteServ
    [Documentation]   Stops Android LiteServ Activity.
    ...  The LiteServ binaries are located in deps/binaries.
    [Timeout]       1 minute
    Stop Activity
    Terminate Process          handle=adb-logcat
    Process Should Be Stopped  handle=adb-logcat


Shutdown Net LiteServ
    [Documentation]   Stops Net LiteServ.
    ...  The LiteServ binaries are located in deps/binaries.
    [Timeout]       1 minute
    Terminate Process          handle=liteserv-net
    Process Should Be Stopped  handle=liteserv-net
