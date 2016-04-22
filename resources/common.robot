*** Settings ***
Documentation    Common Variables / Keywords

*** Variables ***
${LIBRARIES}                libraries

${RESOURCES}                resources
${ARTIFACTS}                ${RESOURCES}/artifacts
${SYNC_GATEWAY_CONFIGS}     ${RESOURCES}/sync_gateway_configs
${CLUSTER_CONFIGS}          ${RESOURCES}/cluster_configs

# Suite paths
${SYNC_GATEWAY_SUITE_FUNCTIONAL}  testsuites/syncgateway/functional

*** Keywords ***
Provision Cluster With Sync Gateway Build
    [Arguments]     ${server_version}  ${sync_gateway_version}  ${sync_gateway_config}
    [Documentation]    Installs a Sync Gateway (build) + Sg Accel cluster based on the set $CLUSTER_CONFIG.
    ...  server_version = the version of Couchbase Server to install (ex. 4.1.0 or 4.5.0-2151)
    ...  sync_gateway_version = the version of Sync Gateway and Sg Accel to install (ex. 1.2.1-4)
    ...  sync_gateway_config = the config to launch the Sync Gateways and Sg Accels with.
    ...  Cluster configs can be found in 'resources/cluster_configs'

    Log                         Cluster Config: %{CLUSTER_CONFIG}
    ${server_arg}               Catenate  SEPARATOR=  --server-version=            ${server_version}
    ${sync_gateway_arg}         Catenate  SEPARATOR=  --sync-gateway-version=      ${sync_gateway_version}
    ${sync_gateway_config_arg}  Catenate  SEPARATOR=  --sync-gateway-config-file=  ${sync_gateway_config}
    Log  ${server_arg}
    Log  ${sync_gateway_arg}
    Log  ${sync_gateway_config_arg}
    ${result} =  Run Process  python  ${LIBRARIES}/provision/provision_cluster.py  ${server_arg}  ${sync_gateway_arg}  ${sync_gateway_config_arg}
    Log  ${result.stderr}
    Log  ${result.stdout}

Provision Cluster With Sync Gateway Source
    [Arguments]     ${server_version}   ${sync_gateway_branch}    ${sync_gateway_config}
    [Documentation]    Installs a Sync Gateway (source) + Sg Accel cluster based on the set $CLUSTER_CONFIG.
    ...  server_version = the version of Couchbase Server to install (ex. 4.1.0 or 4.5.0-2151)
    ...  sync_gateway_version = the version of Sync Gateway and Sg Accel to install (ex. 1.2.1-4)
    ...  sync_gateway_config = the config to launch the Sync Gateways and Sg Accels with.
    ...  Cluster configs can be found in 'resources/cluster_configs'

    Log                         Cluster Config: %{CLUSTER_CONFIG}
    ${server_arg}               Catenate  SEPARATOR=  --server-version=            ${server_version}
    ${sync_gateway_arg}         Catenate  SEPARATOR=  --sync-gateway-branch=       ${sync_gateway_branch}
    ${sync_gateway_config_arg}  Catenate  SEPARATOR=  --sync-gateway-config-file=  ${sync_gateway_config}
    Log  ${server_arg}
    Log  ${sync_gateway_arg}
    Log  ${sync_gateway_config_arg}
    ${result} =  Run Process  python  ${LIBRARIES}/provision/provision_cluster.py  ${server_arg}  ${sync_gateway_arg}  ${sync_gateway_config_arg}
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



