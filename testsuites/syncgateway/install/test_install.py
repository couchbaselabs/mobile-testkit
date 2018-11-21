from keywords.utils import log_info, host_for_url
from keywords.SyncGateway import (verify_sg_accel_version,
                                  verify_sync_gateway_version,
                                  verify_sync_gateway_product_info,
                                  )
from keywords.ClusterKeywords import ClusterKeywords


def test_install(params_from_base_test_setup):
    """
    @summary
        The initial versions of SG and CBS has already been provisioned at this point
        We have to query SG/A "/" endpoint on ADMIN Rest API
    """
    cluster_config = params_from_base_test_setup['cluster_config']
    mode = params_from_base_test_setup['mode']
    sync_gateway_version = params_from_base_test_setup['sync_gateway_version']

    cluster_util = ClusterKeywords()
    topology = cluster_util.get_cluster_topology(cluster_config, lb_enable=False)
    sync_gateways = topology["sync_gateways"]
    sg_accels = topology["sg_accels"]

    validate_sync_gateway(
        sync_gateways,
        sync_gateway_version,
    )

    if mode == "di":
        validate_sg_accel(
            sg_accels,
            sync_gateway_version,
        )


def validate_sync_gateway(sync_gateways, sync_gateway_version):
    log_info('---------------------------------------')
    log_info('Validating installation of Sync Gateway')
    log_info('---------------------------------------')

    for sg in sync_gateways:
        sg_ip = host_for_url(sg["admin"])
        log_info("Checking for sync gateway product info")
        verify_sync_gateway_product_info(sg_ip)
        log_info("Checking for sync gateway version: {}".format(sync_gateway_version))
        verify_sync_gateway_version(sg_ip, sync_gateway_version)

    log_info("Checked all the sync gateway nodes in the cluster")
    log_info('------------------------------------------')
    log_info('END Sync Gateway cluster check')
    log_info('------------------------------------------')


def validate_sg_accel(sg_accels, sync_gateway_version):
    log_info('----------------------------------')
    log_info('Vaidating installation of SG Accel')
    log_info('----------------------------------')

    for ac in sg_accels:
        ac_ip = host_for_url(ac)
        log_info("Checking for sg_accel version: {}".format(sync_gateway_version))
        verify_sg_accel_version(ac_ip, sync_gateway_version)

    log_info("Checked  all the sg accel nodes in the cluster")
    log_info('------------------------------------------')
    log_info('END SG Accel cluster check')
    log_info('------------------------------------------')
