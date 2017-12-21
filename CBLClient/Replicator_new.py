from CBLClient.Client import Client
from CBLClient.Args import Args

class Replicator(object):
    '''
    classdocs
    '''


    def __init__(self, baseUrl):
        '''
        Constructor
        '''
        self.baseUrl = baseUrl

        # If no base url was specified, raise an exception
        if not self.baseUrl:
            raise Exception("No baseUrl specified")
        self._client = Client(baseUrl)

    def create(self, config):
        args = Args()
        args.setMemoryPointer("config", config)
        self._client.invokeMethod("replicator_create", args)

    def getConfig(self,replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        self._client.invokeMethod("replicator_getConfig", args)

    def getStatus(self,replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        self._client.invokeMethod("replicator_getStatus", args)

    def addChangeListener(self,replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        self._client.invokeMethod("replicator_addChangeListener", args)

    def removeChangeListener(self,replicator, changeListener):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        args.setMemoryPointer("changeListener", changeListener)
        self._client.invokeMethod("replicator_removeChangeListener", args)

    def toString(self,replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        self._client.invokeMethod("replicator_toString", args)

    def networkReachable(self,replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        self._client.invokeMethod("replicator_networkReachable", args)

    def networkUnreachable(self,replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        self._client.invokeMethod("replicator_networkUnreachable", args)

    def start(self,replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        self._client.invokeMethod("replicator_start", args)

    def stop(self,replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        self._client.invokeMethod("replicator_stop", args)
