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
    [Arguments]  ${platform}  ${version}  ${storage_type}
    [Timeout]       2 minutes
    Run Keyword If  "${platform}" == "android"  Install Apk  ${version}  ${storage_type}  ELSE  Log  No install need

Start LiteServ
    [Documentation]   Starts LiteServ for a specific platform.
    ...  The LiteServ binaries are located in deps/.
    [Arguments]  ${platform}  ${version}  ${host}  ${port}  ${storage_type}
    [Timeout]       1 minute

    ${ls_url} =  Run Keyword If  "${platform}" == "macosx"   Start MacOSX LiteServ      version=${version}  host=${host}  port=${port}  storage_type=${storage_type}
    ${ls_url} =  Run Keyword If  "${platform}" == "android"  Start Android LiteServ                         host=${host}  port=${port}
    ${ls_url} =  Run Keyword If  "${platform}" == "net"      Start Net ListenerConsole  version=${version}  host=${host}  port=${port}  storage_type=${storage_type}

    ${ls_url} =  Verify LiteServ Launched  host=${host}  port=${port}  version_build=${version}
    [return]  ${ls_url}

Start MacOSX LiteServ
    [Documentation]   Starts LiteServ for MacOSX platform.
    ...  The LiteServ binaries are located in deps/.
    [Arguments]  ${version}  ${host}  ${port}  ${storage_type}
    #[Timeout]       1 minute
    ${binary_path} =  Get LiteServ Binary Path  platform=macosx  version=${version}
    Start Process   ${binary_path}  --port  ${port}  --storage  ${storage_type}
    ...             -Log  YES  -LogSync  YES  -LogCBLRouter  YES  -LogSyncVerbose  YES  -LogRemoteRequest  YES
    ...             alias=liteserv-ios
    ...             shell=True
    ...             stdout=${RESULTS}/${TEST_NAME}-macosx-liteserv-stdout.log
    ...             stderr=${RESULTS}/${TEST_NAME}-macosx-liteserv-stderr.log
    Process Should Be Running   handle=liteserv-ios

Start Android LiteServ
    [Documentation]   Starts LiteServ Activity on Running on port.
    ...  The LiteServ binaries are located in deps/.
    [Arguments]  ${host}  ${port}
    [Timeout]       1 minute

    Start Process   adb  logcat
    ...             alias=adb-logcat
    ...             stdout=${RESULTS}/${TEST_NAME}-android-logcat-stdout.log
    ...             stderr=${RESULTS}/${TEST_NAME}-android-logcat-stderr.log
    Process Should Be Running   handle=adb-logcat

    Launch Activity  ${port}

Start Net ListenerConsole
    [Documentation]   Starts a .net ListenerConsole on a port.
    [Arguments]  ${version}  ${host}  ${port}  ${storage_type}
    [Timeout]       1 minute
    ${binary_path} =  Get LiteServ Binary Path  platform=net  version=${version}
    Start Mono Process  ${binary_path}  ${port}

Shutdown LiteServ
    [Documentation]   Stops LiteServ for a specific platform.
    ...  The LiteServ binaries are located in
    [Arguments]  ${platform}
    [Timeout]       1 minute
    Run Keyword If  "${platform}" == "macosx"  Shutdown MacOSX LiteServ
    Run Keyword If  "${platform}" == "android"  Shutdown Android LiteServ
    Run Keyword If  "${platform}" == "net"  Shutdown Net ListenerConsole

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


Shutdown Net ListenerConsole
    [Documentation]   Kills Net Listener Console Process.
    ...  The LiteServ binaries are located in deps/binaries.
    [Timeout]       1 minute
    Kill Mono Process
