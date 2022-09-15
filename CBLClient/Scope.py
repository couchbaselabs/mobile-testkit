from CBLClient.Client import Client
from CBLClient.Args import Args


class Scope(object):
    _client = None

    def __init__(self, base_url):
        self.base_url = base_url

        # If no base url was specified, raise an exception
        if not self.base_url:
            raise Exception("No base_url specified")

        self._client = Client(base_url)

    def scopeName(self, scope):
        args = Args()
        args.setMemoryPointer("scope", scope)
        return self._client.invokeMethod("scope_scopeName", args)
        