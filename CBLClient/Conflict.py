from CBLClient.Client import Client
from CBLClient.Args import Args

class Conflict:
    _client = None
    _baseUrl = None

    def __init__(self, baseUrl):
        self.baseUrl = baseUrl

        # If no base url was specified, raise an exception
        if not self.baseUrl:
            raise Exception("No baseUrl specified")

        self._client = Client(baseUrl)

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
