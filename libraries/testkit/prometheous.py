import requests
from requests import HTTPError
from libraries.testkit.debug import log_request, log_response



def start_prometheous():
    pass


def stop_prometheous():
    pass


def verify_stat_on_prometheous(stat_name):
    stats_data = query_prometheous(stat_name)
    print(stats_data)
    return stats_data["data"]["result"][0]["value"][0]


def parse_the_prometheous_data(stat_name, stat_data):
    print(stat_data)
    pass


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
    pass


def install(self):
    pass



