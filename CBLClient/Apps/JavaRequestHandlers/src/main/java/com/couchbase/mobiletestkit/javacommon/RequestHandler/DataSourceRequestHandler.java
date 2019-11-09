package com.couchbase.mobiletestkit.javacommon.RequestHandler;


import com.couchbase.mobiletestkit.javacommon.Args;
import com.couchbase.lite.DataSource;
import com.couchbase.lite.Database;


public class DataSourceRequestHandler {

    public DataSource database(Args args) {
        Database database = args.get("database");
        return DataSource.database(database);
    }
}
