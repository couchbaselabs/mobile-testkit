import argparse

from keywords.LiteServFactory import LiteServFactory


def install_liteserv(platform, version_build, host, port, storage_engine):

    liteserv = LiteServFactory.create(platform=platform,
                                      version_build=version_build,
                                      host=host,
                                      port=port,
                                      storage_engine=storage_engine)
    liteserv.download()
    liteserv.install()

    # launch to verify version
    liteserv.start("log.txt")
    liteserv.stop()


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", help="platform of liteserv to install", required=True)
    parser.add_argument("--version-build", help="version_build of liteserv to install", required=True)
    parser.add_argument("--host", help="host of liteserv to install", required=True)
    parser.add_argument("--port", help="port of liteserv to install", required=True)
    parser.add_argument("--storage-engine", help="storage_engine of liteserv to install", required=True)

    args = parser.parse_args()

    print("Installing LiteServ: {} {} on {}:{} with storage engine: {}".format(args.platform,
                                                                               args.version_build,
                                                                               args.host,
                                                                               args.port,
                                                                               args.storage_engine))

    install_liteserv(platform=args.platform,
                     version_build=args.version_build,
                     host=args.host,
                     port=args.port,
                     storage_engine=args.storage_engine)
