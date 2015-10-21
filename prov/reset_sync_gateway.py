import ansible_runner


def reset_sync_gateway():
    ansible_runner.run_ansible_playbook("reset-sync-gateway.yml")
