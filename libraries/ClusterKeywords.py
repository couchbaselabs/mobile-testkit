from testkit.cluster import Cluster


class ClusterKeywords:

    def reset_cluster(self, sync_gateway_config):
        c = Cluster()
        c.reset(sync_gateway_config)


