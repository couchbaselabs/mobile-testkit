import requests
from requests import HTTPError
from libraries.testkit.debug import log_request, log_response
import subprocess
from sys import platform
import yaml
import os
import signal


def start_prometheus(sg_ip):
    prometheus_file = "libraries/provision/ansible/playbooks/prometheus.yml"
    with open(prometheus_file) as fp:
        data = yaml.full_load(fp)
        data["scrape_configs"]["static_configs"]["target"] = {sg_ip: 4986}
    # Replace the SG_IP value in the prometheus_file
    with open(prometheus_file, 'w') as file:
        yaml.dump(data, file)
    # Start the premetheous in the separate process
    pid = subprocess.Popen(["prometheus", "--config.file=libraries/provision/ansible/playbooks/prometheus.yml"], creationflags=subprocess.DETACHED_PROCESS)
    return pid


def stop_prometheus(pid):
    os.kill(int(pid), signal.SIGKILL)


def is_prometheus_installed():
    try:
        subprocess.run(['prometheus --version'], check=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    except subprocess.CalledProcessError:
        return False
    return True


def get_platform():
    return platform


def verify_stat_on_prometheus(stat_name):
    stats_data = query_prometheus(stat_name)
    print(stats_data)
    return stats_data["data"]["result"][0]["value"][0]


def query_prometheus(stat_name, host_name="localhost"):
    partial_url = "http://localhost:9090/api/v1/query?query="
    try:
        r = requests.get("{}{}".format(partial_url, stat_name))
        log_request(r)
        log_response(r)
        r.raise_for_status()
        resp_data = r.json()
        return resp_data
    except HTTPError:
        raise HTTPError


def install_prometheus():
    if platform == "darwin":
        subprocess.run("brew install prometheus", shell=True, check=True)
        return is_prometheus_installed()
    else:
        url = "https://github.com/prometheus/prometheus/releases/download/v2.3.2/prometheus-2.3.2.linux-amd64.tar.gz"
        cmd = 'wget %s' % url
        subprocess.run(cmd, shell=True)
        cmd4 = "tar -xvzf prometheus-2.3.2.linux-amd64.tar.gz"
        subprocess.run(cmd4, shell=True)
        cmd2 = 'cp prometheus-2.3.2.linux-amd64/prometheus /usr/local/bin/'
        subprocess.run(cmd2, shell=True)
        cmd3 = 'cp prometheus-2.3.2.linux-amd64/promtool /usr/local/bin/'
        subprocess.run(cmd3, shell=True)
        return is_prometheus_installed()
