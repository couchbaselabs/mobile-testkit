package com.couchbase.CouchbaseLiteServ.server.RequestHandler;


import android.content.Context;

import com.couchbase.CouchbaseLiteServ.MainActivity;
import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.DatabaseConfiguration;
import com.couchbase.lite.ConflictResolver;
import com.couchbase.lite.EncryptionKey;

public class DatabaseConfigurationRequestHandler {

    /* Not required as builder is removed
    public DatabaseConfiguration builderCreate(Args args){
        return new DatabaseConfiguration();
    }*/

    public DatabaseConfiguration configure(Args args) {
        String directory = args.get("directory");
        ConflictResolver conflictResolver = args.get("conflictResolver");
        // EncryptionKey encryptionKey = args.get("encryptionKey");
        String password = args.get("password");
        Context context = MainActivity.getAppContext();
        DatabaseConfiguration config = new DatabaseConfiguration(context);
        if (directory != null) {
            config.setDirectory(directory);
        }
        if (conflictResolver != null) {
            config.setConflictResolver(conflictResolver);
        }
        if (password != null) {
          EncryptionKey encryptionKey = new EncryptionKey(password);
          config.setEncryptionKey(encryptionKey);
        }
        return config;
    }

    // TODO : This is may not require. Remove it if it is not used
    public DatabaseConfiguration create(Args args) {
        DatabaseConfiguration config = args.get("config");
        return config;
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

    public DatabaseConfiguration setConflictResolver(Args args){
        DatabaseConfiguration config = args.get("config");
        ConflictResolver conflictResolver = args.get("conflictResolver");
        return config.setConflictResolver(conflictResolver);
    }

    public DatabaseConfiguration setDirectory(Args args){
        DatabaseConfiguration config = args.get("config");
        String directory = args.get("directory");
        return config.setDirectory(directory);
    }

    public DatabaseConfiguration setEncryptionKey(Args args){
        DatabaseConfiguration config = args.get("config");
        String password = args.get("password");
        EncryptionKey encryptionKey = new EncryptionKey(password);
        return config.setEncryptionKey(encryptionKey);
    }
}
