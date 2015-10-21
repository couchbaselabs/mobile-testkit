from ansible_runner import run_targeted_ansible_playbook


def stop_instance(hostname):
    run_targeted_ansible_playbook("kill-sync-gateway.yml", hostname)
