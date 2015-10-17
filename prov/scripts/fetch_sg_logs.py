import ansible_runner


def fetch_sync_gateway_logs():
    ansible_runner.run_ansible_playbook("fetch-sync-gateway-logs.yml")

if __name__ == "__main__":
    fetch_sync_gateway_logs()