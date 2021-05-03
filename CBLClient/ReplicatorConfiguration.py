import os

from CBLClient.Client import Client
from CBLClient.Args import Args
from utilities.cluster_config_utils import sg_ssl_enabled


class ReplicatorConfiguration(object):
    _client = None
    baseUrl = None

    def __init__(self, base_url):
        self.base_url = base_url

        # If no base url was specified, raise an exception
        if not self.base_url:
            raise Exception("No base_url specified")

        self._client = Client(base_url)

    def configure(self, source_db, target_url=None, target_db=None, replication_type="push_pull", continuous=False,
                  channels=None, documentIDs=None, replicator_authenticator=None, headers=None, max_timeout_interval=None, retries=None):
        args = Args()
        args.setMemoryPointer("source_db", source_db)
        args.setString("replication_type", replication_type)
        args.setBoolean("continuous", continuous)
        if channels is not None:
            args.setArray("channels", channels)
        if documentIDs is not None:
            args.setArray("documentIDs", documentIDs)
        if replicator_authenticator is not None:
            args.setMemoryPointer("authenticator", replicator_authenticator)
        if headers is not None:
            args.setDictionary("headers", headers)
        if target_db is None:
            args.setString("target_url", target_url)
            return self._client.invokeMethod("replicator_configureRemoteDbUrl", args)
        else:
            args.setMemoryPointer("target_db", target_db)
            return self._client.invokeMethod("replicator_configureLocalDb", args)

        cluster_config = os.environ["CLUSTER_CONFIG"]
        if sg_ssl_enabled(cluster_config):
            args.setString("pinnedservercert", "sg_cert")

        if retries is not None:
            args.setString("max_retries", retries)
        if max_timeout_interval is not None:
            args.setString("max_timeout", max_timeout_interval)


    def builderCreate(self, source_db, target_db=None, target_url=None):
        args = Args()
        args.setMemoryPointer("sourceDb", source_db)
        if target_db:
            args.setMemoryPointer("targetDb", target_db)
        elif target_url:
            args.setMemoryPointer("targetURI", target_url)
        else:
            raise Exception("Pass either target_db or target_url.")
        return self._client.invokeMethod("replicatorConfiguration_builderCreate", args)

    def create(self, replicatorBuilder):
        args = Args()
        args.setMemoryPointer("replicatorBuilder", replicatorBuilder)
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
        return self._client.invokeMethod("replicatorConfiguration_getConflictResolver",
                                         args)

    def getDatabase(self, configuration):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        return self._client.invokeMethod("replicatorConfiguration_getDatabase",
                                         args)

    def getDocumentIDs(self, configuration):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        return self._client.invokeMethod("replicatorConfiguration_getDocumentIDs",
                                         args)

    def getPinnedServerCertificate(self, configuration):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        return self._client.invokeMethod("replicatorConfiguration_getPinnedServerCertificate",
                                         args)

    def getReplicatorType(self, configuration):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        return self._client.invokeMethod("replicatorConfiguration_getReplicatorType",
                                         args)

    def getTarget(self, configuration):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        return self._client.invokeMethod("replicatorConfiguration_getTarget", args)

    def isContinuous(self, configuration):
        args = Args()
        args.setMemoryPointer("configuration", configuration)
        return self._client.invokeMethod("replicatorConfiguration_isContinuous",
                                         args)

    def setAuthenticator(self, replicator_builder, authenticator):
        args = Args()
        args.setMemoryPointer("replicatorBuilder", replicator_builder)
        args.setMemoryPointer("authenticator", authenticator)
        return self._client.invokeMethod("replicatorConfiguration_setAuthenticator",
                                         args)

    def setChannels(self, replicator_builder, channels):
        args = Args()
        args.setMemoryPointer("replicatorBuilder", replicator_builder)
        args.setArray("channels", channels)
        return self._client.invokeMethod("replicatorConfiguration_setChannels",
                                         args)

    def setConflictResolver(self, replicator_builder, conflict_resolver):
        args = Args()
        args.setMemoryPointer("replicatorBuilder", replicator_builder)
        args.setMemoryPointer("conflictResolver", conflict_resolver)
        return self._client.invokeMethod("replicatorConfiguration_setConflictResolver",
                                         args)

    def setContinuous(self, replicator_builder, continuous):
        args = Args()
        args.setMemoryPointer("replicatorBuilder", replicator_builder)
        args.setBoolean("continuous", continuous)
        return self._client.invokeMethod("replicatorConfiguration_setContinuous",
                                         args)

    def setDocumentIDs(self, replicator_builder, document_ids):
        args = Args()
        args.setMemoryPointer("replicatorBuilder", replicator_builder)
        args.setArray("documentIds", document_ids)
        return self._client.invokeMethod("replicatorConfiguration_setDocumentIDs",
                                         args)

    def setPinnedServerCertificate(self, replicator_builder, cert):
        args = Args()
        args.setMemoryPointer("replicatorBuilder", replicator_builder)
        args.setArray("cert", cert)
        return self._client.invokeMethod("replicatorConfiguration_setPinnedServerCertificate",
                                         args)

    def setReplicatorType(self, replicator_builder, repl_type):
        args = Args()
        args.setMemoryPointer("replicatorBuilder", replicator_builder)
        args.setMemoryPointer("replType", repl_type)
        return self._client.invokeMethod("replicatorConfiguration_setReplicatorType",
                                         args)
