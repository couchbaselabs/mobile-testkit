from keywords.TestServerAndroid import TestServerAndroid
from keywords.TestServeriOS import TestServeriOS
from keywords.TestServerNetMono import TestServerNetMono
from keywords.TestServerNetMsft import TestServerNetMsft
from keywords.TestServerJava import TestServerJava
from keywords.TestServerJavaWS import TestServerJavaWS
from keywords.TestServerCpp import TestServerCpp

class TestServerFactory:

    @staticmethod
    def validate_version_build(version_build):
        if version_build is None:
            raise ValueError("Make sure you provide a version / build!")

    @staticmethod
    def validate_platform(platform):
        valid_platforms = ["android", "ios", "net-mono", "net-msft", "net-uwp", "xamarin-android", "xamarin-ios",
                           "java-macosx", "java-msft", "java-ubuntu", "java-centos", "c-linux", "c-rpi", "c-macosx",
                           "javaws-macosx", "javaws-msft", "javaws-ubuntu", "javaws-centos", "c-msft", "c-ios", "c-uwp",
                           "c-android", "c-debian"]
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
    def create(platform, version_build, host, port, community_enabled=None, debug_mode=False):
        TestServerFactory.validate_platform(platform)
        TestServerFactory.validate_host(host)
        TestServerFactory.validate_port(port)

        if platform == "android" or platform == "xamarin-android" or platform == "c-android":
            return TestServerAndroid(version_build, host, port, community_enabled=community_enabled,
                                     debug_mode=debug_mode, platform=platform)
        elif platform == "ios" or platform == "xamarin-ios" or platform == "c-ios":
            return TestServeriOS(version_build, host, port, community_enabled=community_enabled, debug_mode=debug_mode,
                                 platform=platform)
        elif platform == "net-mono":
            return TestServerNetMono(version_build, host, port)
        elif platform == "net-msft" or platform == "net-uwp" or platform == "c-msft":
            return TestServerNetMsft(version_build, host, port, platform=platform, community_enabled=community_enabled)
        elif platform in ["java-macosx", "java-msft", "java-ubuntu", "java-centos"]:
            return TestServerJava(version_build, host, port, debug_mode, platform=platform,
                                  community_enabled=community_enabled)
        elif platform in ["javaws-macosx", "javaws-msft", "javaws-ubuntu", "javaws-centos"]:
            return TestServerJavaWS(version_build, host, port, debug_mode, platform=platform,
                                    community_enabled=community_enabled)
        elif platform in ["c-macosx", "c-rpi", "c-debian"]:
            return TestServerCpp(version_build, host, port, debug_mode, platform=platform,
                                 community_enabled=community_enabled)
        else:
            raise NotImplementedError("Test server does not support this version")
