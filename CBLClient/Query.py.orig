from CBLClient.Client import Client
from CBLClient.Args import Args
from keywords.utils import log_info


class Query:
    _client = None
    _baseUrl = None

    def __init__(self, baseUrl):
        self.baseUrl = baseUrl

        # If no base url was specified, raise an exception
        if not self.baseUrl:
            raise Exception("No baseUrl specified")

        self._client = Client(baseUrl)

    ############
    # Collator #
    ############
    def query_collator_ascii(self, ignoreCase):
        args = Args()
        args.setString("ignoreCase", ignoreCase)

        #needs to be change
        #return self._client.invokeMethod("query_collator_ascii", args)
        return self._client.invokeMethod("collation_ascii", args)

    def query_collator_unicode(self, ignoreCase, ignoreAccents):
        args = Args()
        args.setString("ignoreCase", ignoreCase)
        args.setString("ignoreAccents", ignoreAccents)

        #needs to be change
        #return self._client.invokeMethod("query_collator_unicode", args)
        return self._client.invokeMethod("collation_unicode", args)

    def query_expression_property(self, prop):
        args = Args()
        args.setString("property", prop)

        #needs to be change
        #return self._client.invokeMethod("query_expression_property", args)
        return self._client.invokeMethod("expression_property", args)

    def query_datasource_database(self, database):
        args = Args()
        args.setString("database", database)

        #needs to be change
        #return self._client.invokeMethod("query_datasource_database", args)
        return self._client.invokeMethod("datasource_database", args)

    def query_create(self, select_prop, from_prop, whr_key_prop):
        args = Args()
        args.setString("select_prop", select_prop)
        args.setMemoryPointer("from_prop", from_prop)
        args.setString("whr_key_prop", whr_key_prop)

        return self._client.invokeMethod("query_create", args)

    def query_run(self, query):
        args = Args()
        args.setString("query", query)

        return self._client.invokeMethod("query_run", args)

    def query_next_result(self, query_result_set):
        args = Args()
        args.setString("query_result_set", query_result_set)

        #needs to be change
        #return self._client.invokeMethod("query_next_result", args)
        return self._client.invokeMethod("query_nextResult", args)


    def query_result_string(self, query_result, key):
        args = Args()
        args.setString("query_result", query_result)
        args.setString("key", key)

        #needs to be change
        #return self._client.invokeMethod("query_result_string", args)
        #There is no method string in Android API. I'm assumming this method is for getString
        return self._client.invokeMethod("result_getString", args) 

    def query_select_result_expression_create(self, expression):
        args = Args()
        args.setMemoryPointer("expression", expression)

        #needs to be change
        #return self._client.invokeMethod("query_select_result_expression_create", args)
        return self._client.invokeMethod("selectResult_expressionCreate", args)

    def query_select_result_all_create(self):
        #needs to be change
        #return self._client.invokeMethod("query_select_result_all_create")
        return self._client.invokeMethod("selectResult_all")

    def query_expression_meta_id(self):
        #needs to be change
        #return self._client.invokeMethod("query_expression_meta_id")
        return self._client.invokeMethod("expression_metaId")

    def query_expression_meta_sequence(self):
        #needs to be change
        #return self._client.invokeMethod("query_expression_meta_sequence")
        return self._client.invokeMethod("expression_metaSequence")

    def create_equalTo_expression(self, expression1, expression2):
        args = Args()
        args.setMemoryPointer("expression1", expression1)
        args.setMemoryPointer("expression2", expression2)

        #needs to be change
        #return self._client.invokeMethod("create_equalTo_expression", args)
        return self._client.invokeMethod("expression_createEqualTo", args)

    def create_and_expression(self, expression1, expression2):
        args = Args()
        args.setMemoryPointer("expression1", expression1)
        args.setMemoryPointer("expression2", expression2)

        #needs to be change
        #return self._client.invokeMethod("create_and_expression", args)
        return self._client.invokeMethod("expression_createAnd", args)

    def create_or_expression(self, expression1, expression2):
        args = Args()
        args.setMemoryPointer("expression1", expression1)
        args.setMemoryPointer("expression2", expression2)

        #needs to be change
        #return self._client.invokeMethod("create_or_expression", args)
        return self._client.invokeMethod("expression_createOr", args)

    def query_get_doc(self, database, doc_id):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("doc_id", doc_id)

        #needs to be change
        #return self._client.invokeMethod("query_get_doc", args)
        return self._client.invokeMethod("query_getDoc", args)

    def query_get_docs_limit_offset(self, database, limit, offset):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setInt("limit", limit)
        args.setInt("offset", offset)

        #needs to be change
        #return self._client.invokeMethod("query_get_docs_limit_offset", args)
        return self._client.invokeMethod("query_docsLimitOffset", args)

    def query_multiple_selects(self, database, select_property1, select_property2, whr_key, whr_val):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("select_property1", select_property1)
        args.setString("select_property2", select_property2)
        args.setString("whr_key", whr_key)
        args.setString("whr_val", whr_val)

        #needs to be change
        #return self._client.invokeMethod("query_multiple_selects", args)
        return self._client.invokeMethod("query_multipleSelects", args)
