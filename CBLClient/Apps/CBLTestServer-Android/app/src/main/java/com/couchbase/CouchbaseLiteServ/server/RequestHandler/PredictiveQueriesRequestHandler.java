package com.couchbase.CouchbaseLiteServ.server.RequestHandler;

/**
 * Created by sridevi.saragadam on 2/26/19.
 */

import android.content.Context;

import com.couchbase.CouchbaseLiteServ.MainActivity;
import com.couchbase.CouchbaseLiteServ.server.Args;
/*
import com.couchbase.lite.CouchbaseLiteException;
import com.couchbase.lite.DataSource;
import com.couchbase.lite.Expression;
import com.couchbase.lite.Meta;
import com.couchbase.lite.PredictiveModel;
import com.couchbase.lite.Dictionary;
import com.couchbase.lite.Database;
import com.couchbase.lite.Query;
import com.couchbase.lite.QueryBuilder;
import com.couchbase.lite.Result;
import com.couchbase.lite.ResultSet;
import com.couchbase.lite.SelectResult;
import com.couchbase.lite.PredictionFunction;*/
import com.couchbase.lite.*;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;


public class PredictiveQueriesRequestHandler {


  public EchoModel registerModel(Args args){
    String modelName = args.get("model_name");
    EchoModel echoModel = new EchoModel(modelName);
    Database.prediction.registerModel(modelName, echoModel);
    return echoModel;
  }

  public void unRegisterModel(Args args){
    String modelName = args.get("model_name");
    Database.prediction.unregisterModel(modelName);
  }

  public List<Object> getPredictionQueryResult(Args args) throws CouchbaseLiteException {
    EchoModel echoModel = args.get("model");
    Database database = args.get("database");
    Map<String, Object> dict = args.get("dictionary");
    Expression input = Expression.value(dict);
    PredictionFunction prediction = Function.prediction(echoModel.getName(), input);
    //String select_property1 = args.get("select_property1");
    //String select_property2 = args.get("select_property2");

    Query query = QueryBuilder
        .select(SelectResult.expression(prediction))
        .from(DataSource.database(database));

    List<Object> resultArray = new ArrayList<>();
    ResultSet rows = query.execute();
    for (Result row : rows){
      resultArray.add(row.toMap());
    }
    return resultArray;
  }

  public String nonDictionary(Args args) throws CouchbaseLiteException {
    EchoModel echoModel = args.get("model");
    Database database = args.get("database");
    String dict = args.get("dictionary");
    Expression input = Expression.value(dict);
    PredictionFunction prediction = Function.prediction(echoModel.getName(), input);

    Query query = QueryBuilder
        .select(SelectResult.expression(prediction))
        .from(DataSource.database(database));

    List<Object> resultArray = new ArrayList<>();
    try {
      query.execute();
    }
    catch(Exception e){
      return e.getLocalizedMessage();
    }
    return "success";
  }

  public List<Object> euclideanDistance(Args args) throws CouchbaseLiteException {
    Database database = args.get("database");

    String key1 = args.get("key1");
    String key2 = args.get("key2");
    Expression distance = Function.euclideanDistance(Expression.property(key1), Expression.property(key2));

    Query query = QueryBuilder
        .select(SelectResult.expression(distance))
        .from(DataSource.database(database));

    List<Object> resultArray = new ArrayList<>();
    ResultSet rows = query.execute();
    for (Result row : rows){
      resultArray.add(row.toMap());
    }
    return resultArray;
  }

  public int getNumberOfCalls(Args args) {
    EchoModel echoModel = args.get("model");
    return echoModel.numberOfCalls;
  }

  public List<Object> squaredEuclideanDistance(Args args) throws CouchbaseLiteException {
    Database database = args.get("database");

    String key1 = args.get("key1");
    String key2 = args.get("key2");
    Expression distance = Function.squaredEuclideanDistance(Expression.property(key1), Expression.property(key2));

    Query query = QueryBuilder
        .select(SelectResult.expression(distance))
        .from(DataSource.database(database));

    List<Object> resultArray = new ArrayList<>();
    ResultSet rows = query.execute();
    for (Result row : rows){
      resultArray.add(row.toMap());
    }
    return resultArray;
  }

  public List<Object> cosineDistance(Args args) throws CouchbaseLiteException {
    Database database = args.get("database");

    String key1 = args.get("key1");
    String key2 = args.get("key2");
    Expression distance = Function.cosineDistance(Expression.property(key1), Expression.property(key2));

    Query query = QueryBuilder
        .select(SelectResult.expression(distance))
        .from(DataSource.database(database));

    List<Object> resultArray = new ArrayList<>();
    ResultSet rows = query.execute();
    for (Result row : rows){
      resultArray.add(row.toMap());
    }
    return resultArray;
  }

  private static final class EchoModel implements PredictiveModel {
    public String name;
    private int numberOfCalls = 0;

    EchoModel(String name){
      System.out.println("Entered into echo model");
      this.name = name;
    }

    public String getName() {
      return name;
    }

    @Override
    public Dictionary predict(Dictionary input) {
      numberOfCalls++;
      return input;
    }
  }
}