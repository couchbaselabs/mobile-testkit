from CBLClient.Client import Client
from CBLClient.Args import Args

class EncryptionKey:
    _client = None
    _baseUrl = None

    def __init__(self, baseUrl):
        self.baseUrl = baseUrl

        # If no base url was specified, raise an exception
        if not self.baseUrl:
            raise Exception("No baseUrl specified")

        self._client = Client(baseUrl)

    def create(self, key, password):
        args = Args()
        if key:
            args.setArray("key", key)
        elif password:
            args.setArray("password", password)
        else:
            raise Exception("Incorrect parameters provided")
        return self._client.invokeMethod("encryptionKey_create", args)