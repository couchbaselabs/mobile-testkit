import os
import subprocess

import requests

from keywords.TestServerBase import TestServerBase
from keywords.constants import LATEST_BUILDS, RELEASED_BUILDS
from keywords.constants import BINARY_DIR
from keywords.exceptions import LiteServError
from keywords.utils import version_and_build
from keywords.utils import log_info


class TestServerJava(TestServerBase):

    def __init__(self, version_build, host, port, community_enabled=None, debug_mode=False, platform="java"):
        super(TestServerJava, self).__init__(version_build, host, port)
        self.platform = platform

        if self.platform == "java":
            # java desktop
            # prepare java desktop parameters TODO: remove this line after implementation
            print("self.platform = {}".format(self.platform))
        elif self.platform == "java-ws":
            # java web service
            # prepare java web service parameters TODO: remove this line after implementation
            print("self.platform = {}".format(self.platform))

    def download(self, version_build=None):
       raise NotImplementedError()

    def install(self):
        raise NotImplementedError()

    def remove(self):
        raise NotImplementedError()

    def start(self, logfile_name):
        raise NotImplementedError()

    def _verify_launched(self):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()
