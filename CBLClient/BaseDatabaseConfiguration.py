from CBLClient.Client import Client
from CBLClient.Args import Args

class BaseDatabaseConfiguration:
    _client = None
    _baseUrl = None

    def __init__(self, baseUrl):
        self.baseUrl = baseUrl

        # If no base url was specified, raise an exception
        if not self.baseUrl:
            raise Exception("No baseUrl specified")

        self._client = Client(baseUrl)

    def create(self):
        args = Args()
        return self._client.invokeMethod("baseDbConfig_create", args)

    def getConflictResolver(self, config):
        args = Args()
        args.setMemoryPointer("config", config)
        return self._client.invokeMethod("baseDbConfig_getConflictResolver",
                                          args)

    def getDirectory(self, config):
        args = Args()
        args.setMemoryPointer("config", config)
        return self._client.invokeMethod("baseDbConfig_getDirectory",
                                          args)

    def getEncryptionKey(self, config):
        args = Args()
        args.setMemoryPointer("config", config)
        return self._client.invokeMethod("baseDbConfig_getEncryptionKey",
                                          args)

    def setConflictResolver(self, config, conflictResolver):
        args = Args()
        args.setMemoryPointer("config", config)
        args.setMemoryPointer("conflictResolver", conflictResolver)
        return self._client.invokeMethod("baseDbConfig_setConflictResolver",
                                          args)

    def setDirectory(self, config, directory):
        args = Args()
        args.setMemoryPointer("config", config)
        args.setMemoryPointer("directory", directory)
        return self._client.invokeMethod("baseDbConfig_setDirectory",
                                          args)

    def setEncryptionKey(self, config, key):
        args = Args()
        args.setMemoryPointer("config", config)
        args.setMemoryPointer("key", key)
        return self._client.invokeMethod("baseDbConfig_setEncryptionKey",
                                          args)

