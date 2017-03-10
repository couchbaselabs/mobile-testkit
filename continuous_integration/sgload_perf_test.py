#! /usr/bin/env python

# This is the Jenkins shell script for running an sgload based performance test

import collections
import os
import re
from libraries.utilities.generate_clusters_from_pool import generate_clusters_from_pool
from utilities.setup_ssh_tunnel import setup_tunnel
from utilities.setup_ssh_tunnel import get_remote_hosts_list
from libraries.provision.install_deps import install_deps
from libraries.provision.provision_cluster import provision_cluster
from libraries.provision.install_couchbase_server import CouchbaseServerConfig
from libraries.provision.install_sync_gateway import SyncGatewayConfig
from libraries.testkit.cluster import Cluster
from testsuites.syncgateway.performance.run_sgload_perf_test import run_sgload_perf_test
from keywords.utils import version_and_build


# A named tuple to hold all the environment variables (lightweight class without the boilerplate)
ScriptEnv = collections.namedtuple(
    'ScriptEnv',
    'remote_user ' +
    'pools_json ' +
    'sg_deploy_type ' +
    'install_deps_flag ' +
    'cluster_config ' +
    'provision_or_reset ' +
    'couchbase_server_version ' +
    'sync_gateway_version ' +
    'sync_gateway_commit ' +
    'sync_gateway_config_file ' +
    'sgload_num_readers ' +
    'sgload_num_writers ' +
    'sgload_num_updaters ' +
    'sgload_num_revs_per_doc ' +
    'sgload_num_docs ' +
    'sgload_num_channels ' +
    'sgload_batch_size ' +
    'sgload_writer_delay_ms ' +
    'sgload_log_level ' +
    'influxdb_host',
)

RESOURCES_POOL_FILENAME = "resources/pool.json"


def main():

    env = validate_environment()

    create_ansible_config(env.remote_user)

    write_resources_pool_json(env.pools_json)

    generate_clusters_from_pool(RESOURCES_POOL_FILENAME)

    maybe_setup_ssh_tunnel(env.remote_user, env.influxdb_host)

    maybe_deploy_github_keys(env.sg_deploy_type)

    maybe_install_deps(env.install_deps_flag, env.cluster_config)

    provision_or_reset_cluster(
        provision_or_reset=env.provision_or_reset,
        sg_deploy_type=env.sg_deploy_type,
        couchbase_server_version=env.couchbase_server_version,
        sync_gateway_version=env.sync_gateway_version,
        sync_gateway_commit=env.sync_gateway_commit,
        sync_gateway_config_file=env.sync_gateway_config_file,
        cluster_config=env.cluster_config,
    )

    run_sgload_perf_test_wrapper(
        cluster_config=env.cluster_config,
        remote_user=env.remote_user,
        sgload_num_readers=env.sgload_num_readers,
        sgload_num_writers=env.sgload_num_writers,
        sgload_num_updaters=env.sgload_num_updaters,
        sgload_num_revs_per_doc=env.sgload_num_revs_per_doc,
        sgload_num_docs=env.sgload_num_docs,
        sgload_num_channels=env.sgload_num_channels,
        sgload_batch_size=env.sgload_batch_size,
        sgload_writer_delay_ms=env.sgload_writer_delay_ms,
        sgload_log_level=env.sgload_log_level,
        influxdb_host=env.influxdb_host,
    )


def validate_environment():
    """
    Check for expected env variables
    """

    return ScriptEnv(
        remote_user=os.environ["REMOTE_USER"],
        pools_json=os.environ["POOLS_JSON"],
        sg_deploy_type=os.environ["SG_DEPLOY_TYPE"],
        install_deps_flag=str_to_bool(os.environ["INSTALL_DEPS"]),
        cluster_config=os.environ["CLUSTER_CONFIG"],
        provision_or_reset=os.environ["PROVISION_OR_RESET"],
        couchbase_server_version=os.environ["COUCHBASE_SERVER_VERSION"],
        sync_gateway_version=os.environ["SYNC_GATEWAY_VERSION"],
        sync_gateway_commit=os.environ["SYNC_GATEWAY_COMMIT"],
        sync_gateway_config_file=os.environ["SYNC_GATEWAY_CONFIG_PATH"],
        sgload_num_readers=os.environ["SGLOAD_NUM_READERS"],
        sgload_num_writers=os.environ["SGLOAD_NUM_WRITERS"],
        sgload_num_updaters=os.environ["SGLOAD_NUM_UPDATERS"],
        sgload_num_revs_per_doc=os.environ["SGLOAD_NUM_REVS_PER_DOC"],
        sgload_num_docs=os.environ["SGLOAD_NUM_DOCS"],
        sgload_num_channels=os.environ["SGLOAD_NUM_CHANNELS"],
        sgload_batch_size=os.environ["SGLOAD_BATCH_SIZE"],
        sgload_writer_delay_ms=os.environ["SGLOAD_WRITER_DELAY_MS"],
        sgload_log_level=os.environ["SGLOAD_LOG_LEVEL"],
        influxdb_host=os.environ["INFLUXDB_HOST"],
    )


def create_ansible_config(remote_user):
    # Read in ansible.cfg.example and replace "vagrant" -> remote_user and
    # write out result to ansible.cfg
    ansible_cfg_example = open("ansible.cfg.example").read()
    ansible_cfg = re.sub("vagrant", remote_user, ansible_cfg_example)
    with open("ansible.cfg", "w") as f:
        f.write(ansible_cfg)


def write_resources_pool_json(pools_json):
    with open(RESOURCES_POOL_FILENAME, "w") as f:
        f.write(pools_json)


def maybe_setup_ssh_tunnel(remote_user, influxdb_host):

    # Only want to do this on AWS, where remote_user is centos
    if remote_user != "centos":
        return

    remote_hosts_list = get_remote_hosts_list(RESOURCES_POOL_FILENAME)
    setup_tunnel(
        target_host=influxdb_host,
        target_port="8086",
        remote_hosts_user=remote_user,
        remote_hosts=remote_hosts_list,
        remote_host_port="8086",
    )


def maybe_deploy_github_keys(sg_deploy_type):
    if sg_deploy_type == "Source":
        raise Exception("TODO: support deploying gh deploy keys")


def maybe_install_deps(install_deps_flag, cluster_config):
    if install_deps_flag:
        print("install_deps_flag: {}, installing deps", install_deps_flag)
        install_deps(cluster_config)


def provision_or_reset_cluster(provision_or_reset, sg_deploy_type, couchbase_server_version,
                               sync_gateway_version, sync_gateway_commit,
                               sync_gateway_config_file, cluster_config):

    server_config = CouchbaseServerConfig(
        version=couchbase_server_version
    )

    version_number, build_number = version_and_build(sync_gateway_version)

    sync_gateway_conf = SyncGatewayConfig(
        version_number=version_number,
        build_number=build_number,
        commit=sync_gateway_commit,
        build_flags="",
        config_path=sync_gateway_config_file,
        skip_bucketcreation=False
    )

    # Don't specify version number on a source build
    if sg_deploy_type == "Source":
        sync_gateway_conf.version_number = None
    else:
        # Likewise, don't specify commmit on a package build
        sync_gateway_conf.commit = None

    if provision_or_reset == "Provision":
        print("provisioning cluster")
        provision_cluster(
            cluster_config=cluster_config,
            couchbase_server_config=server_config,
            sync_gateway_config=sync_gateway_conf
        )
    elif provision_or_reset == "Reset":
        print("resetting cluster")
        cluster = Cluster(config=cluster_config)
        cluster.reset(sync_gateway_config_file)


def run_sgload_perf_test_wrapper(cluster_config, remote_user, sgload_num_readers,
                                 sgload_num_writers, sgload_num_updaters,
                                 sgload_num_revs_per_doc, sgload_num_docs,
                                 sgload_num_channels, sgload_batch_size,
                                 sgload_writer_delay_ms, sgload_log_level,
                                 influxdb_host):

    if "GRAFANA_DB" not in os.environ:
        raise Exception("Missing GRAFANA_DB env variable that is required to install telegraf")

    if remote_user == "centos":
        os.environ["INFLUX_URL"] = "http://localhost:8086"
    else:
        os.environ["INFLUX_URL"] = "http://{}:8086".format(influxdb_host)

    sgload_arg_list_main = [
        'gateload',
        '--createreaders',
        '--createwriters',
        '--numreaders', sgload_num_readers,
        '--numwriters', sgload_num_writers,
        '--numupdaters', sgload_num_updaters,
        '--numrevsperdoc', sgload_num_revs_per_doc,
        '--numdocs', sgload_num_docs,
        '--numchannels', sgload_num_channels,
        '--batchsize', sgload_batch_size,
        '--statsdendpoint',
        'localhost:8125',
        '--statsdenabled',
        '--expvarprogressenabled',
        '--writerdelayms', sgload_writer_delay_ms,
        '--loglevel', sgload_log_level,
    ]

    run_sgload_perf_test(
        cluster_config,
        sgload_arg_list_main,
        False,
    )


def str_to_bool(strval):
    if strval == 'true':
        return True
    elif strval == 'false':
        return False
    else:
        raise Exception("Invalid boolean string value: {}.  Expecting 'true' or 'false'".format(strval))


if __name__ == "__main__":
    main()
