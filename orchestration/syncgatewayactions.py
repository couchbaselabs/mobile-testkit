import os

from prov.ansible_runner import run_targeted_ansible_playbook


def stop(hostname):
    run_targeted_ansible_playbook("stop-sync-gateway.yml", target_name=hostname)


def start(hostname, configuration):

    conf_path = os.path.abspath("conf/" + configuration)

    print(">>> Starting sync_gateway with configuration: {}".format(conf_path))

    run_targeted_ansible_playbook(
        "start-sync-gateway.yml",
        extra_vars="sync_gateway_config_filepath={0}".format(conf_path),
        target_name=hostname)


def restart(hostname, configuration):

    conf_path = os.path.abspath("conf/" + configuration)

    print(">>> Restarting sync_gateway with configuration: {}".format(conf_path))

    run_targeted_ansible_playbook(
        "reset-sync-gateway.yml",
        extra_vars="sync_gateway_config_filepath={0}".format(conf_path),
        target_name=hostname
    )



