package com.couchbase.mobiletestkit.javacommon.RequestHandler;

import com.couchbase.mobiletestkit.javacommon.Args;
import com.couchbase.lite.Result;


public class ResultRequestHandler {

    public String getString(Args args) {
        Result query_result = args.get("query_result");
        String key = args.get("key");
        return query_result.getString(key);
    }
}
