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
    Run Keyword If  "${platform}" == "android"  Install Apk  ${version}  ${storage_engine}  ELSE  Log  No install need

Shutdown LiteServ
    [Documentation]   Stops LiteServ for a specific platform.
    ...  The LiteServ binaries are located in
    [Arguments]  ${platform}
    [Timeout]       1 minute
    Run Keyword If  "${platform}" == "macosx"   Shutdown MacOSX LiteServ
    Run Keyword If  "${platform}" == "android"  Shutdown Android LiteServ
    Run Keyword If  "${platform}" == "net"      Shutdown Net LiteServ


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

Shutdown Android LiteServ
    [Documentation]   Stops Android LiteServ Activity.
    ...  The LiteServ binaries are located in deps/binaries.
    [Timeout]       1 minute
    Stop Activity
    Terminate Process          handle=adb-logcat
    Process Should Be Stopped  handle=adb-logcat

