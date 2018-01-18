import time

from CBLClient.Client import Client
from CBLClient.Args import Args
from CBLClient.ReplicatorConfiguration import ReplicatorConfiguration
from keywords.utils import log_info


class Replication(object):
    _client = None
    _baseUrl = None

    def __init__(self, baseUrl):
        self._baseUrl = baseUrl

        # If no base url was specified, raise an exception
        if not self._baseUrl:
            raise Exception("No baseUrl specified")

        self._client = Client(baseUrl)
        self.config = None

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
            args.setMemoryPointer("target_db", target_db)
            return self._client.invokeMethod("replicator_configureLocalDb", args)

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

    def getConfig(self, replication_obj):
        args = Args()
        args.setMemoryPointer("replication_obj", replication_obj)

        return self._client.invokeMethod("replicator_config", args)

    def getCompleted(self, replication_obj):
        args = Args()
        args.setMemoryPointer("replication_obj", replication_obj)

        return self._client.invokeMethod("replicator_getCompleted", args)

    def getTotal(self, replication_obj):
        args = Args()
        args.setMemoryPointer("replication_obj", replication_obj)

        return self._client.invokeMethod("replicator_getTotal", args)

    def getActivitylevel(self, replication_obj):
        args = Args()
        args.setMemoryPointer("replication_obj", replication_obj)
        
        return self._client.invokeMethod("replicator_getActivityLevel", args)

    def getError(self, replication_obj):
        args = Args()
        args.setMemoryPointer("replication_obj", replication_obj)
        error = self._client.invokeMethod("replicator_getError", args)
        if error.__contains__("@"):
            error = None
        return self._client.invokeMethod("replicator_getError", args)

    def addChangeListener(self, replication_obj):
        args = Args()
        args.setMemoryPointer("replication_obj", replication_obj)

        return self._client.invokeMethod("replicator_addChangeListener", args)

    def removeChangeListener(self, replication_obj, change_listener):
        args = Args()
        args.setMemoryPointer("replication_obj", replication_obj)
        args.setMemoryPointer("changeListener", change_listener)

        return self._client.invokeMethod("replicator_removeChangeListener", args)

    def getChangesCount(self, change_listener):
        args = Args()
        args.setMemoryPointer("changeListener", change_listener)

        return self._client.invokeMethod("replicatorChangeListener_changesCount", args)

    def getChangesChangeListener(self, change_listener):
        args = Args()
        args.setMemoryPointer("changeListener", change_listener)
        # args.setInt("index", index)

        return self._client.invokeMethod("replicatorChangeListener_getChanges", args)

    def conflictResolver(self, conflict_type="giveup"):
        args = Args()
        args.setString("conflict_type", conflict_type)
        
        return self._client.invokeMethod("replicator_conflict_resolver", args)

    def configure_and_replicate(self, source_db, replicator, replicator_authenticator, target_db=None, target_url=None, replication_type="push_pull", continuous=True,
                                channels=None):
        if target_db is None:
            repl_config = replicator.configure(source_db, target_url=target_url, continuous=continuous,
                                               replication_type=replication_type, channels=channels, replicator_authenticator=replicator_authenticator)
        else:
            repl_config = replicator.configure(source_db, target_db=target_db, continuous=continuous,
                                               replication_type=replication_type, channels=channels, replicator_authenticator=replicator_authenticator)
        repl = replicator.create(repl_config)
        replicator.start(repl)
        self.wait_until_replicator_idle(repl)
        return repl

    def wait_until_replicator_idle(self, repl):
        max_times = 10
        count = 0
        # Sleep until replicator completely processed
        while(self.getActivitylevel(repl) != 3 and count < max_times):
            print "sleeping... actvity level is", self.getActivitylevel(repl)
            time.sleep(0.5)
            if self.getActivitylevel(repl) == 3 or self.getActivitylevel(repl) == 1 or self.getActivitylevel(repl) == 2:
                count += 1
            if self.getActivitylevel(repl) == 0:
                break

    def create_session_configure_replicate(self, baseUrl, sg_admin_url, sg_db, username, password,
                                           channels, sg_client, cbl_db, sg_blip_url, replication_type):
        sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels)
        cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
        session = cookie, session_id
        replicator_authenticator = self.authentication(session_id, cookie, authentication_type="session")
        repl_config = self.configure(cbl_db, sg_blip_url, continuous=True, channels=channels, replication_type=replication_type, replicator_authenticator=replicator_authenticator)
        repl = self.create(repl_config)
        self.start(repl)
        self.wait_until_replicator_idle(repl)

        return session, replicator_authenticator, repl
