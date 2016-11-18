import time

from requests.sessions import Session
from requests.exceptions import ConnectionError

from keywords.constants import MAX_RETRIES
from keywords.exceptions import LiteServError
from keywords.utils import log_r
from keywords.utils import log_info


class LiteServBase(object):
    """Base class that each LiteServ platform need to inherit from.
    Look at LiteServMacOSX.py as an example of a plaform implementation
    of this. This class provides a few common functions as well as
    specifies the API that must be implemented in the subclass."""

    def __init__(self, version_build, host, port, storage_engine, ssl_enabled):
        self.version_build = version_build
        self.host = host
        self.port = port
        self.ssl_enabled = ssl_enabled

        if self.ssl_enabled:
            scheme = "https"
        else:
            scheme = "http"

        self.url = "{}://{}:{}".format(scheme, self.host, self.port)
        self.storage_engine = storage_engine

        # Used for commandline programs such as net-mono and macosx
        self.process = None

        # For the subclasses, this property may be a file handle or a string
        self.logfile = None

        self.session = Session()
        self.session.headers['Content-Type'] = 'application/json'

        # Do not fail for self signed certificates.
        # Not a real world best practice!! For testing only.
        self.session.verify = False

    def download(self):
        raise NotImplementedError()

    def install(self):
        raise NotImplementedError()

    def start(self, logfile_name):
        raise NotImplementedError()

    def _verify_not_running(self):
        """
        Verifys that the endpoint does not return a 200 from a running service
        """
        try:
            resp = self.session.get(self.url)
        except ConnectionError:
            # Expecting connection error if LiteServ is not running on the port
            return

        log_r(resp)
        raise LiteServError("There should be no service running on the port")

    def _wait_until_reachable(self):

        count = 0
        while count < MAX_RETRIES:
            try:
                resp = self.session.get(self.url)
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

    def stop(self):
        raise NotImplementedError()

    def remove(self):
        raise NotImplementedError()
