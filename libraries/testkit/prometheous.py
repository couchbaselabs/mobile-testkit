import requests
from requests import HTTPError
from libraries.testkit.debug import log_request, log_response


class Prometheous:

    def start_prometheous(self):
        pass

    def stop_prometheous(self):
        pass

    def verify_stat_on_prometheous(self, stat_name, value):

        pass

    def parse_the_prometheous_data(self, stat_name, stat_data):
        print(stat_data)
        pass

    def query_prometheous(self, stat_name, host_name="localhost"):
        partial_url = "http://${host_name}:9090/api/v1/query?query="
        try:
            r = requests.get("{}{}".format(partial_url, stat_name))
            log_request(r)
            log_response(r)
            r.raise_for_status()
            resp_data = r.json()
            return resp_data
        except HTTPError:
            raise HTTPError



