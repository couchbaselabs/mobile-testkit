package com.couchbase.CouchbaseLiteServ.server.RequestHandler;


import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.DatabaseConfiguration;
import com.couchbase.lite.EncryptionKey;


public class DatabaseConfigurationRequestHandler {

    public DatabaseConfiguration configure(Args args) {
        String directory = args.get("directory");
        EncryptionKey encryptionKey;
        //ConflictResolver conflictResolver = args.get("conflictResolver");
        String password = args.get("password");
        DatabaseConfiguration config = new DatabaseConfiguration();
        if (directory != null) {
            config.setDirectory(directory);
        }
        /*if (conflictResolver != null) {
            config.setConflictResolver(conflictResolver);
        }*/
        if (password != null) {
            encryptionKey = new EncryptionKey(password);
            config.setEncryptionKey(encryptionKey);
        }
        return config;
    }

    /*public ConflictResolver getConflictResolver(Args args){
        DatabaseConfiguration config = args.get("config");
        return config.getConflictResolver();
    }*/

    public String getDirectory(Args args) {
        DatabaseConfiguration config = args.get("config");
        return config.getDirectory();
    }

    public EncryptionKey getEncryptionKey(Args args) {
        DatabaseConfiguration config = args.get("config");
        return config.getEncryptionKey();
    }

    /*public DatabaseConfiguration setConflictResolver(Args args){
        DatabaseConfiguration config = args.get("config");
        ConflictResolver conflictResolver = args.get("conflictResolver");
        return config.setConflictResolver(conflictResolver);
    }*/

    public DatabaseConfiguration setDirectory(Args args) {
        DatabaseConfiguration config = args.get("config");
        String directory = args.get("directory");
        return config.setDirectory(directory);
    }

    public DatabaseConfiguration setEncryptionKey(Args args) {
        DatabaseConfiguration config = args.get("config");
        String password = args.get("password");
        EncryptionKey encryptionKey = new EncryptionKey(password);
        return config.setEncryptionKey(encryptionKey);
    }
}
