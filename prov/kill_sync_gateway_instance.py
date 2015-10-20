from ansible_runner import run_targeted_ansible_playbook


def kill_sync_gateway_instance(hostname):
    run_targeted_ansible_playbook("kill-sync-gateway.yml", hostname)
