import logging

from testkit.debug import log_request
from testkit.debug import log_response
import requests

class Listener:

    def __init__(self, hostname, port):
        self.url = "http://{}:{}".format(hostname, port)
        logging.info("Launching Listener on {}".format(self.url))

    def verify_listener_launched(self):
        resp = requests.get(self.url)
        log_request(resp)
        log_response(resp)
