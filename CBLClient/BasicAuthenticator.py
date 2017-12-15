from CBLClient.Client import Client
from CBLClient.Args import Args

class BasicAuthenticator:
    _client = None
    _baseUrl = None

    def __init__(self, baseUrl):
        self.baseUrl = baseUrl

        # If no base url was specified, raise an exception
        if not self.baseUrl:
            raise Exception("No baseUrl specified")

        self._client = Client(baseUrl)

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