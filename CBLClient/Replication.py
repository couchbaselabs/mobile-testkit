from CBLClient.Client import Client
from CBLClient.Args import Args
from keywords.utils import log_info


class Replication:
    _client = None
    _baseUrl = None

    def __init__(self, baseUrl):
        self.baseUrl = baseUrl

        # If no base url was specified, raise an exception
        if not self.baseUrl:
            raise Exception("No baseUrl specified")

        self._client = Client(baseUrl)

    def configure_replication(self, source_db, target_url, replication_type="push_pull", continuous=True):
        args = Args()
        args.setMemoryPointer("source_db", source_db)
        args.setString("target_url", target_url)
        args.setString("replication_type", replication_type)
        args.setBoolean("continuous", continuous)

        return self._client.invokeMethod("configure_replication", args)

    def start_replication(self, replication_obj):
        args = Args()
        args.setMemoryPointer("replication_obj", replication_obj)

        self._client.invokeMethod("start_replication", args)

    def stop_replication(self, replication_obj):
        args = Args()
        args.setMemoryPointer("replication_obj", replication_obj)

        self._client.invokeMethod("stop_replication", args)
