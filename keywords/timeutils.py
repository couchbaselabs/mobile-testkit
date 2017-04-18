import time
import datetime

from keywords.utils import log_info


class Time:

    def get_unix_timestamp(self, delta=0):
        """
        Returns the unix timestamp since epoch (https://en.wikipedia.org/wiki/Unix_time)
        If a delta is provided, it will return the timestamp +/- the delta (s)
        ex. delta=3, if epoch=1466540261, then the return value will be 1466540264
        ex. delta=-3, if epoch=1466540261, then the return value will be 1466540258
        """

        unix_time_now = int(time.time())
        log_info("Unix timestamp: {}".format(unix_time_now))
        timestamp_with_delta = unix_time_now + delta
        log_info("Unix timestamp with delta: {}".format(timestamp_with_delta))
        return timestamp_with_delta

    def get_iso_datetime(self, delta=0):
        """
        Returns an ISO 8061 timestamp with a specified delta
        If a delta is provided, it will return the timestamp +/- the delta in seconds
        ex. return format "2026-01-01T00:00:00.000+00:00"
        """

        iso_8061_utc_now = datetime.datetime.utcnow()

        # Strip off microseconds to give sync_gateway the expected format defined in the docstring
        iso_8061_utc_now = iso_8061_utc_now.replace(microsecond=0)
        iso_8061_utc_now_with_delta = iso_8061_utc_now + datetime.timedelta(days=0, seconds=delta)

        timestamp_now = "{}.000+00:00".format(iso_8061_utc_now.isoformat())
        timestamp_with_delta = "{}.000+00:00".format(iso_8061_utc_now_with_delta.isoformat())

        log_info("Now: {}".format(timestamp_now))
        log_info("With delta: {}".format(timestamp_with_delta))

        return timestamp_with_delta
