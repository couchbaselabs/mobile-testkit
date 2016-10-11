import sys
import os
from optparse import OptionParser

from keywords.utils import log_info

from testkit.cluster import Cluster

if __name__ == "__main__":
    usage = """usage: reset_cluster.py
    --cong=<name-of-conf>
    """

    parser = OptionParser(usage=usage)

    parser.add_option("", "--conf",
                      action="store", type="string", dest="conf", default=None,
                      help="name of configuration in conf/ to reset cluster with")

    arg_parameters = sys.argv[1:]

    (opts, args) = parser.parse_args(arg_parameters)

    try:
        cluster_conf = os.environ["CLUSTER_CONFIG"]
    except KeyError as ke:
        log_info("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        raise KeyError("CLUSTER_CONFIG not defined. Unable to provision cluster.")

    cluster = Cluster(config=cluster_conf)
    cluster.reset(opts.conf)
