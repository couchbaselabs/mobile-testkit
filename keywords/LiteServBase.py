import time

import requests
from requests.exceptions import ConnectionError

from keywords.constants import MAX_RETRIES
from keywords.exceptions import LiteServError
from keywords.utils import log_r
from keywords.utils import log_info


class LiteServBase(object):

    def __init__(self, version_build, host, port, storage_engine):
        self.version_build = version_build
        self.host = host
        self.port = port
        self.storage_engine = storage_engine

        # Used for commandline programs such as net-mono and macosx
        self.process = None

    def download(self):
        raise NotImplementedError()

    def install(self):
        raise NotImplementedError()

    def start(self, logfile=None):
        raise NotImplementedError()

    def _verify_not_running(self):
        """
        Verifys that the endpoint does not return a 200 from a running service
        """
        try:
            resp = requests.get("http://{}:{}/".format(self.host, self.port))
        except ConnectionError:
            # Expecting connection error if LiteServ is not running on the port
            return

        log_r(resp)
        raise LiteServError("There should be no service running on the port")

    def _wait_until_reachable(self):
        url = "http://{}:{}".format(self.host, self.port)
        count = 0
        while count < MAX_RETRIES:
            try:
                resp = requests.get(url)
                # If request does not throw, exit retry loop
                break
            except ConnectionError:
                log_info("LiteServ may not be launched (Retrying) ...")
                time.sleep(1)
                count += 1

        if count == MAX_RETRIES:
            raise LiteServError("Could not connect to LiteServ")

        return resp.json()

    def _verify_launched(self):
        raise NotImplementedError()

    def stop(self, logfile):
        raise NotImplementedError()
