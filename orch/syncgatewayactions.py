from ansible_runner import run_targeted_ansible_playbook


def stop(hostname):
    run_targeted_ansible_playbook("tasks/stop-sync-gateway.yml", hostname)


def start(hostname):
    run_targeted_ansible_playbook("tasks/start-sync-gateway.yml", hostname)
