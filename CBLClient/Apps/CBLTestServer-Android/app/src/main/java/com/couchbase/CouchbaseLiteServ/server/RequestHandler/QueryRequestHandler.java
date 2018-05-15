package com.couchbase.CouchbaseLiteServ.server.RequestHandler;


import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.Collation;
import com.couchbase.lite.CouchbaseLiteException;
import com.couchbase.lite.DataSource;
import com.couchbase.lite.Database;
import com.couchbase.lite.Expression;
import com.couchbase.lite.FullTextExpression;
import com.couchbase.lite.FullTextFunction;
import com.couchbase.lite.FullTextIndex;
import com.couchbase.lite.FullTextIndexItem;
import com.couchbase.lite.Function;
import com.couchbase.lite.IndexBuilder;
import com.couchbase.lite.Join;
import com.couchbase.lite.Meta;
import com.couchbase.lite.Ordering;
import com.couchbase.lite.Query;
import com.couchbase.lite.QueryBuilder;
import com.couchbase.lite.Result;
import com.couchbase.lite.ResultSet;
import com.couchbase.lite.SelectResult;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class QueryRequestHandler {

   public Query select(Args args){
       SelectResult select_result = args.get("select_result");
       return QueryBuilder.select(select_result);
   }

    public Query distinct(Args args){
        SelectResult select_result = args.get("select_prop");
        DataSource from_prop = args.get("from_prop");
        Expression whr_key_prop = Expression.value(args.get("whr_key_prop"));
        return QueryBuilder.select(select_result).from(from_prop).where(whr_key_prop);
    }

    public Query create(Args args){
        SelectResult select_result = args.get("select_result");
        return QueryBuilder.select(select_result);
    }

    public ResultSet run(Args args) throws CouchbaseLiteException {
        Query query = args.get("query");
        return query.execute();
    }

    public Result nextResult(Args args){
        ResultSet query_result_set = args.get("query_result_set");
        return query_result_set.next();
    }

    public List<Object> getDoc(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        long out = database.getCount();
        Expression doc_id = Expression.value(args.get("doc_id"));
        Query query = QueryBuilder
                .select(SelectResult.all())
                .from(DataSource.database(database))
                .where((Meta.id).equalTo(doc_id));
        List<Object> resultArray = new ArrayList<Object>();
        for (Result row : query.execute()){
            resultArray.add(row.toMap());
        }
        return resultArray;
    }

    public List<Object> docsLimitOffset(Args args) throws CouchbaseLiteException {
        Database database = args.get("database");
        Expression limit = Expression.value(args.get("limit"));
        Expression offset = Expression.value(args.get("offset"));
        Query search_query = QueryBuilder
                .select(SelectResult.all())
                .from(DataSource.database(database))
                .limit(limit, offset);
        List<Object> resultArray = new ArrayList<>();
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

        Query search_query = QueryBuilder
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(select_property1)),
                        SelectResult.expression(Expression.property(select_property2)))
                .from(DataSource.database(database))
                .where(Expression.property(whr_key).equalTo(whr_val));
        List<Object> resultArray = new ArrayList<>();
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
        List<Object> resultArray = new ArrayList<>();
        Query query = QueryBuilder
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
        long out = database.getCount();
        String whr_key = args.get("whr_key");
        String select_property1 = args.get("select_property1");
        String select_property2 = args.get("select_property2");
        String like_key = args.get("like_key");
        Expression whr_val = Expression.value(args.get("whr_val"));
        Expression like_val = Expression.value(args.get("like_val"));
        List<Object> resultArray = new ArrayList<>();
        Query query = QueryBuilder
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
        List<Object> resultArray = new ArrayList<>();
        Query query = QueryBuilder
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
        List<Object> resultArray = new ArrayList<>();
        Query query = QueryBuilder
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
        List<Object> resultArray = new ArrayList<>();
        Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(select_property1)),
                        SelectResult.expression(Function.upper(Expression.property(select_property2))))
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
        List<Object> resultArray = new ArrayList<>();
        Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(select_property1)))
                .from(DataSource.database(database))
                .where(Expression.property(select_property1).isNullOrMissing())
                .orderBy(Ordering.expression(Meta.id).ascending())
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
        List<Object> resultArray = new ArrayList<>();

        Collation collation = Collation.unicode()
                .ignoreAccents(true)
                .ignoreCase(true);
        Query query = QueryBuilder
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

    public List<Object> join(Args args) throws CouchbaseLiteException {
        Database db = args.get("database");
        String prop1 = args.get("select_property1");
        String prop2 = args.get("select_property2");
        String prop3 = args.get("select_property3");
        String prop4 = args.get("select_property4");
        String prop5 = args.get("select_property5");
        String joinKey = args.get("join_key");
        String whrKey1 = args.get("whr_key1");
        String whrKey2 = args.get("whr_key2");
        String whrKey3 = args.get("whr_key3");
        Expression limit = Expression.value(args.get("limit"));
        Expression whrVal1 = Expression.value(args.get("whr_val1"));
        Expression whrVal2 = Expression.value(args.get("whr_val2"));
        Expression whrVal3 = Expression.value(args.get("whr_val3"));
        String main = "route";
        String secondary = "airline";

        List<Object> resultArray = new ArrayList<>();

        Query query = QueryBuilder
                .selectDistinct(
                        SelectResult.expression(Expression.property(prop1).from(secondary)),
                        SelectResult.expression(Expression.property(prop2).from(secondary)),
                        SelectResult.expression(Expression.property(prop3).from(main)),
                        SelectResult.expression(Expression.property(prop4).from(main)),
                        SelectResult.expression(Expression.property(prop5).from(main)))
                .from(DataSource.database(db).as(main))
                .join(Join.join(DataSource.database(db).as(secondary))
                    .on(Meta.id.from(secondary).equalTo(Expression.property(joinKey).from(main))))
                .where(Expression.property(whrKey1).from(main).equalTo(whrVal1)
                    .and(Expression.property(whrKey2).from(secondary).equalTo(whrVal2))
                    .and(Expression.property(whrKey3).from(main).equalTo(whrVal3)));
        for (Result row : query.execute()){
            resultArray.add(row.toMap());
        }
        return resultArray;
    }

    public List<Object> leftJoin(Args args) throws CouchbaseLiteException {
        Database db = args.get("database");
        String prop = args.get("select_property");
        int limit = args.get("limit");
        String main = "airline";
        String secondary = "route";

        List<Object> resultArray = new ArrayList<>();


        Query query = QueryBuilder
                .select(SelectResult.all().from(main),
                        SelectResult.all().from((secondary)))
                .from(DataSource.database(db).as(main))
                .join(Join.leftJoin(DataSource.database(db).as(secondary))
                        .on(Meta.id.from(main).equalTo(Expression.property(prop).from(secondary))))
                //.orderBy(Ordering.expression(Expression.property(prop).from(secondary)).ascending())
                .limit(Expression.intValue(limit));
        for (Result row : query.execute()) {
            resultArray.add(row.toMap());
        }
        return resultArray;
    }

    public List<Object> leftOuterJoin(Args args) throws CouchbaseLiteException {
        Database db = args.get("database");
        String prop = args.get("select_property");
        int limit = args.get("limit");
        String main = "airline";
        String secondary = "route";

        List<Object> resultArray = new ArrayList<>();


        Query query = QueryBuilder
                .select(SelectResult.all().from(main),
                        SelectResult.all().from((secondary)))
                .from(DataSource.database(db).as(main))
                .join(Join.leftOuterJoin(DataSource.database(db).as(secondary))
                        .on(Meta.id.from(main).equalTo(Expression.property(prop).from(secondary))))
                //.orderBy(Ordering.expression(Expression.property(prop).from(secondary)).ascending())
                .limit(Expression.intValue(limit));
        for (Result row : query.execute()) {
            resultArray.add(row.toMap());
        }
        return resultArray;
    }

    public List<Object> innerJoin(Args args) throws CouchbaseLiteException {
        /*
        SELECT
          employeeDS.firstname,
          employeeDS.lastname,
          departmentDS.name
        FROM
          `travel-sample` employeeDS
          INNER JOIN `travel-sample` departmentDS ON employeeDS.department = departmentDS.code
        WHERE
          employeeDS.type = "employee"
          AND departmentDS.type = "department"
         */
        Database db = args.get("database");
        String prop1 = args.get("select_property1");
        String prop2 = args.get("select_property2");
        String prop3 = args.get("select_property3");
        String joinKey1 = args.get("join_key1");
        String joinKey2 = args.get("join_key2");
        String whrKey1 = args.get("whr_key1");
        String whrKey2 = args.get("whr_key2");
        String whrVal1 = args.get("whr_val1");
        int whrVal2 = args.get("whr_val2");
        int limit = args.get("limit");
        String main = "route";
        String secondary = "airline";

        List<Object> resultArray = new ArrayList<>();


        Query query = QueryBuilder
                .select(SelectResult.expression(Expression.property(prop1).from(main)),
                        SelectResult.expression(Expression.property(prop2).from(main)),
                        SelectResult.expression(Expression.property(prop3).from(secondary)))
                .from(DataSource.database(db).as(main))
                .join(Join.innerJoin(DataSource.database(db).as(secondary))
                        .on(Expression.property(joinKey1).from(secondary).equalTo(Expression.property(joinKey2).from(main))
                                .and(Expression.property(whrKey1).from(secondary).equalTo(Expression.string(whrVal1)))
                                .and(Expression.property(whrKey2).from(main).equalTo(Expression.intValue(whrVal2)))))
                //.orderBy(Ordering.expression(Expression.property(prop1).from(main)).ascending())
                .limit(Expression.intValue(limit));
        ResultSet queryResults = query.execute();
        for (Result row : queryResults) {
            resultArray.add(row.toMap());
        }
        return resultArray;
    }


    public List<Object> crossJoin(Args args) throws CouchbaseLiteException {
        /*
        SELECT
          departmentDS.name AS DeptName,
          locationDS.name AS LocationName,
          locationDS.address
        FROM
          `travel-sample` departmentDS
          CROSS JOIN `travel-sample` locationDS
        WHERE
          departmentDS.type = "department"
         */
        Database db = args.get("database");
        String prop1 = args.get("select_property1");
        String prop2 = args.get("select_property2");
        String whrKey1 = args.get("whr_key1");
        String whrKey2 = args.get("whr_key2");
        String whrVal1 = args.get("whr_val1");
        String whrVal2 = args.get("whr_val2");
        int limit = args.get("limit");
        String main = "airport";
        String secondary = "airline";
        String firstName = "firstName";
        String secondName = "secondName";
        List<Object> resultArray = new ArrayList<>();


        Query query = QueryBuilder
                .select(SelectResult.expression(Expression.property(prop1).from(main)).as(firstName),
                        SelectResult.expression(Expression.property(prop1).from(secondary)).as(secondName),
                        SelectResult.expression(Expression.property(prop2).from(secondary)))
                .from(DataSource.database(db).as(main))
                .join(Join.crossJoin(DataSource.database(db).as(secondary)))
                .where(Expression.property(whrKey1).from(main).equalTo(Expression.string(whrVal1))
                        .and(Expression.property(whrKey2).from(secondary).equalTo(Expression.string(whrVal2))))
                //.orderBy(Ordering.expression(Expression.property(prop1).from(main)).ascending())
                .limit(Expression.intValue(limit));
        for (Result row : query.execute()) {
            resultArray.add(row.toMap());
        }
        return resultArray;
    }

    public List<Object> equalTo(Args args) throws CouchbaseLiteException {
        //SELECT * FROM `travel-sample` where id = 24
        Database db = args.get("database");
        String prop = args.get("prop");
        Expression val = Expression.value(args.get("val"));
        List<Object> resultArray = new ArrayList<>();

        Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(db))
                .where(Expression.property(prop).equalTo(val))
                .orderBy(Ordering.expression(Meta.id).ascending());
        for (Result row : query.execute()) {
            resultArray.add(row.toMap());
        }
        return resultArray;
    }

    public List<Object> notEqualTo(Args args) throws CouchbaseLiteException {
        //SELECT * FROM `travel-sample` where id != 24
        Database db = args.get("database");
        String prop = args.get("prop");
        Expression val = Expression.value(args.get("val"));
        List<Object> resultArray = new ArrayList<>();

        Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(db))
                .where(Expression.property(prop).notEqualTo(val))
                .orderBy(Ordering.expression(Meta.id).ascending());
        for (Result row : query.execute()) {
            resultArray.add(row.toMap());
        }
        return resultArray;
    }

    public List<Object> greaterThan(Args args) throws CouchbaseLiteException {
        //SELECT * FROM `travel-sample` where id > 1000
        Database db = args.get("database");
        String prop = args.get("prop");
        Expression val = Expression.value(args.get("val"));
        List<Object> resultArray = new ArrayList<>();

        Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(db))
                .where(Expression.property(prop).greaterThan(val))
                .orderBy(Ordering.expression(Meta.id).ascending());
        for (Result row : query.execute()) {
            resultArray.add(row.toMap());
        }
        return resultArray;
    }

    public List<Object> greaterThanOrEqualTo(Args args) throws CouchbaseLiteException {
        //SELECT * FROM `travel-sample` where id >= 31000 limit 5
        Database db = args.get("database");
        String prop = args.get("prop");
        Expression val = Expression.value(args.get("val"));
        List<Object> resultArray = new ArrayList<>();

        Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(db))
                .where(Expression.property(prop).greaterThanOrEqualTo(val))
                .orderBy(Ordering.expression(Meta.id).ascending());
        for (Result row : query.execute()) {
            resultArray.add(row.toMap());
        }
        return resultArray;
    }

    public List<Object> lessThan(Args args) throws CouchbaseLiteException {
        //SELECT * FROM `travel-sample` where id < 100 limit 5
        Database db = args.get("database");
        String prop = args.get("prop");
        Expression val = Expression.value(args.get("val"));
        List<Object> resultArray = new ArrayList<>();

        Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(db))
                .where(Expression.property(prop).lessThan(val))
                .orderBy(Ordering.expression(Meta.id).ascending());
        for (Result row : query.execute()) {
            resultArray.add(row.toMap());
        }
        return resultArray;
    }

    public List<Object> lessThanOrEqualTo(Args args) throws CouchbaseLiteException {
        //SELECT * FROM `travel-sample` where id <= 100 limit 5
        Database db = args.get("database");
        String prop = args.get("prop");
        Expression val = Expression.value(args.get("val"));
        List<Object> resultArray = new ArrayList<>();

        Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(db))
                .where(Expression.property(prop).lessThanOrEqualTo(val))
                .orderBy(Ordering.expression(Meta.id).ascending());
        for (Result row : query.execute()) {
            resultArray.add(row.toMap());
        }
        return resultArray;
    }

    public List<Object> between(Args args) throws CouchbaseLiteException {
        //SELECT * FROM `travel-sample` where id between 100 and 200
        Database db = args.get("database");
        String prop = args.get("prop");
        Expression val1 = Expression.value(args.get("val1"));
        Expression val2 = Expression.value(args.get("val2"));
        List<Object> resultArray = new ArrayList<>();

        Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(db))
                .where(Expression.property(prop).between(val1, val2))
                .orderBy(Ordering.expression(Meta.id).ascending());
        for (Result row : query.execute()) {
            resultArray.add(row.toMap());
        }
        return resultArray;
    }

    public List<Object> in(Args args) throws CouchbaseLiteException {
        //SELECT * FROM `travel-sample` where country in ["france", "United States"]
        Database db = args.get("database");
        String prop = args.get("prop");
        String val1 =  args.get("val1");
        String val2 =  args.get("val2");
        List<Object> resultArray = new ArrayList<>();

        Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(db))
                .where(Expression.property(prop).in(Expression.value(val1), Expression.value(val2)))
                .orderBy(Ordering.expression(Meta.id).ascending());
        for (Result row : query.execute()) {
            resultArray.add(row.toMap());
        }
        return resultArray;
    }

    public List<Object> is(Args args) throws CouchbaseLiteException {
        //SELECT * FROM `travel-sample` where callsign is null
        Database db = args.get("database");
        String prop = args.get("prop");
        List<Object> resultArray = new ArrayList<>();

        Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(db))
                .where(Expression.property(prop).is(Expression.value(null)))
                .orderBy(Ordering.expression(Meta.id).ascending());
        for (Result row : query.execute()) {
            resultArray.add(row.toMap());
        }
        return resultArray;
    }

    public List<Object> not(Args args) throws CouchbaseLiteException {
        //SELECT * FROM `travel-sample` where id not  between 100 and 200 limit 5
        Database db = args.get("database");
        String prop = args.get("prop");
        Expression val1 = Expression.value(args.get("val1"));
        Expression val2 = Expression.value(args.get("val2"));
        List<Object> resultArray = new ArrayList<>();

        Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id))
                .from(DataSource.database(db))
                .where(Expression.not(Expression.property(prop).between(val1, val2)))
                .orderBy(Ordering.expression(Expression.property(prop)).ascending());
        for (Result row : query.execute()) {
            resultArray.add(row.toMap());
        }
        return resultArray;
    }

    public List<Object> isNot(Args args) throws CouchbaseLiteException {
        //SELECT * FROM `travel-sample` where callsign is not null limit 5
        Database db = args.get("database");
        String prop = args.get("prop");

        List<Object> resultArray = new ArrayList<>();

        Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(prop)))
                .from(DataSource.database(db))
                .where(Expression.property(prop).isNot(Expression.value(null)))
                .orderBy(Ordering.expression(Meta.id).ascending());
        for (Result row : query.execute()) {
            resultArray.add(row.toMap());
        }
        return resultArray;
    }

    public List<Object> singlePropertyFTS(Args args) throws CouchbaseLiteException {
        Database db = args.get("database");
        String prop = args.get("prop");
        String val = args.get("val");
        Boolean stemming = args.get("stemming");
        Expression docType = Expression.value(args.get("doc_type"));
        Expression limit = Expression.value(args.get("limit"));
        String index = "singlePropertyIndex";
        FullTextIndex ftsIndex;

        if (stemming) {
            ftsIndex = IndexBuilder.fullTextIndex(FullTextIndexItem.property(prop));
        } else {
            ftsIndex = IndexBuilder.fullTextIndex(FullTextIndexItem.property(prop)).setLanguage(null);
        }
        db.createIndex(index,ftsIndex);
        FullTextExpression ftsExpression = FullTextExpression.index(index);
        List<Object> resultArray = new ArrayList<>();

        Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(prop)))
                .from(DataSource.database(db))
                .where(Expression.property("type").equalTo(docType).and(ftsExpression.match(val)))
                .limit(limit);
        for (Result row : query.execute()) {
            resultArray.add(row.toMap());
        }
        return resultArray;
    }

    public List<Object> multiplePropertyFTS(Args args) throws CouchbaseLiteException {
        Database db = args.get("database");
        String prop1 = args.get("prop1");
        String prop2 = args.get("prop2");
        String val = args.get("val");
        Boolean stemming = args.get("stemming");
        Expression docType = Expression.value(args.get("doc_type"));
        Expression limit = Expression.value(args.get("limit"));
        String index = "multiplePropertyIndex";
        FullTextIndex ftsIndex;

        if (stemming) {
            ftsIndex = IndexBuilder.fullTextIndex(FullTextIndexItem.property(prop1), FullTextIndexItem.property(prop2));
        } else {
            ftsIndex = IndexBuilder.fullTextIndex(FullTextIndexItem.property(prop1), FullTextIndexItem.property(prop2)).setLanguage(null);
        }
        db.createIndex(index,ftsIndex);
        FullTextExpression ftsExpression = FullTextExpression.index(index);
        List<Object> resultArray = new ArrayList<>();

        Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(prop1)),
                        SelectResult.expression(Expression.property(prop2)))
                .from(DataSource.database(db))
                .where(Expression.property("type").equalTo(docType).and(ftsExpression.match(val)))
                .limit(limit);
        for (Result row : query.execute()) {
            resultArray.add(row.toMap());
        }
        return resultArray;
    }

    public List<Object> ftsWithRanking(Args args) throws CouchbaseLiteException {
        Database db = args.get("database");
        String prop = args.get("prop");
        String val = args.get("val");
        Expression docType = Expression.value(args.get("doc_type"));
        Expression limit = Expression.value(args.get("limit"));
        String index = "singlePropertyIndex";

        FullTextIndex ftsIndex = IndexBuilder.fullTextIndex(FullTextIndexItem.property(prop));
        db.createIndex(index,ftsIndex);
        FullTextExpression ftsExpression = FullTextExpression.index(index);
        List<Object> resultArray = new ArrayList<>();

        Query query = QueryBuilder
                .select(SelectResult.expression(Meta.id),
                        SelectResult.expression(Expression.property(prop)))
                .from(DataSource.database(db))
                .where(Expression.property("type").equalTo(docType).and(ftsExpression.match(val)))
                .orderBy(Ordering.expression(FullTextFunction.rank(index)).descending())
                .limit(limit);
        for (Result row : query.execute()) {
            resultArray.add(row.toMap());
        }
        return resultArray;
    }
}
