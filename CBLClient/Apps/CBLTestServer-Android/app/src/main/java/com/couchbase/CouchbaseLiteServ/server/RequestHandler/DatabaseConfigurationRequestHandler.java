package com.couchbase.CouchbaseLiteServ.server.RequestHandler;


import android.content.Context;

import com.couchbase.CouchbaseLiteServ.MainActivity;
import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.DatabaseConfiguration;
import com.couchbase.lite.DatabaseConfiguration.Builder;
import com.couchbase.lite.ConflictResolver;
import com.couchbase.lite.EncryptionKey;

public class DatabaseConfigurationRequestHandler {

    public Builder builderCreate(Args args){
        DatabaseConfiguration config = args.get("config");
        if (config != null) {
            return new Builder(config);
        } else {
            Context context = MainActivity.getAppContext();
            return new Builder(context);
        }
    }

    public DatabaseConfiguration create(Args args) {
        Builder builder = args.get("databaseBuilder");
        return builder.build();
    }

    public ConflictResolver getConflictResolver(Args args){
        DatabaseConfiguration config = args.get("config");
        return config.getConflictResolver();
    }

    public String getDirectory(Args args){
        DatabaseConfiguration config = args.get("config");
        return config.getDirectory();
    }

    public EncryptionKey getEncryptionKey(Args args){
        DatabaseConfiguration config = args.get("config");
        return config.getEncryptionKey();
    }

    public Builder setConflictResolver(Args args){
        Builder builder = args.get("builder");
        ConflictResolver conflictResolver = args.get("conflictResolver");
        return builder.setConflictResolver(conflictResolver);
    }

    public Builder setDirectory(Args args){
        Builder builder = args.get("builder");
        String directory = args.get("directory");
        return builder.setDirectory(directory);
    }

    public Builder setEncryptionKey(Args args){
        Builder builder = args.get("builder");
        EncryptionKey key = args.get("key");
        return builder.setEncryptionKey(key);
    }
}
