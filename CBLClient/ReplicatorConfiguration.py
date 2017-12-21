from CBLClient.Client import Client
from CBLClient.Args import Args

class ReplicatorConfiguration:
    _client = None
    _baseUrl = None

    def __init__(self, baseUrl):
        self.baseUrl = baseUrl

        # If no base url was specified, raise an exception
        if not self.baseUrl:
            raise Exception("No baseUrl specified")

        self._client = Client(baseUrl)

    def create(self, sourceDb, targetDb=None, targetURI=None ):
        args = Args()
        args.setMemoryPointer("sourceDb", sourceDb)
        if targetDb:
            args.setMemoryPointer("targetDb", targetDb)
        elif targetURI:
            args.setMemoryPointer("targetURI", targetURI)
        else:
            raise Exception("Pass either targetDb or targetURI.")
        return self._client.invokeMethod("replicatorConfiguration_create",
                                         args)

    def copy(self, configuration):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        return self._client.invokeMethod("replicatorConfiguration_copy", args)

    def getAuthenticator(self, configuration):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        return self._client.invokeMethod("replicatorConfiguration_getAuthenticator",
                                         args)

    def getChannels(self, configuration):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        return self._client.invokeMethod("replicatorConfiguration_getChannels",
                                         args)

    def getConflictResolver(self, configuration):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        self._client.invokeMethod("replicatorConfiguration_getConflictResolver",
                                  args)

    def getDatabase(self, configuration):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        self._client.invokeMethod("replicatorConfiguration_getDatabase",
                                  args)

    def getDocumentIDs(self, configuration):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        self._client.invokeMethod("replicatorConfiguration_getDocumentIDs",
                                  args)

    def getPinnedServerCertificate(self, configuration):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        self._client.invokeMethod("replicatorConfiguration_getPinnedServerCertificate",
                                  args)

    def getReplicatorType(self, configuration):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        self._client.invokeMethod("replicatorConfiguration_getReplicatorType",
                                  args)

    def getTarget(self, configuration):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        self._client.invokeMethod("replicatorConfiguration_getTarget", args)

    def isContinuous(self, configuration):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        self._client.invokeMethod("replicatorConfiguration_isContinuous",
                                  args)

    def setAuthenticator(self, configuration, authenticator):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        args.setMemoryPointer("authenticator", authenticator)
        self._client.invokeMethod("replicatorConfiguration_setAuthenticator",
                                  args)

    def setChannels(self, configuration, channels):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        args.setArray("channels", channels)
        self._client.invokeMethod("replicatorConfiguration_setChannels",
                                  args)

    def setConflictResolver(self, configuration, conflictResolver):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        args.setMemoryPointer("conflictResolver", conflictResolver)
        self._client.invokeMethod("replicatorConfiguration_setConflictResolver",
                                  args)

    def setContinuous(self, configuration, continuous):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        args.setBoolean("continuous", continuous)
        self._client.invokeMethod("replicatorConfiguration_setContinuous",
                                  args)

    def setDocumentIDs(self, configuration, documentIds):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        args.setArray("documentIds", documentIds)
        self._client.invokeMethod("replicatorConfiguration_setDocumentIDs",
                                  args)

    def setPinnedServerCertificate(self, configuration, cert):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        args.setArray("cert", cert)
        self._client.invokeMethod("replicatorConfiguration_setPinnedServerCertificate",
                                  args)

    def setReplicatorType(self, configuration, replType):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        args.setMemoryPointer("replType", replType)
        self._client.invokeMethod("replicatorConfiguration_setReplicatorType",
                                  args)
