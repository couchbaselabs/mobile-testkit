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

    def create(self, type, encryptable_value):
        args = Args()
        args.setString("type", type)

        if type == "String":
            args.setString("encrytableValue", encryptable_value)
        elif type == "Array":
            args.setMemoryPointer("encryptableValue", encryptable_value)
        elif type == "Bool":
            args.setBoolean("encryptableValue", encryptable_value)
        elif type == "Float":
            args.setFloat("encryptableValue", encryptable_value)
        elif type == "Dict":
            args.setString("encryptableValue", encryptable_value)
        elif type == "Int":
            args.setInt("encryptableValue", encryptable_value)
        elif type == "UInt":
            args.setInt("encryptableValue", encryptable_value)
        elif type == "Double":
            args.setFloat("encryptableValue", encryptable_value)
        else:
            raise Exception("Provide correct parameter")
        return self._client.invokeMethod("encryptable_createValue", args)

    def createEncryptor(self, algo="xor", key="testkit"):
        args = Args()
        args.setString("algo", algo)
        args.setString("key", key)
        return self._client.invokeMethod("encryptable_createEncryptor", args)

    def get_encryptable_value(self, encryptable_value):
        args = Args()
        args.setString("encryptableValue", encryptable_value)
        return self._client.invokeMethod("encryptable_getEncryptableValue", args)

    def set_encryptable_value(self, encryptable_value):
        args = Args()
        args.setMemoryPointer("encryptedValue", encryptable_value)
        return self._client.invokeMethod("encryptable_setEncryptableValue", args)

    def is_encryptable_value(self, encryptable_value):
        args = Args()
        args.setString("encryptableValue", encryptable_value)
        return self._client.invokeMethod("encryptable_isEncryptableValue", args)