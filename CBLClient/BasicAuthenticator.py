from CBLClient.Client import Client
from CBLClient.Args import Args


class BasicAuthenticator(object):
    _client = None

    def __init__(self, base_url):
        self.base_url = base_url

        # If no base url was specified, raise an exception
        if not self.base_url:
            raise Exception("No base_url specified")

        self._client = Client(base_url)

    def create(self, username, password):
        args = Args()
        args.setString("username", username)
        args.setString("password", password)
        return self._client.invokeMethod("basicAuthenticator_create",
                                         args)

    def getPassword(self, authenticator):
        args = Args()
        args.setMemoryPointer("authenticator", authenticator)
        return self._client.invokeMethod("basicAuthenticator_getPassword",
                                         args)

    def getUsername(self, authenticator):
        args = Args()
        args.setMemoryPointer("authenticator", authenticator)
        return self._client.invokeMethod("basicAuthenticator_getUsername",
                                         args)
