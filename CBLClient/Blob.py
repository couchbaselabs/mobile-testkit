from CBLClient.Client import Client
from CBLClient.Args import Args

class Blob:
    _client = None
    _baseUrl = None

    def __init__(self, baseUrl):
        self.baseUrl = baseUrl

        # If no base url was specified, raise an exception
        if not self.baseUrl:
            raise Exception("No baseUrl specified")

        self._client = Client(baseUrl)

    def create(self, contentType, content=None,
               stream=None, fileURL = None):
        args = Args()
        args.setString("contentType", contentType)
        if content:
            args.setArray("content", content)
        elif stream:
            args.setArray("stream", stream)
        elif fileURL:
            args.setMemoryPointer("fileURL", fileURL)
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