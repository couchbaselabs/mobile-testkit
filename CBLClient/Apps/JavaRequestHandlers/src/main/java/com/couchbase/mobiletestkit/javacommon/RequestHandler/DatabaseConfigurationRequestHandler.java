package com.couchbase.mobiletestkit.javacommon.RequestHandler;


import com.couchbase.mobiletestkit.javacommon.Args;
import com.couchbase.mobiletestkit.javacommon.RequestHandlerDispatcher;
import com.couchbase.mobiletestkit.javacommon.util.Log;
import com.couchbase.lite.DatabaseConfiguration;
import com.couchbase.lite.EncryptionKey;

public class DatabaseConfigurationRequestHandler {
    private static final String TAG = "DATABASE_CONFIG";
    public DatabaseConfiguration configure(Args args) {
        String directory = args.get("directory");
        Log.i(TAG, "DatabaseConfiguration_configure directory=" + directory);
        EncryptionKey encryptionKey;
        //ConflictResolver conflictResolver = args.get("conflictResolver");
        String password = args.get("password");
        DatabaseConfiguration config = new DatabaseConfiguration();
        if (directory != null) {
            config.setDirectory(directory);
        }
        else{
            directory = RequestHandlerDispatcher.context.getFilesDir().getAbsolutePath();
            Log.i(TAG, "No directory is set, now point to " + directory);
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
