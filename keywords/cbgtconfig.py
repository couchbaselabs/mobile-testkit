class CbgtConfig:

    def __init__(self, rest_config):
        self.config = rest_config
        self.p_indexes = self.config["planPIndexes"]["planPIndexes"]
        self.num_shards = len(self.p_indexes)
