package com.couchbase.CouchbaseLiteServ.server.RequestHandler;

import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.Result;


public class ResultRequestHandler {

    public String getString(Args args) {
        Result query_result = args.get("query_result");
        String key = args.get("key");
        return query_result.getString(key);
    }
}
