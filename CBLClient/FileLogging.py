from CBLClient.Client import Client
from CBLClient.Args import Args
from keywords.utils import log_info

class FileLogging(object):
    _db = None
    _baseUrl = None

    def __init__(self, base_url):
        self.base_url = base_url

        # If no base url was specified, raise an exception
        if not self.base_url:
            raise Exception("No base_url specified")

        self._client = Client(base_url)

    def configure(self, log_level="debug", directory="", max_rotate_count=0, max_size=0, plain_text=False):
        args = Args()
        args.setString("log_level", log_level)
        args.setString("directory", directory)
        args.setInt("max_rotate_count", max_rotate_count)
        args.setLong("max_size", max_size)
        args.setBoolean("plain_text", plain_text)
        return self._client.invokeMethod("logging_configure", args)

    def get_plain_text_status(self):
        args = Args()
        return self._client.invokeMethod("logging_getPlainTextStatus", args)

    def get_max_rotate_count(self):
        args = Args()
        return self._client.invokeMethod("logging_getMaxRotateCount", args)

    def get_max_size(self):
        args = Args()
        return self._client.invokeMethod("logging_getMaxSize", args)

    def get_log_level(self):
        args = Args()
        return self._client.invokeMethod("logging_getLogLevel", args)

    def get_config(self):
        args = Args()
        return self._client.invokeMethod("logging_getConfig", args)

    def delete_log_files(self):
        args = Args()
        return self._client.invokeMethod("logging_deleteLogFiles", args)