from CBLClient.Client import Client
from CBLClient.Args import Args


class VectorSearch(object):
    _client = None

    def __init__(self, base_url):

        self.base_url = base_url
        # If no base url was specified, raise an exception
        if not self.base_url:
            raise Exception("No base_url specified")

        self._client = Client(base_url)

    # TEMPORARY TEST FUNCTIONS
    def testTokenizer(self, input=None):
        args = Args()
        if input is not None:
            args.setString("input", input)
        return self._client.invokeMethod("vectorSearch_testTokeniser", args)

    def testDecode(self, input=None):
        args = Args()
        if input is not None:
            args.setString("input", input)
        return self._client.invokeMethod("vectorSearch_testDecode", args)

    # USEFUL FUNCTIONS
    def createIndex(self, database, scopeName, collectionName, indexName, expression,
                    dimensions, centroids, scalarEncoding=None, subquantizers=None, bits=None,
                    metric=None, minTrainingSize=None, maxTrainingSize=None, isLazy=None):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("collectionName", collectionName)
        args.setString("scopeName", scopeName)
        args.setString("indexName", indexName)
        args.setString("expression", expression)
        args.setInt("dimensions", dimensions)
        args.setInt("centroids", centroids)
        if scalarEncoding:
            args.setMemoryPointer("scalarEncoding", scalarEncoding)
        if subquantizers:
            args.setInt("subquantizers", subquantizers)
        if bits:
            args.setInt("bits", bits)
        if metric:
            args.setString("metric", metric)
        if minTrainingSize:
            args.setInt("minTrainingSize", minTrainingSize)
        if maxTrainingSize:
            args.setInt("maxTrainingSize", maxTrainingSize)
        if isLazy:
            args.setBoolean("isLazy", isLazy)
        return self._client.invokeMethod("vectorSearch_createIndex", args)

    def getEmbedding(self, input):
        args = Args()
        args.setString("input", input)
        return self._client.invokeMethod("vectorSearch_getEmbedding", args)

    def registerModel(self, key, name):
        args = Args()
        args.setString("key", key)
        args.setString("name", name)
        return self._client.invokeMethod("vectorSearch_registerModel", args)

    def query(self, term, sql, database):
        args = Args()
        args.setString("term", term)
        args.setString("sql", sql)
        args.setMemoryPointer("database", database)

        return self._client.invokeMethod("vectorSearch_query", args)

    def loadDatabase(self, dbPath=None):
        args = Args()
        if dbPath:
            args.setString("dbPath", dbPath)
        return self._client.invokeMethod("vectorSearch_loadDatabase", args)

    def regenerateWordEmbeddings(self):
        return self._client.invokeMethod("vectorSearch_regenerateWordEmbeddings")

    def register_model(self, key, name):
        args = Args()
        args.setString("key", key)
        args.setString("name", name)
        return self._client.invokeMethod("vectorSearch_registerModel", args)
