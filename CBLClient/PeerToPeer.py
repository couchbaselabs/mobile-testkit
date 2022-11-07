from CBLClient.Client import Client
from CBLClient.Args import Args


class PeerToPeer(object):
    '''
    classdocs
    '''
    def __init__(self, base_url):
        '''
        Constructor
        '''
        self.base_url = base_url

        # If no base url was specified, raise an exception
        if not self.base_url:
            raise Exception("No base_url specified")
        self._client = Client(base_url)
        self.config = None

    def peer_intialize(self, database, continuous, host, port):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setBoolean("continuous", continuous)
        args.setInt("port", port)
        args.setString("host", host)
        return self._client.invokeMethod("peerToPeer_initialize", args)

    def start(self, peerToPeerObj):
        args = Args()
        args.setMemoryPointer("PeerToPeerImplementation", peerToPeerObj)
        return self._client.invokeMethod("peerToPeer_start", args)

    def stop(self, peerToPeerObj):
        args = Args()
        args.setMemoryPointer("PeerToPeerImplementation", peerToPeerObj)
        return self._client.invokeMethod("peerToPeer_stop", args)

    def stopSession(self):
        return self._client.invokeMethod("peerToPeer_stopSession")

    def create_connection(self):
        return self._client.invokeMethod("peerToPeer_createConnection")

    def socket_connection(self, port):
        args = Args()
        args.setInt("port", port)
        return self._client.invokeMethod("peerToPeer_socketConnection", args)

    def socket_clientConnection(self, host, port):
        args = Args()
        args.setString("host", host)
        args.setInt("port", port)
        return self._client.invokeMethod("peerToPeer_socketClientConnection", args)

    def accept_client(self, server):
        args = Args()
        args.setMemoryPointer("server", server)
        return self._client.invokeMethod("peerToPeer_acceptClient", args)

    def read_data_fromClient(self, socket):
        args = Args()
        args.setInt("socket", socket)
        return self._client.invokeMethod("peerToPeer_readDataFromClient", args)

    def server_start(self, database, port=0, basic_auth=None, tls_disable=True, tls_auth_type="tls", tls_authenticator=False, delta_sync=True):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setInt("port", port)
        if basic_auth is not None:
            args.setMemoryPointer("basic_auth", basic_auth)
        args.setBoolean("tls_disable", tls_disable)

        args.setString("tls_auth_type", tls_auth_type)
        args.setBoolean("tls_authenticator", tls_authenticator)
        args.setBoolean("enable_delta_sync", delta_sync)
        return self._client.invokeMethod("peerToPeer_serverStart", args)

    def message_listener_start(self, database, port=5000):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setInt("port", port)
        return self._client.invokeMethod("peerToPeer_messageEndpointListenerStart", args)

    def get_url_listener_port(self, url_listener):
        args = Args()
        args.setMemoryPointer("listener", url_listener)
        return self._client.invokeMethod("peerToPeer_getListenerPort", args)

    def server_stop(self, url_listener, end_point_type):
        args = Args()
        args.setMemoryPointer("listener", url_listener)
        args.setString("endPointType", end_point_type)
        return self._client.invokeMethod("peerToPeer_serverStop", args)

    def configure(self, host, server_db_name, client_database, port=5000, continuous=None, authenticator=None,
                  replication_type=None, documentIDs=None, endPointType="MessageEndPoint", basic_auth=None,
                  push_filter=False, pull_filter=False, filter_callback_func='', conflict_resolver="", tls_disable=True,
                  tls_auth_type="tls", tls_authenticator=False, server_verification_mode=False, retries=None,
                  max_timeout_interval=None, collections=None, collection_configuration=None):
        args = Args()
        args.setString("host", host)
        args.setInt("port", port)
        args.setString("serverDBName", server_db_name)
        args.setMemoryPointer("database", client_database)
        args.setBoolean("push_filter", push_filter)
        args.setBoolean("pull_filter", pull_filter)
        args.setString("filter_callback_func", filter_callback_func)
        args.setString("conflict_resolver", conflict_resolver)
        args.setBoolean("tls_enable", tls_disable)
        if authenticator is not None:
            args.setMemoryPointer("authenticator", authenticator)
        if replication_type is not None:
            args.setString("replicationType", replication_type)
        if continuous is not None:
            args.setBoolean("continuous", continuous)
        if documentIDs is not None:
            args.setArray("documentIDs", documentIDs)
        args.setArray("endPointType", endPointType)
        if basic_auth is not None:
            args.setMemoryPointer("basic_auth", basic_auth)
        if tls_disable is not None:
            args.setBoolean("tls_disable", tls_disable)
        if retries is not None:
            args.setString("max_retries", retries)
        if max_timeout_interval is not None:
            args.setString("max_timeout", max_timeout_interval)

        args.setString("tls_auth_type", tls_auth_type)
        args.setBoolean("tls_authenticator", tls_authenticator)
        args.setBoolean("server_verification_mode", server_verification_mode)
        if collections:
            args.setArray("collections", collections)
        if collection_configuration:
            args.setArray("collection_configuration", collection_configuration)
        return self._client.invokeMethod("peerToPeer_configure", args)

    def client_start(self, replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        return self._client.invokeMethod("peerToPeer_clientStart", args)

    def client_start_mep(self, host, server_db_name, client_database, continuous=None,
                         authenticator=None, replication_type=None):
        args = Args()
        args.setString("host", host)
        args.setString("serverDBName", server_db_name)
        args.setMemoryPointer("database", client_database)
        if authenticator is not None:
            args.setMemoryPointer("authenticator", authenticator)
        if replication_type is not None:
            args.setString("replication_type", replication_type)
        if continuous is not None:
            args.setBoolean("continuous", continuous)
        return self._client.invokeMethod("peerToPeer_clientStart_mep", args)

    def addReplicatorEventChangeListener(self, replicator):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        return self._client.invokeMethod("peerToPeer_addReplicatorEventChangeListener", args)

    def removeReplicatorEventListener(self, replicator, change_listener):
        args = Args()
        args.setMemoryPointer("replicator", replicator)
        args.setMemoryPointer("changeListener", change_listener)
        return self._client.invokeMethod("peerToPeer_removeReplicatorEventListener", args)

    def getReplicatorEventChanges(self, change_listener):
        args = Args()
        args.setMemoryPointer("changeListener", change_listener)
        return self._client.invokeMethod("peerToPeer_replicatorEventGetChanges", args)

    def getReplicatorEventChangesCount(self, change_listener):
        args = Args()
        args.setMemoryPointer("changeListener", change_listener)
        return self._client.invokeMethod("peerToPeer_replicatorEventChangesCount", args)
