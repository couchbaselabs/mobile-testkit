from CBLClient.Client import Client
from CBLClient.Args import Args


class FileLogging(object):
    _db = None
    _baseUrl = None

    def __init__(self, base_url):
        self.base_url = base_url

        # If no base url was specified, raise an exception
        if not self.base_url:
            raise Exception("No base_url specified")

        self._client = Client(base_url)

    def configure(self, log_level="debug", directory="", max_rotate_count=1, max_size=512000, plain_text=False):
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

    def get_directory(self):
        args = Args()
        return self._client.invokeMethod("logging_getDirectory", args)

    def set_plain_text_status(self, config, plain_text=False):
        args = Args()
        args.setMemoryPointer("config", config)
        args.setBoolean("plain_text", plain_text)
        return self._client.invokeMethod("logging_setPlainTextStatus", args)

    def set_max_rotate_count(self, config, max_rotate_count=1):
        args = Args()
        args.setMemoryPointer("config", config)
        args.setInt("max_rotate_count", max_rotate_count)
        return self._client.invokeMethod("logging_setMaxRotateCount", args)

    def set_max_size(self, config, max_size=512000):
        args = Args()
        args.setMemoryPointer("config", config)
        args.setLong("max_size", max_size)
        return self._client.invokeMethod("logging_setMaxSize", args)

    def set_config(self, directory=""):
        args = Args()
        args.SetString("directory", directory)
        return self._client.invokeMethod("logging_setConfig", args)

    def set_log_level(self, config, log_level="verbose"):
        args = Args()
        args.setMemoryPointer("config", config)
        args.setString("log_level", log_level)
        return self._client.invokeMethod("logging_setLogLevel", args)

    def get_logs_in_zip(self):
        args = Args()
        file = self._client.invokeMethod("logging_getLogsInZip", args, True)
        return file
