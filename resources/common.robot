*** Settings ***
Documentation    Common Variables / Keywords

Library     ${KEYWORDS}/ClusterKeywords.py

*** Variables ***
${LIBRARIES}                libraries
${KEYWORDS}                 keywords

${RESOURCES}                resources
${ARTIFACTS}                ${RESOURCES}/artifacts
${SYNC_GATEWAY_CONFIGS}     ${RESOURCES}/sync_gateway_configs
${CLUSTER_CONFIGS}          ${RESOURCES}/cluster_configs

# Suite paths
${SYNC_GATEWAY_SUITE_FUNCTIONAL}  testsuites/syncgateway/functional

*** Keywords ***
Provision Cluster
    [Arguments]    ${cluster_config}  ${server_version}  ${sync_gateway_version}  ${sync_gateway_config}
    [Documentation]    Installs a Sync Gateway (build) + Sg Accel cluster based on the ${cluster_config}
    ...  server_version = the version of Couchbase Server to install (ex. 4.1.0 or 4.5.0-2151)
    ...  sync_gateway_version = the version of Sync Gateway and Sg Accel to install (ex. 1.2.1-4 or commit hash)
    ...  sync_gateway_config = the config to launch the Sync Gateways and Sg Accels with.
    ...  Cluster configs can be found in 'resources/cluster_configs'

    Set Environment Variable  CLUSTER_CONFIG  ${cluster_config}

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

    Should Be Equal As Integers  ${result.rc}  0

    Log  ${result.stderr}
    Log  ${result.stdout}

Clean Cluster
    Log                         Cluster Config: %{CLUSTER_CONFIG}
    ${result} =  Run Process  python  ${LIBRARIES}/provision/clean_cluster.py

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



