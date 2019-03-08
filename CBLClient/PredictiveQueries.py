from CBLClient.Args import Args
from CBLClient.Client import Client


class PredictiveQueries(object):
    _db = None
    _baseUrl = None

    def __init__(self, base_url):
        self.base_url = base_url

        # If no base url was specified, raise an exception
        if not self.base_url:
            raise Exception("No base_url specified")

        self._client = Client(base_url)

    def registerModel(self, modelName):
        args = Args()
        args.setString("model_name", modelName)
        return self._client.invokeMethod("predictiveQuery_registerModel", args)

    def unregisterModel(self, modelName):
        args = Args()
        args.setString("model_name", modelName)
        return self._client.invokeMethod("predictiveQuery_unRegisterModel", args)

    def getPredictionQueryResult(self, model, dictionary, database):
        args = Args()
        args.setMemoryPointer("model", model)
        args.setMemoryPointer("dictionary", dictionary)
        args.setMemoryPointer("database", database)
        return self._client.invokeMethod("predictiveQuery_getPredictionQueryResult", args)

    def queryNonDictionaryInput(self, model, nonDictionary, database):
        args = Args()
        args.setMemoryPointer("model", model)
        args.setString("nonDictionary", nonDictionary)
        args.setMemoryPointer("database", database)
        return self._client.invokeMethod("predictiveQuery_nonDictionary", args)

    def getNumberOfCalls(self, model):
        args = Args()
        args.setMemoryPointer("model", model)
        return self._client.invokeMethod("predictiveQuery_getNumberOfCalls", args)

    def getEuclideanDistance(self, database, key1, key2):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("key1", key1)
        args.setString("key2", key2)
        return self._client.invokeMethod("predictiveQuery_getEuclideanDistance", args)

    def getSquaredEuclideanDistance(self, database, key1, key2):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("key1", key1)
        args.setString("key2", key2)
        return self._client.invokeMethod("predictiveQuery_getSquaredEuclideanDistance", args)

    def getCosineDistance(self, database, key1, key2):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("key1", key1)
        args.setString("key2", key2)
        return self._client.invokeMethod("predictiveQuery_getCosineDistance", args)
