import time

from CBLClient.Client import Client
from CBLClient.Args import Args
from CBLClient.ReplicatorConfiguration import ReplicatorConfiguration
from CBLClient.Authenticator import Authenticator
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

    def create(self, config):
        args = Args()
        args.setMemoryPointer("config", config)
        return self._client.invokeMethod("replicator_create", args)

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
        replicatorConfiguration = ReplicatorConfiguration(self._baseUrl)
        if target_db is None:
            repl_config = replicatorConfiguration.configure(source_db, target_url=target_url, continuous=continuous,
                                                            replication_type=replication_type, channels=channels, replicator_authenticator=replicator_authenticator)
        else:
            repl_config = replicatorConfiguration.configure(source_db, target_db=target_db, continuous=continuous,
                                                            replication_type=replication_type, channels=channels, replicator_authenticator=replicator_authenticator)
        repl = self.create(repl_config)
        replicator.start(repl)
        self.wait_until_replicator_idle(repl)
        return repl

    def wait_until_replicator_idle(self, repl):
        max_times = 10
        count = 0
        # Sleep until replicator completely processed
        while self.getActivitylevel(repl) != 3 and count < max_times:
            print "sleeping... actvity level is", self.getActivitylevel(repl)
            time.sleep(0.5)
            if self.getActivitylevel(repl) == 3 or self.getActivitylevel(repl) == 1 or self.getActivitylevel(repl) == 2:
                count += 1
            if self.getActivitylevel(repl) == 0:
                break

    def create_session_configure_replicate(self, sg_admin_url, sg_db, username, password,
                                           channels, sg_client, cbl_db, sg_blip_url, replication_type, continuous=True):

        authenticator = Authenticator(self._baseUrl)
        replicatorConfiguration = ReplicatorConfiguration(self._baseUrl)
        sg_client.create_user(sg_admin_url, sg_db, username, password, channels=channels)
        cookie, session_id = sg_client.create_session(sg_admin_url, sg_db, "autotest")
        session = cookie, session_id
        replicator_authenticator = authenticator.authentication(session_id, cookie, authentication_type="session")
        repl_config = replicatorConfiguration.configure(cbl_db, sg_blip_url, continuous=continuous, channels=channels, replication_type=replication_type, replicator_authenticator=replicator_authenticator)
        repl = self.create(repl_config)
        self.start(repl)
        self.wait_until_replicator_idle(repl)

        return session, replicator_authenticator, repl
