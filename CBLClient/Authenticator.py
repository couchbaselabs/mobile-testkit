from CBLClient.Client import Client
from CBLClient.Args import Args


class Authenticator(object):
    _client = None
    base_url = None

    def __init__(self, base_url, auth=None):
        self.base_url = base_url
        self.auth=auth # A tuple of name/password
        # If no base url was specified, raise an exception
        if self.base_url is None:
            raise Exception("No base_url specified")

        self._client = Client(base_url)

    def basicAuthenticator_create(self, username, password):
        args = Args()
        args.setString("username", username)
        args.setString("password", password)
        return self._client.invokeMethod("basicAuthenticator_create", args, auth=self.auth)

    def proxyAuthenticator_create(self, username, password):
        args = Args()
        args.setString("username", username)
        args.setString("password", password)
        return self._client.invokeMethod("proxyAuthenticator_create", args, auth=self.auth)

    def basicAuthenticator_getPassword(self, authenticator):
        args = Args()
        args.setMemoryPointer("authenticator", authenticator)
        return self._client.invokeMethod("basicAuthenticator_getPassword", args)

    def basicAuthenticator_getUsername(self, authenticator):
        args = Args()
        args.setMemoryPointer("authenticator", authenticator)
        return self._client.invokeMethod("basicAuthenticator_getUsername", args)

    def sessionAuthenticator_create(self, session_id, cookie_name):
        args = Args()
        args.setString("sessionId", session_id)
        args.setString("cookieName", cookie_name)
        return self._client.invokeMethod("sessionAuthenticator_create", args)

    def sessionAuthenticator_getSessionId(self, session):
        args = Args()
        args.setMemoryPointer("session", session)
        return self._client.invokeMethod("sessionAuthenticator_getSessionId", args)

    def sessionAuthenticator_getCookieName(self, session):
        args = Args()
        args.setMemoryPointer("session", session)
        return self._client.invokeMethod("sessionAuthenticator_getCookieName", args)

    def authentication(self, session_id=None, cookie=None, username=None, password=None, authentication_type="basic"):
        args = Args()
        args.setString("authentication_type", authentication_type)
        if authentication_type == "session":
            return self.sessionAuthenticator_create(session_id, cookie)
        elif authentication_type == "proxy":
            return self.proxyAuthenticator_create(username, password)
        else:
            return self.basicAuthenticator_create(username, password)