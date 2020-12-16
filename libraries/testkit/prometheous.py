import requests
from requests import HTTPError
from libraries.testkit.debug import log_request, log_response
import os
import subprocess
import sys
import yaml

def start_prometheous(sg_ip):
    prometheous_file = "libraries/provision/ansible/playbooks/prometheous.yml"
    with open(prometheous_file) as fp:
        data = yaml.full_load(fp)
        data["scrape_configs"]["static_configs"]["target"] = {sg_ip: 4986}
    with open(prometheous_file, 'w') as file:
        yaml.dump(data, file)

    pid = subprocess.Popen(["prometheous", "--config.file=libraries/provision/ansible/playbooks/prometheous.yml"], creationflags=subprocess.DETACHED_PROCESS)
    return pid


def stop_prometheous(pid):
    subprocess.Popen.kill(pid)


def verify_stat_on_prometheous(stat_name):
    stats_data = query_prometheous(stat_name)
    print(stats_data)
    return stats_data["data"]["result"][0]["value"][0]


def query_prometheous(stat_name, host_name="localhost"):
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


def download_prometheous(self):
    url = "https://github.com/prometheus/prometheus/releases/ download/v2.3.2/prometheus-2.3.2.linux-amd64.tar.gz"
    cmd = 'wget %s' % url
    subprocess.call(cmd, shell=True)
    cmd2 = 'cp prometheus - 2.3.2.linux - amd64/prometheus /usr/local/bin/'
    subprocess.call(cmd2, shell=True)
    cmd3 = 'cp prometheus-2.3.2.linux-amd64/promtool /usr/local/bin/'
    subprocess.call(cmd3, shell=True)


def install(self):
    subprocess.check_call([sys.executable, '-m', 'brew', 'install',
                           'prometheous'])



