from CBLClient.Client import Client
from CBLClient.Args import Args


class EncryptionKey(object):
    _client = None

    def __init__(self, base_url):
        self.base_url = base_url

        # If no base url was specified, raise an exception
        if not self.base_url:
            raise Exception("No base_url specified")

        self._client = Client(base_url)

    def create(self, key, password):
        args = Args()
        if key:
            args.setArray("key", key)
        elif password:
            args.setArray("password", password)
        else:
            raise Exception("Incorrect parameters provided")
        return self._client.invokeMethod("encryptionKey_create", args)
