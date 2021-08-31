from CBLClient.Client import Client
from CBLClient.Args import Args


class ReplicatorCallback(object):
    _client = None

    def __init__(self, base_url):
        self.base_url = base_url

        # If no base url was specified, raise an exception
        if not self.base_url:
            raise Exception("No base_url specified")

        self._client = Client(base_url)

    def create(self, type, encryptable_value, decrypted_value):
        args = Args()
        args.setString("decryptedValue", decrypted_value)
        if type == "array":
            args.setArray("encryptableValue", encryptable_value)
        elif type == "string":
            args.setString("encryptableValue", encryptable_value)
        elif type == "dic":
            args.setDictionary("encryptableValue", encryptable_value)
        else:
            raise Exception("Provide correct parameter")
        args.setString("type", type)
        return self._client.invokeMethod("encryptionCallback_create", args)

    def create_encryptor(self, doc_id, doc_data, key, doc_property, alg="xor"):
        args = Args()
        args.setString("id", doc_id)
        args.setString("algo", "xor")
        args.setString("doc_data", doc_data)
        args.setString("key", key)
        args.setString("doc_property", doc_property)
        return self._client.invokeMethod("encryptionCallback_encryptor", args)

    def create_decryptor(self, doc_id, doc_data, doc_property, key, alg="xor"):
        args = Args()
        args.setString("id", doc_id)
        args.setString("algo", "xor")
        args.setString("doc_data", doc_data)
        args.setString("key", key)
        args.setString("doc_property", doc_property)
        return self._client.invokeMethod("encryptionCallback_decryptor", args)

    def get_encryptable_value(self, encryptable_value):
        args = Args()
        args.setString("encryptableValue", encryptable_value)
        return self._client.invokeMethod("encryptionCallback_getEncryptableValue", args)

    def set_encryptable_value(self, encryptable_value):
        args = Args()
        args.setMemoryPointer("encryptedValue", encryptable_value)
        return self._client.invokeMethod("encryptionCallback_setEncryptableValue", args)

    def is_encryptable_value(self, encryptable_value):
        args = Args()
        args.setString("encryptableValue", encryptable_value)
        return self._client.invokeMethod("encryptionCallback_isEncryptableValue", args)