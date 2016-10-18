from LiteServAndroid import LiteServAndroid
from LiteServMacOSX import LiteServMacOSX
from LiteServNetMono import LiteServNetMono


class LiteServFactory:

    @staticmethod
    def validate_storage_engine(storage_engine):
        valid_storage_engines = ["SQLite", "SQLCipher", "ForestDB", "ForestDB+Encryption"]
        if storage_engine not in valid_storage_engines:
            raise ValueError("Unsupported 'storage_engine': {}".format(storage_engine))

    @staticmethod
    def validate_platform(platform):
        valid_platforms = ["android", "ios", "macosx", "net-mono", "net-msft"]
        if platform not in valid_platforms:
            raise ValueError("Unsupported 'platform': {}".format(platform))

    @staticmethod
    def create(platform, version_build, host, port, storage_engine):

        LiteServFactory.validate_platform(platform)
        LiteServFactory.validate_storage_engine(storage_engine)

        if platform == "android":
            return LiteServAndroid(version_build, host, port, storage_engine)
        # elif platform == "ios":
        #     return iOSLiteServ(version, host, port, storage_engine)
        elif platform == "macosx":
            return LiteServMacOSX(version_build, host, port, storage_engine)
        elif platform == "net-mono":
            return LiteServNetMono(version_build, host, port, storage_engine)
        # elif platform == "net-msft":
        #     return NetMSFT(version, host, port, storage_engine)
        # else:
            raise NotImplementedError("Unsupported version of LiteServ")
