from CBLClient.Client import Client
from CBLClient.Args import Args


class ListenerAuthenticator(object):
    _client = None
    base_url = None

    def __init__(self, base_url):
        self.base_url = base_url

        # If no base url was specified, raise an exception
        if self.base_url is None:
            raise Exception("No base_url specified")

        self._client = Client(base_url)

    def create(self, username, password):
        args = Args()
        args.setString("username", username)
        args.setString("password", password)
        return self._client.invokeMethod("listenerAuthenticator_create", args)

    def listenerCertificateAuthenticator_create(self):
        args = Args()
        return self._client.invokeMethod("listenerCertificateAuthenticator_create",
                                         args)
