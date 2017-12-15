package com.couchbase.CouchbaseLiteServ.server.RequestHandler;


import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.BaseDatabaseConfiguration;
import com.couchbase.lite.ConflictResolver;
import com.couchbase.lite.EncryptionKey;

import java.io.File;

public class BaseDatabaseConfigurationRequestHandler {

    public BaseDatabaseConfiguration create(Args args){
        return new BaseDatabaseConfiguration();
    }

    public ConflictResolver getConflictResolver(Args args){
        BaseDatabaseConfiguration config = args.get("config");
        return config.getConflictResolver();
    }

    public File getDirectory(Args args){
        BaseDatabaseConfiguration config = args.get("config");
        return config.getDirectory();
    }

    public EncryptionKey getEncryptionKey(Args args){
        BaseDatabaseConfiguration config = args.get("config");
        return config.getEncryptionKey();
    }

    public BaseDatabaseConfiguration setConflictResolver(Args args){
        BaseDatabaseConfiguration config = args.get("config");
        ConflictResolver conflictResolver = args.get("conflictResolver");
        return config.setConflictResolver(conflictResolver);
    }

    public BaseDatabaseConfiguration setDirectory(Args args){
        BaseDatabaseConfiguration config = args.get("config");
        File directory = args.get("directory");
        return config.setDirectory(directory);
    }

    public BaseDatabaseConfiguration setEncryptionKey(Args args){
        BaseDatabaseConfiguration config = args.get("config");
        EncryptionKey key = args.get("key");
        return config.setEncryptionKey(key);
    }
}
