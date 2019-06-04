from CBLClient.Client import Client
from CBLClient.Args import Args


class Utils:
    _client = None

    def __init__(self, base_url):
        self.base_url = base_url

        # If no base url was specified, raise an exception
        if not self.base_url:
            raise Exception("No base_url specified")

        self._client = Client(base_url)

    def release(self, obj):
        # Release memory on the server
        if isinstance(obj, list):
            for i in obj:
                self._client.release(i)
        else:
            self._client.release(obj)

    def flushMemory(self):
        return self._client.invokeMethod("flushMemory")

    def copy_files(self, source_path, destination_path):
        args = Args()
        args.setString("source_path", source_path)
        args.setString("destination_path", destination_path)
        return self._client.invokeMethod("copy_files", args)
