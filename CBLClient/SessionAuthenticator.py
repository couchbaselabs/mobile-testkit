from CBLClient.Client import Client
from CBLClient.Args import Args


class SessionAuthenticator(object):
    _client = None

    def __init__(self, base_url):
        self.base_url = base_url

        # If no base url was specified, raise an exception
        if not self.base_url:
            raise Exception("No base_url specified")

        self._client = Client(base_url)

    def create(self, session_id, expires, cookie_name):
        args = Args()
        args.setString("sessionId", session_id)
        args.setString("cookieName", cookie_name)
        args.setLong("expires", expires)
        return self._client.invokeMethod("sessionAuthenticator_create",
                                         args)

    def getSessionId(self, session):
        args = Args()
        args.setMemoryPointer("session", session)
        return self._client.invokeMethod("sessionAuthenticator_getSessionId",
                                         args)

    def getCookieName(self, session):
        args = Args()
        args.setMemoryPointer("session", session)
        return self._client.invokeMethod("sessionAuthenticator_getCookieName",
                                         args)

    def getExpires(self, session):
        args = Args()
        args.setMemoryPointer("session", session)
        return self._client.invokeMethod("sessionAuthenticator_getExpires",
                                         args)
