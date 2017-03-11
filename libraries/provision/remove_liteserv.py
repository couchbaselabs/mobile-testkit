import argparse

from keywords.LiteServFactory import LiteServFactory


def remove_liteserv(platform, version_build, host, port, storage_engine):

    liteserv = LiteServFactory.create(platform=platform,
                                      version_build=version_build,
                                      host=host,
                                      port=port,
                                      storage_engine=storage_engine)
    liteserv.remove()


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", help="platform of liteserv to install", required=True)
    parser.add_argument("--version-build", help="version_build of liteserv to install", required=True)
    parser.add_argument("--host", help="host of liteserv to install", required=True)
    parser.add_argument("--port", help="port of liteserv to install", required=True)
    parser.add_argument("--storage-engine", help="storage_engine of liteserv to install", required=True)

    args = parser.parse_args()

    print("Uninstalling LiteServ: {} {} on {}:{} with storage engine: {}".format(args.platform,
                                                                                 args.version_build,
                                                                                 args.host,
                                                                                 args.port,
                                                                                 args.storage_engine))

    remove_liteserv(platform=args.platform,
                    version_build=args.version_build,
                    host=args.host,
                    port=args.port,
                    storage_engine=args.storage_engine)
