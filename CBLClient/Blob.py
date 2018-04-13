from CBLClient.Client import Client
from CBLClient.Args import Args


class Blob(object):
    _client = None

    def __init__(self, base_url):
        self.base_url = base_url

        # If no base url was specified, raise an exception
        if not self.base_url:
            raise Exception("No base_url specified")

        self._client = Client(base_url)

    def create(self, content_type, content=None,
               stream=None, file_url=None):
        args = Args()
        args.setString("contentType", content_type)
        if content:
            args.setArray("content", content)
        elif stream:
            args.setArray("stream", stream)
        elif file_url:
            args.setMemoryPointer("fileURL", file_url)
        else:
            raise Exception("Provide correct parameter")
        return self._client.invokeMethod("blob_create", args)

    def digest(self, obj):
        args = Args()
        args.setMemoryPointer("obj", obj)
        return self._client.invokeMethod("blob_digest", args)

    def fleeceEncode(self, obj, encoder, database):
        args = Args()
        args.setMemoryPointer("obj", obj)
        args.setMemoryPointer("encoder", encoder)
        args.setMemoryPointer("database", database)
        return self._client.invokeMethod("blob_fleeceEncode", args)

    def getContent(self, obj):
        args = Args()
        args.setMemoryPointer("obj", obj)
        return self._client.invokeMethod("blob_getContent", args)

    def getProperties(self, obj):
        args = Args()
        args.setMemoryPointer("obj", obj)
        return self._client.invokeMethod("blob_getProperties", args)

    def getContentStream(self, obj):
        args = Args()
        args.setMemoryPointer("obj", obj)
        return self._client.invokeMethod("blob_getContentStream", args)

    def getContentType(self, obj):
        args = Args()
        args.setMemoryPointer("obj", obj)
        return self._client.invokeMethod("blob_getContentType", args)

    def length(self, obj):
        args = Args()
        args.setMemoryPointer("obj", obj)
        return self._client.invokeMethod("blob_length", args)

    def toString(self, obj):
        args = Args()
        args.setMemoryPointer("obj", obj)
        return self._client.invokeMethod("blob_toString", args)
