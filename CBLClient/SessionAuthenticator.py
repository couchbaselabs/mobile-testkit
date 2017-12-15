from CBLClient.Client import Client
from CBLClient.Args import Args

class SessionAuthenticator:
    _client = None
    _baseUrl = None

    def __init__(self, baseUrl):
        self.baseUrl = baseUrl

        # If no base url was specified, raise an exception
        if not self.baseUrl:
            raise Exception("No baseUrl specified")

        self._client = Client(baseUrl)

    def create(self, sessionId, expires, cookieName):
        args = Args()
        args.setString("sessionId", sessionId)
        args.setString("cookieName", cookieName)
        args.setMemoryPointer("expires", expires)
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