package com.couchbase.CouchbaseLiteServ.server.RequestHandler;


import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.Collation;
import com.couchbase.lite.CouchbaseLiteException;
import com.couchbase.lite.DataSource;
import com.couchbase.lite.Database;
import com.couchbase.lite.Expression;
import com.couchbase.lite.Function;
import com.couchbase.lite.Meta;
import com.couchbase.lite.Ordering;
import com.couchbase.lite.Query;
import com.couchbase.lite.Result;
import com.couchbase.lite.ResultSet;
import com.couchbase.lite.SelectResult;

import java.util.ArrayList;
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
        Expression whr_key_prop = Expression.value(args.get("whr_key_prop"));
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
        Expression doc_id = Expression.value(args.get("doc_id"));
        Query query = Query
                .select(SelectResult.all())
                .from(DataSource.database(database))
                .where((Meta.id).equalTo(doc_id));
        for (Result row : query.execute()){
            return row.toMap();
        }
        return null;
    }

    public List<Object> docsLimitOffset(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        Expression limit = Expression.value(args.get("limit"));
        Expression offset = Expression.value(args.get("offset"));
        Query search_query = Query
                .select(SelectResult.all())
                .from(DataSource.database(database))
                .limit(limit, offset);
        List<Object> resultArray = new ArrayList<Object>();
        ResultSet rows = search_query.execute();
        for (Result row : rows){
            resultArray.add(row);
        }
        return resultArray;
    }

    public List<Object> multipleSelects(Args args) throws CouchbaseLiteException{
        Database database = args.get("database");
        String select_property1 = args.get("select_property1");
        String select_property2 = args.get("select_property2");
        String whr_key = args.get("whr_key");
        Expression whr_val = Expression.value(args.get("whr_val"));

        Query search_query = Query
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(select_property1)),
                        SelectResult.expression(Expression.property(select_property2)))
                .from(DataSource.database(database))
                .where(Expression.property(whr_key).equalTo(whr_val));
        List<Object> resultArray = new ArrayList<Object>();
        ResultSet rows = search_query.execute();
        for (Result row : rows){
            resultArray.add(row.toMap());
        }
        return resultArray;
    }

    public List<Object> whereAndOr(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        String whr_key1 = args.get("whr_key1");
        String whr_key2 = args.get("whr_key2");
        String whr_key3 = args.get("whr_key3");
        String whr_key4 = args.get("whr_key4");
        Expression whr_val1 = Expression.value(args.get("whr_val1"));
        Expression whr_val2 = Expression.value(args.get("whr_val2"));
        Expression whr_val3 = Expression.value(args.get("whr_val3"));
        Expression whr_val4 = Expression.value(args.get("whr_val4"));
        List<Object> resultArray = new ArrayList<Object>();
        Query query = Query
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(database))
                .where(Expression.property(whr_key1).equalTo(whr_val1)
                        .and(Expression.property(whr_key2).equalTo(whr_val2)
                                .or(Expression.property(whr_key3).equalTo(whr_val3)))
                        .and(Expression.property(whr_key4).equalTo(whr_val4)));
        for (Result row : query.execute()){
            resultArray.add(row.toMap());
        }
        return resultArray;
    }

    public List<Object> like(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        int out = database.getCount();
        String whr_key = args.get("whr_key");
        String select_property1 = args.get("select_property1");
        String select_property2 = args.get("select_property2");
        String like_key = args.get("like_key");
        Expression whr_val = Expression.value(args.get("whr_val"));
        Expression like_val = Expression.value(args.get("like_val"));
        List<Object> resultArray = new ArrayList<Object>();
        Query query = Query
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(select_property1)),
                        SelectResult.expression(Expression.property(select_property2)))
                .from(DataSource.database(database))
                .where(Expression.property(whr_key).equalTo(whr_val)
                        .and(Expression.property(like_key).like(like_val)));
        for (Result row : query.execute()){
            resultArray.add(row.toMap());
        }
        return resultArray;
    }

    public List<Object> regex(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        String whr_key = args.get("whr_key");
        String select_property1 = args.get("select_property1");
        String select_property2 = args.get("select_property2");
        String regex_key = args.get("regex_key");
        Expression whr_val = Expression.value(args.get("whr_val"));
        Expression regex_val = Expression.value(args.get("regex_val"));
        List<Object> resultArray = new ArrayList<Object>();
        Query query = Query
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(select_property1)),
                        SelectResult.expression(Expression.property(select_property2)))
                .from(DataSource.database(database))
                .where(Expression.property(whr_key).equalTo(whr_val)
                        .and(Expression.property(regex_key).regex(regex_val)));
        for (Result row : query.execute()){
            resultArray.add(row.toMap());
        }
        return resultArray;
    }

    public List<Object> ordering(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        String whr_key = args.get("whr_key");
        String select_property1 = args.get("select_property1");
        Expression whr_val = Expression.value(args.get("whr_val"));
        List<Object> resultArray = new ArrayList<Object>();
        Query query = Query
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(select_property1)))
                .from(DataSource.database(database))
                .where(Expression.property(whr_key).equalTo(whr_val))
                .orderBy(Ordering.property(select_property1).ascending());
        for (Result row : query.execute()){
            resultArray.add(row.toMap());
        }
        return resultArray;
    }

    public List<Object> substring(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        String select_property1 = args.get("select_property1");
        String select_property2 = args.get("select_property2");
        Expression substring = Expression.value(args.get("substring"));
        List<Object> resultArray = new ArrayList<Object>();
        Query query = Query
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(select_property1)),
                        SelectResult.expression(Expression.property(select_property2)))
                .from(DataSource.database(database))
                .where((Function.contains(Expression.property(select_property1), substring)));
        for (Result row : query.execute()){
            resultArray.add(row.toMap());
        }
        return resultArray;
    }

    public List<Object> isNullOrMissing(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        String select_property1 = args.get("select_property1");
        Expression limit = Expression.value(args.get("limit"));
        List<Object> resultArray = new ArrayList<Object>();
        Query query = Query
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(select_property1)))
                .from(DataSource.database(database))
                .where(Expression.property(select_property1).isNullOrMissing())
                .limit(limit);
        for (Result row : query.execute()){
            resultArray.add(row.toMap());
        }
        return resultArray;
    }

    public List<Object> collation(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        String select_property1 = args.get("select_property1");
        String whr_key1 = args.get("whr_key1");
        String whr_key2 = args.get("whr_key2");
        Expression whr_val1 = Expression.value(args.get("whr_val1"));
        Expression whr_val2 = Expression.value(args.get("whr_val2"));
        Expression equal_to = Expression.value(args.get("equal_to"));
        List<Object> resultArray = new ArrayList<Object>();

        Collation collation = Collation.unicode()
                .ignoreAccents(true)
                .ignoreCase(true);
        Query query = Query
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(select_property1)))
                .from(DataSource.database(database))
                .where(Expression.property(whr_key1).equalTo(whr_val1)
                        .and(Expression.property(whr_key2).equalTo(whr_val2)
                        .and(Expression.property(select_property1).collate(collation).equalTo(equal_to))));
        for (Result row : query.execute()){
            resultArray.add(row.toMap());
        }
        return resultArray;
    }


}
