from CBLClient.Client import Client
from CBLClient.Args import Args
from keywords.utils import log_info


class Replication:
    _client = None
    _baseUrl = None

    def __init__(self, baseUrl):
        self.baseUrl = baseUrl

        # If no base url was specified, raise an exception
        if not self.baseUrl:
            raise Exception("No baseUrl specified")

        self._client = Client(baseUrl)

    def configure(self, source_db, target_url=None, target_db=None, replication_type="push_pull", continuous=False,
                  channels=None, documentIDs=None, replicator_authenticator=None, headers=None):
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
            args.setString("target_db", target_db)
            return self._client.invokeMethod("configure_replicator_local_db", args)

    def create(self, config):
        args = Args()
        args.setMemoryPointer("config", config)
        return self._client.invokeMethod("replicator_create", args)

    def authentication(self, session_id=None, cookie=None, username=None, password=None, authentication_type="basic"):
        args = Args()
        args.setString("authentication_type", authentication_type)
        if authentication_type == "session":
            args.setString("sessionId", session_id)
            args.setString("cookieName", cookie)
        else:
            args.setString("username", username)
            args.setString("password", password)
        return self._client.invokeMethod("replicator_create_authenticator", args)

    def start(self, replication_obj):
        args = Args()
        args.setMemoryPointer("replication_obj", replication_obj)

        self._client.invokeMethod("replicator_start", args)

    def stop(self, replication_obj):
        args = Args()
        args.setMemoryPointer("replication_obj", replication_obj)

        self._client.invokeMethod("replicator_stop", args)

    def status(self, replication_obj):
        args = Args()
        args.setMemoryPointer("replication_obj", replication_obj)

        return self._client.invokeMethod("replicator_status", args)

    def get_config(self, replication_obj):
        args = Args()
        args.setMemoryPointer("replication_obj", replication_obj)

        return self._client.invokeMethod("replicator_config", args)

    def get_completed(self, replication_obj):
        args = Args()
        args.setMemoryPointer("replication_obj", replication_obj)

        return self._client.invokeMethod("replicator_get_completed", args)

    def get_total(self, replication_obj):
        args = Args()
        args.setMemoryPointer("replication_obj", replication_obj)

        return self._client.invokeMethod("replicator_get_total", args)

    def get_activitylevel(self, replication_obj):
        args = Args()
        args.setMemoryPointer("replication_obj", replication_obj)
        
        return self._client.invokeMethod("replicator_get_activitylevel", args)

    def get_error(self, replication_obj):
        args = Args()
        args.setMemoryPointer("replication_obj", replication_obj)

        return self._client.invokeMethod("replicator_get_error", args)

    def add_change_listener(self, replication_obj):
        args = Args()
        args.setMemoryPointer("replication_obj", replication_obj)

        return self._client.invokeMethod("replicator_addChangeListener", args)

    def remove_change_listener(self, replication_obj, change_listener):
        args = Args()
        args.setMemoryPointer("replication_obj", replication_obj)
        args.setMemoryPointer("changeListener", change_listener)

        return self._client.invokeMethod("replicator_removeChangeListener", args)

    def get_changes_count(self, change_listener):
        args = Args()
        args.setMemoryPointer("changeListener", change_listener)

        return self._client.invokeMethod("replicatorChangeListener_changesCount", args)

    def get_changes_changelistener(self, change_listener, index):
        args = Args()
        args.setMemoryPointer("changeListener", change_listener)
        args.setInt("index", index)

        return self._client.invokeMethod("replicatorChangeListener_getChange", args)

    def conflict_resolver(self, conflict_type="giveup"):
        args = Args()
        args.setString("conflict_type", conflict_type)
        
        return self._client.invokeMethod("replicator_conflict_resolver", args)
