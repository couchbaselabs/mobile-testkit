package com.couchbase.CouchbaseLiteServ.server.RequestHandler;

import android.content.Context;

import com.couchbase.CouchbaseLiteServ.MainActivity;
import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.Database;
import com.couchbase.lite.LogFileConfiguration;
import com.couchbase.lite.LogLevel;

public class LoggingRequestHandler {
    /* ----------- */
    /* - Logging - */
    /* ----------- */

    public void configure(Args args){
        LogLevel level = args.get("log_level");
        String directory = args.get("directory");
        int maxRotateCount = args.get("max_rotate_count");
        long maxSize = args.get("max_size");
        boolean plainText = args.get("plain_text");


        if (level.equals("debug")) {
            Database.log.getFile().setLevel(LogLevel.DEBUG);
        } else if (level.equals("verbose")) {
            Database.log.getFile().setLevel(LogLevel.VERBOSE);
        } else if (level.equals("error")) {
            Database.log.getFile().setLevel(LogLevel.ERROR);
        } else if (level.equals("info")) {
            Database.log.getFile().setLevel(LogLevel.INFO);
        } else if (level.equals("warning")) {
            Database.log.getFile().setLevel(LogLevel.WARNING);
        } else {
            Database.log.getFile().setLevel(LogLevel.NONE);
        }

        if (directory.equals("")) {
            Context context = MainActivity.getAppContext();
            directory = context.getFilesDir().getAbsolutePath();
        }
        LogFileConfiguration config = new LogFileConfiguration(directory);
        if (maxRotateCount > 0) {
            config.setMaxRotateCount(maxRotateCount);
        }
        if (maxSize > 0) {
            config.setMaxSize(maxSize);
        }
        config.setUsePlaintext(plainText);
        Database.log.getFile().setConfig(config);
    }

    public boolean getPlainTextStatus(Args args) {
        return Database.log.getFile().getConfig().usesPlaintext();
    }

    public int getMaxRotateCount(Args args) {
        return Database.log.getFile().getConfig().getMaxRotateCount();
    }

    public long getMaxSize(Args args) {
        return Database.log.getFile().getConfig().getMaxSize();
    }

    public String getDirectory(Args args) {
        return Database.log.getFile().getConfig().getDirectory();
    }

    public int getLevel(Args args) {
        return Database.log.getFile().getLevel().getValue();
    }

    public LogFileConfiguration getConfig(Args args) {
        return Database.log.getFile().getConfig();
    }
}
