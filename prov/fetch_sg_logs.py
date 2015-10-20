from ansible_runner import run_ansible_playbook


def fetch_sync_gateway_logs():
    run_ansible_playbook("fetch-sync-gateway-logs.yml")

if __name__ == "__main__":
    fetch_sync_gateway_logs()
