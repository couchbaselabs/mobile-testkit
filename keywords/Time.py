import time
from utils import log_info

class Time:

    def get_unix_timestamp(self, delta=0):
        """
        Returns the unix timestamp since epoch (https://en.wikipedia.org/wiki/Unix_time)
        If a delta is provided, it will return the timestamp +/- the delta (s)
        ex. delta=3, if epoch=1466540261, then the return value will be 1466540264
        ex. delta=-3, if epoch=1466540261, then the return value will be 1466540258
        """
        unix_time_now= int(time.time())
        log_info("Unix timestamp: {}".format(unix_time_now))
        timestamp_with_delta = unix_time_now + delta
        log_info("Unix timestamp with delta: {}".format(timestamp_with_delta))
        return timestamp_with_delta