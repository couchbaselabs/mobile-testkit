package com.couchbase.CouchbaseLiteServ.server.RequestHandler;


import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.CouchbaseLiteException;
import com.couchbase.lite.DataSource;
import com.couchbase.lite.Database;
import com.couchbase.lite.Expression;
import com.couchbase.lite.Meta;
import com.couchbase.lite.Query;
import com.couchbase.lite.Result;
import com.couchbase.lite.ResultSet;
import com.couchbase.lite.SelectResult;

import java.util.List;
import java.util.Map;

public class QueryRequestHandler {

   public Query select(Args args){
       SelectResult select_result = args.get("select_result");
       return Query.select(select_result);
   }

    public Query distinct(Args args){
        SelectResult select_result = args.get("select_prop");
        DataSource from_prop = args.get("from_prop");
        Expression whr_key_prop = args.get("whr_key_prop");
        return Query.select(select_result).from(from_prop).where(whr_key_prop);
    }

    public Query create(Args args){
        SelectResult select_result = args.get("select_result");
        return Query.select(select_result);
    }

    public ResultSet run(Args args) throws CouchbaseLiteException {
        Query query = args.get("query");
        return query.execute();
    }

    public Result nextResult(Args args){
        ResultSet query_result_set = args.get("query_result_set");
        return query_result_set.next();
    }

//    public Query string(Args args){
//        Result query_result = args.get("query_result");
//        String key = args.get("key");
//        return query_result.string(key);
//    }

    public Map<String, Object> getDoc(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        int out = database.getCount();
        String doc_id = args.get("doc_id");
        boolean check = database.contains(doc_id);
        Query search_query = Query
                .select(SelectResult.all())
                .from(DataSource.database(database))
                .where((Meta.id).equalTo(doc_id));
        ResultSet rows = search_query.execute();
        for (Result row : rows){
            return row.toMap();
        }
        return null;
    }

    public List<Object> docsLimitOffset(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        int limit = args.get("limit");
        int offset = args.get("offset");
        Query search_query = Query
                .select(SelectResult.all())
                .from(DataSource.database(database))
                .limit(limit, offset);
        List<Object> result_array = null;
        ResultSet rows = search_query.execute();
        for (Result row : rows){
            result_array.add(row);
        }
        return result_array;
    }

    public List<Object> multipleSelects(Args args) throws CouchbaseLiteException{
        Database database = args.get("database");
        String select_property1 = args.get("select_property1");
        String select_property2 = args.get("select_property2");
        String whr_key = args.get("whr_key");
        String whr_val = args.get("whr_val");

        Query search_query = Query
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(select_property1)),
                        SelectResult.expression(Expression.property(select_property2)))
                .from(DataSource.database(database))
                .where(Expression.property(whr_key).equalTo(whr_val));
        List<Object> result_array = null;
        ResultSet rows = search_query.execute();
        for (Result row : rows){
            result_array.add(row.toMap());
        }
        return result_array;
    }

}
