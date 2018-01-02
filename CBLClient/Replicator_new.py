from CBLClient.Client import Client
from CBLClient.Args import Args
from CBLClient.ReplicatorConfiguration import ReplicatorConfiguration

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
        self.config = None

    def create(self, config):
        args = Args()
        args.setMemoryPointer("config", config)
        return self._client.invokeMethod("replicator_create", args)

    def getConfig(self,replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        return self._client.invokeMethod("replicator_getConfig", args)

    def getStatus(self,replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        return self._client.invokeMethod("replicator_getStatus", args)

    def addChangeListener(self,replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        return self._client.invokeMethod("replicator_addChangeListener", args)

    def removeChangeListener(self,replicator, changeListener):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        args.setMemoryPointer("changeListener", changeListener)
        return self._client.invokeMethod("replicator_removeChangeListener", args)

    def toString(self,replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        return self._client.invokeMethod("replicator_toString", args)

    def networkReachable(self,replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        return self._client.invokeMethod("replicator_networkReachable", args)

    def networkUnreachable(self,replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        return self._client.invokeMethod("replicator_networkUnreachable", args)

    def start(self,replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        return self._client.invokeMethod("replicator_start", args)

    def stop(self,replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        return self._client.invokeMethod("replicator_stop", args)

    def configure(self,source_db, target_url=None, target_db=None,
                  replication_type="push_pull", continuous=False,
                  channels=None, documentIDs=None,
                  replicator_authenticator=None):
        args = Args()
        args.setString("replication_type", replication_type)
        repl_config_obj = ReplicatorConfiguration(self.baseUrl)
        if target_url:
            self.config = repl_config_obj.create(source_db, targetURI=target_url)
        elif target_db:
            self.config = repl_config_obj.create(source_db, targetDb=target_db)

        if channels is not None:
            repl_config_obj.setChannels(self.config, channels)

        if documentIDs is not None:
            repl_config_obj.setDocumentIDs(self.config, documentIDs)

        if replicator_authenticator is not None:
            repl_config_obj.setAuthenticator(self.config, replicator_authenticator)

        repl_config_obj.setContinuous(self.config, continuous)
        repl_config_obj.setReplicatorType(self.config, replication_type)
        return self.create(self.config)
