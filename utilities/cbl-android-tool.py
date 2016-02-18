def install_and_launch_liteserv(port):


if __name__ == "__main__":
    usage = """usage: python install_sync_gateway.py
    --branch=<sync_gateway_branch_to_build>
    """

    default_sync_gateway_config = os.path.abspath("conf/sync_gateway_default.json")

    parser = OptionParser(usage=usage)

    parser.add_option("", "--version",
                      action="store", type="string", dest="version", default=None,
                      help="sync_gateway version to download (ex. 1.2.0-5)")