import os

from keywords.utils import log_info
from libraries.testkit.cluster import Cluster

if __name__ == "__main__":

    try:
        cluster_conf = os.environ["CLUSTER_CONFIG"]
    except KeyError as ke:
        log_info("Make sure CLUSTER_CONFIG is defined and pointing to the configuration you would like to provision")
        raise KeyError("CLUSTER_CONFIG not defined. Unable to provision cluster.")

    cluster = Cluster(config=cluster_conf)
    cluster.restart_services()
