import os
import re
import sys
import json
import time

from testkit import settings

import logging
log = logging.getLogger(settings.LOGGER)

class Config:

    def __init__(self, conf_path):

        self.conf_path = conf_path
        self.mode = None 
        self.bucket_name_set = []
        
        with open(conf_path, "r") as config:
            data = config.read()

            # strip out templated variables {{ ... }} and sync functions `function ... }`
            data = strip_invalid_json_from_config(data)

            # Find all bucket names in config's databases: {}
            conf_obj = json.loads(data)

            self.discover_mode(conf_obj)

            self.discover_bucket_name_set(conf_obj)


    def get_mode(self):

        return self.mode

    def get_bucket_name_set(self):

        return self.bucket_name_set

    def discover_mode(self, conf_obj):
        
        if "cluster_config" in conf_obj.keys():
            self.mode = "distributed_index"
        else:
            self.mode = "channel_cache"
        
    def discover_bucket_name_set(self, conf_obj):

            bucket_names_from_config = []
            # Add CBGT buckets
            if "cluster_config" in conf_obj.keys():
                bucket_names_from_config.append(conf_obj["cluster_config"]["bucket"])

            dbs = conf_obj["databases"]
            for key, val in dbs.iteritems():
                # Add data buckets
                bucket_names_from_config.append(val["bucket"])
                if "channel_index" in val:
                    # index buckets
                    bucket_names_from_config.append(val["channel_index"]["bucket"])

                if not val.has_key("shadow"):
                    continue

                shadow = val["shadow"]
                if len(shadow["bucket"]) > 0:
                    bucket_names_from_config.append(shadow["bucket"])

            # Buckets may be shared for different functionality
            self.bucket_name_set = list(set(bucket_names_from_config))


def strip_invalid_json_from_config(data):
    
    # strip out templated variables {{ ... }}
    data = re.sub("({{.*}})", "0", data)
    
    # strip out sync functions `function ... }`
    data = re.sub("(`function.*\n)(.*\n)+(.*}`)", "0", data)

    return data
