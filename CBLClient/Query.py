from CBLClient.Client import Client
from CBLClient.Args import Args


class Query(object):
    _client = None

    def __init__(self, base_url):
        self.base_url = base_url

        # If no base url was specified, raise an exception
        if not self.base_url:
            raise Exception("No base_url specified")

        self._client = Client(base_url)

    ############
    # Collator #
    ############
    def query_collator_ascii(self, ignore_case):
        args = Args()
        args.setString("ignoreCase", ignore_case)

        return self._client.invokeMethod("collator_ascii", args)

    def query_collator_unicode(self, ignore_case, ignore_accents):
        args = Args()
        args.setString("ignoreCase", ignore_case)
        args.setString("ignoreAccents", ignore_accents)

        return self._client.invokeMethod("collator_unicode", args)

    def query_expression_property(self, prop):
        args = Args()
        args.setString("property", prop)

        return self._client.invokeMethod("expression_property", args)

    def query_datasource_database(self, database):
        args = Args()
        args.setString("database", database)

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

        return self._client.invokeMethod("query_nextResult", args)

    def query_result_string(self, query_result, key):
        args = Args()
        args.setString("query_result", query_result)
        args.setString("key", key)

        return self._client.invokeMethod("result_getString", args)

    def query_select_result_expression_create(self, expression):
        args = Args()
        args.setMemoryPointer("expression", expression)

        return self._client.invokeMethod("selectResult_expressionCreate", args)

    def query_select_result_all_create(self):
        return self._client.invokeMethod("selectResult_all")

    def query_expression_meta_id(self):
        return self._client.invokeMethod("expression_metaId")

    def query_expression_meta_sequence(self):
        return self._client.invokeMethod("expression_metaSequence")

    def create_equalTo_expression(self, expression1, expression2):
        args = Args()
        args.setMemoryPointer("expression1", expression1)
        args.setMemoryPointer("expression2", expression2)

        return self._client.invokeMethod("expression_createEqualTo", args)

    def create_and_expression(self, expression1, expression2):
        args = Args()
        args.setMemoryPointer("expression1", expression1)
        args.setMemoryPointer("expression2", expression2)

        return self._client.invokeMethod("expression_createAnd", args)

    def create_or_expression(self, expression1, expression2):
        args = Args()
        args.setMemoryPointer("expression1", expression1)
        args.setMemoryPointer("expression2", expression2)

        return self._client.invokeMethod("expression_createOr", args)

    def query_get_doc(self, database, doc_id):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("doc_id", doc_id)

        return self._client.invokeMethod("query_getDoc", args)

    def query_get_docs_limit_offset(self, database, limit, offset):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setInt("limit", limit)
        args.setInt("offset", offset)

        return self._client.invokeMethod("query_docsLimitOffset", args)

    def query_multiple_selects(self, database, select_property1, select_property2, whr_key, whr_val):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("select_property1", select_property1)
        args.setString("select_property2", select_property2)
        args.setString("whr_key", whr_key)
        args.setString("whr_val", whr_val)
        return self._client.invokeMethod("query_multipleSelects", args)

    def query_multiple_selects_forDoubleValue(self, database, select_property1, select_property2, whr_key, whr_val):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("select_property1", select_property1)
        args.setString("select_property2", select_property2)
        args.setString("whr_key", whr_key)
        args.setFloat("whr_val", whr_val)
        return self._client.invokeMethod("query_multipleSelectsDoubleValue", args)

    def query_multiple_selects_OrderByLocaleValue(self, database, select_property1, select_property2, whr_key, locale):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("select_property1", select_property1)
        args.setString("select_property2", select_property2)
        args.setString("whr_key", whr_key)
        args.setString("locale", locale)
        return self._client.invokeMethod("query_multipleSelectsOrderByLocaleValue", args)

    def query_where_and_or(self, database, whr_key1, whr_val1, whr_key2, whr_val2, whr_key3, whr_val3, whr_key4, whr_val4):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("whr_key1", whr_key1)
        args.setString("whr_val1", whr_val1)
        args.setString("whr_key2", whr_key2)
        args.setString("whr_val2", whr_val2)
        args.setString("whr_key3", whr_key3)
        args.setString("whr_val3", whr_val3)
        args.setString("whr_key4", whr_key4)
        args.setBoolean("whr_val4", whr_val4)

        return self._client.invokeMethod("query_whereAndOr", args)

    def query_like(self, database, whr_key, whr_val, select_property1, select_property2, like_key, like_val):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("whr_key", whr_key)
        args.setString("select_property1", select_property1)
        args.setString("select_property2", select_property2)
        args.setString("whr_val", whr_val)
        args.setString("like_key", like_key)
        args.setString("like_val", like_val)

        return self._client.invokeMethod("query_like", args)

    def query_regex(self, database, whr_key, whr_val, select_property1, select_property2, regex_key, regex_val):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("whr_key", whr_key)
        args.setString("select_property1", select_property1)
        args.setString("select_property2", select_property2)
        args.setString("whr_val", whr_val)
        args.setString("regex_key", regex_key)
        args.setString("regex_val", regex_val)

        return self._client.invokeMethod("query_regex", args)

    def query_isNullOrMissing(self, database, select_property1, limit):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("select_property1", select_property1)
        args.setInt("limit", limit)

        return self._client.invokeMethod("query_isNullOrMissing", args)

    def query_ordering(self, database, select_property1, whr_key, whr_val):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("select_property1", select_property1)
        args.setString("whr_key", whr_key)
        args.setString("whr_val", whr_val)

        return self._client.invokeMethod("query_ordering", args)

    def query_substring(self, database, select_property1, select_property2, substring):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("select_property1", select_property1)
        args.setString("select_property2", select_property2)
        args.setString("substring", substring)

        return self._client.invokeMethod("query_substring", args)

    def query_collation(self, database, select_property1, whr_key1, whr_val1, whr_key2, whr_val2, equal_to):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("select_property1", select_property1)
        args.setString("whr_key1", whr_key1)
        args.setString("whr_val1", whr_val1)
        args.setString("whr_key2", whr_key2)
        args.setString("whr_val2", whr_val2)
        args.setString("equal_to", equal_to)

        return self._client.invokeMethod("query_collation", args)

    def query_join(self, database, select_property1, select_property2,
                   select_property3, select_property4, select_property5,
                   whr_key1, whr_key2, whr_key3, whr_val1, whr_val2,
                   whr_val3, join_key):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("select_property1", select_property1)
        args.setString("select_property2", select_property2)
        args.setString("select_property3", select_property3)
        args.setString("select_property4", select_property4)
        args.setString("select_property5", select_property5)
        args.setString("whr_key1", whr_key1)
        args.setString("whr_key2", whr_key2)
        args.setString("whr_key3", whr_key3)
        args.setString("join_key", join_key)
        args.setString("whr_val1", whr_val1)
        args.setString("whr_val2", whr_val2)
        args.setString("whr_val3", whr_val3)

        return self._client.invokeMethod("query_join", args)

    def query_left_join(self, database, select_property, limit=100):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("select_property", select_property)
        args.setInt("limit", limit)

        return self._client.invokeMethod("query_leftJoin", args)

    def query_left_outer_join(self, database, select_property):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("select_property", select_property)

        return self._client.invokeMethod("query_leftOuterJoin", args)

    def query_inner_join(self, database, select_property1, select_property2,
                         select_property3, whr_key1, whr_key2, whr_val1, whr_val2,
                         join_key1, join_key2, limit=10):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("select_property1", select_property1)
        args.setString("select_property2", select_property2)
        args.setString("select_property3", select_property3)
        args.setString("join_key1", join_key1)
        args.setString("join_key2", join_key2)
        args.setString("whr_key1", whr_key1)
        args.setString("whr_key2", whr_key2)
        args.setString("whr_val1", whr_val1)
        args.setInt("whr_val2", whr_val2)
        args.setInt("limit", limit)

        return self._client.invokeMethod("query_innerJoin", args)

    def query_cross_join(self, database, select_property1, select_property2,
                         whr_key1, whr_key2, whr_val1, whr_val2, limit=10):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("select_property1", select_property1)
        args.setString("select_property2", select_property2)
        args.setString("whr_key1", whr_key1)
        args.setString("whr_key2", whr_key2)
        args.setString("whr_val1", whr_val1)
        args.setString("whr_val2", whr_val2)
        args.setInt("limit", limit)

        return self._client.invokeMethod("query_crossJoin", args)

    def query_between(self, database, prop, val1, val2):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("prop", prop)
        args.setInt("val1", val1)
        args.setInt("val2", val2)

        return self._client.invokeMethod("query_between", args)

    def query_equal_to(self, database, prop, val):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("prop", prop)
        args.setString("val", val)

        return self._client.invokeMethod("query_equalTo", args)

    def query_greater_than_or_equal_to(self, database, prop, val):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("prop", prop)
        args.setInt("val", val)

        return self._client.invokeMethod("query_greaterThanOrEqualTo", args)

    def query_greater_than(self, database, prop, val):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("prop", prop)
        args.setInt("val", val)

        return self._client.invokeMethod("query_greaterThan", args)

    def query_less_than(self, database, prop, val):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("prop", prop)
        args.setInt("val", val)

        return self._client.invokeMethod("query_lessThan", args)

    def query_less_than_or_equal_to(self, database, prop, val):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("prop", prop)
        args.setInt("val", val)

        return self._client.invokeMethod("query_lessThanOrEqualTo", args)

    def query_in(self, database, prop, val1, val2):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("prop", prop)
        args.setString("val1", val1)
        args.setString("val2", val2)
        return self._client.invokeMethod("query_in", args)

    def query_is(self, database, prop):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("prop", prop)

        return self._client.invokeMethod("query_is", args)

    def query_isNot(self, database, prop):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("prop", prop)

        return self._client.invokeMethod("query_isNot", args)

    def query_any_operator(self, database, schedule, departure, departure_prop, departure_val, whr_prop, whr_val):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("schedule", schedule)
        args.setString("departure", departure)
        args.setString("departure_prop", departure_prop)
        args.setString("departure_val", departure_val)
        args.setString("whr_prop", whr_prop)
        args.setString("whr_val", whr_val)

        return self._client.invokeMethod("query_anyOperator", args)

    def query_not(self, database, prop, val1, val2):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("prop", prop)
        args.setInt("val1", val1)
        args.setInt("val2", val2)

        return self._client.invokeMethod("query_not", args)

    def query_not_equal_to(self, database, prop, val):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("prop", prop)
        args.setString("val", val)

        return self._client.invokeMethod("query_notEqualTo", args)

    def query_single_property_fts(self, database, prop, val,
                                  doc_type, limit, stemming):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("prop", prop)
        args.setString("val", val)
        args.setString("doc_type", doc_type)
        args.setBoolean("stemming", stemming)
        args.setInt("limit", limit)

        return self._client.invokeMethod("query_singlePropertyFTS", args)

    def query_multiple_property_fts(self, database, prop1, prop2,
                                    val, doc_type, limit, stemming):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("prop1", prop1)
        args.setString("prop2", prop2)
        args.setString("val", val)
        args.setString("doc_type", doc_type)
        args.setBoolean("stemming", stemming)
        args.setInt("limit", limit)

        return self._client.invokeMethod("query_multiplePropertyFTS", args)

    def query_fts_with_ranking(self, database, prop, val,
                               doc_type, limit):
        args = Args()
        args.setMemoryPointer("database", database)
        args.setString("prop", prop)
        args.setString("val", val)
        args.setString("doc_type", doc_type)
        args.setInt("limit", limit)

        return self._client.invokeMethod("query_ftsWithRanking", args)

    def query_arthimetic(self, database):
        args = Args()
        args.setMemoryPointer("database", database)

        return self._client.invokeMethod("query_arthimetic", args)

    def release(self, obj):
        self._client.release(obj)

    def addChangeListener(self, query):
        args = Args()
        args.setMemoryPointer("query", query)
        return self._client.invokeMethod("query_addChangeListener", args)

    def removeChangeListener(self, query, change_listener):
        args = Args()
        args.setMemoryPointer("query", query)
        args.setMemoryPointer("changeListener", change_listener)
        return self._client.invokeMethod("query_removeChangeListener", args)

    def query_selectAll(self, database):
        args = Args()
        args.setMemoryPointer("database", database)
        return self._client.invokeMethod("query_selectAll", args)

    def query_get_live_query_delay_time(self, database):
        args = Args()
        args.setMemoryPointer("database", database)
        return self._client.invokeMethod("query_getLiveQueryResponseTime", args)
