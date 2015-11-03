import os
from ansible_runner import run_ansible_playbook


def reset(configuration):

    conf_path = os.path.abspath("conf/" + configuration)

    print(">>> Restarting sync_gateway with configuration: {}".format(conf_path))

    run_ansible_playbook(
        "reset-sync-gateway.yml",
        extra_vars="sync_gateway_config_filepath={0}".format(conf_path)
    )
