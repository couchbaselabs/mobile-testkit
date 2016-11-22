from keywords.LiteServAndroid import LiteServAndroid
from keywords.LiteServiOS import LiteServiOS
from keywords.LiteServMacOSX import LiteServMacOSX
from keywords.LiteServNetMono import LiteServNetMono
from keywords.LiteServNetMsft import LiteServNetMsft


class LiteServFactory:

    @staticmethod
    def validate_version_build(version_build):
        if version_build is None:
            raise ValueError("Make sure you provide a version / build!")

        if len(version_build.split("-")) != 2:
            raise ValueError("Make sure your version_build follows the format: 1.3.1-13")

    @staticmethod
    def validate_platform(platform):
        valid_platforms = ["android", "ios", "macosx", "net-mono", "net-msft"]
        if platform not in valid_platforms:
            raise ValueError("Unsupported 'platform': {}".format(platform))

    @staticmethod
    def validate_host(host):
        if host is None:
            raise ValueError("Make sure you provide a host!")

    @staticmethod
    def validate_port(port):
        if port is None:
            raise ValueError("Make sure you provide a port!")

    @staticmethod
    def validate_storage_engine(storage_engine):
        valid_storage_engines = ["SQLite", "SQLCipher", "ForestDB", "ForestDB+Encryption"]
        if storage_engine not in valid_storage_engines:
            raise ValueError("Unsupported 'storage_engine': {}".format(storage_engine))

    @staticmethod
    def create(platform, version_build, host, port, storage_engine):

        LiteServFactory.validate_platform(platform)
        LiteServFactory.validate_version_build(version_build)
        LiteServFactory.validate_host(host)
        LiteServFactory.validate_port(port)
        LiteServFactory.validate_storage_engine(storage_engine)

        if platform == "android":
            return LiteServAndroid(version_build, host, port, storage_engine)
        elif platform == "ios":
            return LiteServiOS(version_build, host, port, storage_engine)
        elif platform == "macosx":
            return LiteServMacOSX(version_build, host, port, storage_engine)
        elif platform == "net-mono":
            return LiteServNetMono(version_build, host, port, storage_engine)
        elif platform == "net-msft":
            return LiteServNetMsft(version_build, host, port, storage_engine)
        else:
            raise NotImplementedError("Unsupported version of LiteServ")
