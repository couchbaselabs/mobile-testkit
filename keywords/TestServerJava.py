from keywords.TestServerBase import TestServerBase


class TestServerJava(TestServerBase):

    def __init__(self, version_build, host, port, community_enabled=None, debug_mode=False, platform="java-linux"):
        super(TestServerJava, self).__init__(version_build, host, port)
        # TODO: implementation will be added in separate PR

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