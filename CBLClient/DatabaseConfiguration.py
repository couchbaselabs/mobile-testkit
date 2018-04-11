from CBLClient.Client import Client
from CBLClient.Args import Args


class DatabaseConfiguration(object):
    _client = None

    def __init__(self, base_url):
        self.base_url = base_url

        # If no base url was specified, raise an exception
        if not self.base_url:
            raise Exception("No base_url specified")

        self._client = Client(base_url)
    """
    def create(self):
        args = Args()
        return self._client.invokeMethod("databaseConfiguration_create", args)
    """
    def getConflictResolver(self, config):
        args = Args()
        args.setMemoryPointer("config", config)
        return self._client.invokeMethod("databaseConfiguration_getConflictResolver",
                                         args)

    def getDirectory(self, config):
        args = Args()
        args.setMemoryPointer("config", config)
        return self._client.invokeMethod("databaseConfiguration_getDirectory",
                                         args)

    def getEncryptionKey(self, config):
        args = Args()
        args.setMemoryPointer("config", config)
        return self._client.invokeMethod("databaseConfiguration_getEncryptionKey",
                                         args)

    def setConflictResolver(self, config, conflict_resolver):
        args = Args()
        args.setMemoryPointer("config", config)
        args.setMemoryPointer("conflictResolver", conflict_resolver)
        return self._client.invokeMethod("databaseConfiguration_setConflictResolver",
                                         args)

    def setDirectory(self, config, directory):
        args = Args()
        args.setMemoryPointer("config", config)
        args.setMemoryPointer("directory", directory)
        return self._client.invokeMethod("databaseConfiguration_setDirectory",
                                         args)

    def setEncryptionKey(self, config, password):
        args = Args()
        args.setMemoryPointer("config", config)
        args.setMemoryPointer("password", password)
        return self._client.invokeMethod("databaseConfiguration_setEncryptionKey",
                                         args)
