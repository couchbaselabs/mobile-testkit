from CBLClient.Client import Client
from CBLClient.Args import Args


class Conflict(object):
    _client = None

    def __init__(self, base_url):
        self.base_url = base_url

        # If no base url was specified, raise an exception
        if not self.base_url:
            raise Exception("No base_url specified")

        self._client = Client(base_url)

    def conflictResolver(self, conflict_type="giveup"):
        args = Args()
        args.setString("conflict_type", conflict_type)
        
        return self._client.invokeMethod("conflict_resolver", args)

    def getBase(self, conflict):
        args = Args()
        args.setMemoryPointer("conflict", conflict)
        self._client.invokeMethod("conflict_getBase", args)

    def getMine(self, conflict):
        args = Args()
        args.setMemoryPointer("conflict", conflict)
        self._client.invokeMethod("conflict_getMine", args)

    def getTheirs(self, conflict):
        args = Args()
        args.setMemoryPointer("conflict", conflict)
        self._client.invokeMethod("conflict_getTheirs", args)
