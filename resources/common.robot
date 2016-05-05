*** Settings ***
Documentation    Common Variables / Keywords

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
# Provisioning Keywords
Provision Cluster
    [Arguments]  ${server_version}  ${sync_gateway_version}  ${sync_gateway_config}
    [Documentation]    Installs a Sync Gateway (build) + Sg Accel cluster based on the CLUSTER_CONFIG environment variable
    ...  server_version = the version of Couchbase Server to install (ex. 4.1.0 or 4.5.0-2151)
    ...  sync_gateway_version = the version of Sync Gateway and Sg Accel to install (ex. 1.2.1-4 or commit hash)
    ...  sync_gateway_config = the config to launch the Sync Gateways and Sg Accels with.
    ...  Cluster configs can be found in 'resources/cluster_configs'

    Clean Cluster
    Verfiy No Running Services  %{CLUSTER_CONFIG}

    ${is_binary} =  Sync Gateway Version Is Binary  version=${sync_gateway_version}
    Log  Is Sync Gateway Version Binary: ${is_binary}

    ${result} =  Run Keyword If  ${is_binary}
    ...  Run Process  python  ${LIBRARIES}/provision/provision_cluster.py
    ...  --server-version\=${server_version}
    ...  --sync-gateway-version\=${sync_gateway_version}
    ...  --sync-gateway-config-file\=${sync_gateway_config}
    ...  ELSE
    ...  Run Process  python  ${LIBRARIES}/provision/provision_cluster.py
    ...  --server-version\=${server_version}
    ...  --sync-gateway-commit\=${sync_gateway_version}
    ...  --sync-gateway-config-file\=${sync_gateway_config}

    Log  ${result.stderr}
    Log  ${result.stdout}

    Should Be Equal As Integers  ${result.rc}  0

Clean Cluster
    Log                         Cluster Config: %{CLUSTER_CONFIG}
    ${result} =  Run Process  python  ${LIBRARIES}/provision/clean_cluster.py
    Log  ${result.stderr}
    Log  ${result.stdout}
    Should Be Equal As Integers  ${result.rc}  0

Install Server
    [Arguments]     ${server_version}
    Log                         Cluster Config: %{CLUSTER_CONFIG}
    ${server_arg}               Catenate  SEPARATOR=  --version=          ${server_version}
    ${result} =  Run Process  python  ${LIBRARIES}/provision/install_couchbase_server.py  ${server_arg}
    Log To Console  ${result.stderr}
    Log To Console  ${result.stdout}

Install Sync Gateway
    [Arguments]     ${sync_gateway_version}  ${sync_gateway_config}
    Log                         Cluster Config: %{CLUSTER_CONFIG}
    ${sync_gateway_arg}         Catenate  SEPARATOR=  --version=      ${sync_gateway_version}
    ${sync_gateway_config_arg}  Catenate  SEPARATOR=  --config-file=  ${sync_gateway_config}
    ${result} =  Run Process  python  ${LIBRARIES}/provision/install_sync_gateway.py  ${sync_gateway_arg}  ${sync_gateway_config_arg}
    Log To Console  ${result.stderr}
    Log To Console  ${result.stdout}

# LiteServ Keywords
Install LiteServ
    Run Keyword If  "${PLATFORM}" == "android"  Install Apk  ELSE  Log  No install need

Start LiteServ
    [Documentation]   Starts LiteServ for a specific platform.
    ...  The LiteServ binaries are located in deps/.
    [Arguments]  ${host}  ${port}
    [Timeout]       1 minute

    ${ls_url} =  Run Keyword If  "${PLATFORM}" == "macosx"  Start MacOSX LiteServ  host=${host}  port=${port}
    ${ls_url} =  Run Keyword If  "${PLATFORM}" == "android"  Start Android LiteServ  host=${host}  port=${port}
    ${ls_url} =  Run Keyword If  "${PLATFORM}" == "net"  Start Net ListenerConsole  host=${host}  port=${port}

    ${ls_url} =  Verify LiteServ Launched  host=${host}  port=${port}
    [return]  ${ls_url}

Start MacOSX LiteServ
    [Documentation]   Starts LiteServ for MacOSX platform.
    ...  The LiteServ binaries are located in deps/.
    [Arguments]  ${host}  ${port}
    [Timeout]       1 minute
    ${binary_path} =  Get LiteServ Binary Path
    Start Process   ${binary_path}  --port  ${port}
    ...             -Log  YES  -LogSync  YES  -LogCBLRouter  YES  -LogSyncVerbose  YES  -LogRemoteRequest  YES
    ...             alias=liteserv-ios
    ...             shell=True
    ...             stdout=${RESULTS}/${TEST_NAME}-${PLATFORM}-liteserv-stdout.log
    ...             stderr=${RESULTS}/${TEST_NAME}-${PLATFORM}-liteserv-stderr.log
    Process Should Be Running   handle=liteserv-ios

Start Android LiteServ
    [Documentation]   Starts LiteServ Activity on Running on port.
    ...  The LiteServ binaries are located in deps/.
    [Arguments]  ${host}  ${port}
    [Timeout]       1 minute
    Launch Activity  ${port}

Start Net ListenerConsole
    [Documentation]   Starts a .net ListenerConsole on a port.
    [Arguments]  ${host}  ${port}
    [Timeout]       1 minute
    ${binary_path} =  Get LiteServ Binary Path
    Start Mono Process  ${binary_path}  ${port}

Shutdown LiteServ
    [Documentation]   Stops LiteServ for a specific platform.
    ...  The LiteServ binaries are located in deps/binaries.
    [Timeout]       1 minute
    Run Keyword If  "${PLATFORM}" == "macosx"  Shutdown MacOSX LiteServ
    Run Keyword If  "${PLATFORM}" == "android"  Shutdown Android LiteServ
    Run Keyword If  "${PLATFORM}" == "net"  Shutdown Net ListenerConsole

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

Shutdown Net ListenerConsole
    [Documentation]   Kills Net Listener Console Process.
    ...  The LiteServ binaries are located in deps/binaries.
    [Timeout]       1 minute
    Kill Mono Process

# sync_gateway keywords
Start Sync Gateway
    [Documentation]   Starts sync_gateway with a provided configuration on a host and port(s).
    ...  The sync_gateway binary is located in deps/binaries.
    [Timeout]       1 minute
    [Arguments]  ${config}  ${host}  ${port}  ${admin_port}
    ${binary_path} =  Get Sync Gateway Binary Path
    Start Process   ${binary_path}
    ...             -interface       ${host}:${port}
    ...             -adminInterface  ${host}:${admin_port}
    ...             ${config}
    ...             alias=sync_gateway
    ...             stdout=${RESULTS}/${TEST_NAME}-sync-gateway-stdout.log
    ...             stderr=${RESULTS}/${TEST_NAME}-sync-gateway-stderr.log
    Process Should Be Running   handle=sync_gateway
    ${sg_url} =  Verify Sync Gateway Launched  host=${host}  port=${port}  admin_port=${admin_port}
    [return]    ${sg_url}

Shutdown Sync Gateway
    [Documentation]   Stops sync_gateway running on a local machine.
    ...  The LiteServ binaries are located in deps/binaries.
    [Timeout]       1 minute
    Terminate Process          handle=sync_gateway
    Process Should Be Stopped  handle=sync_gateway
