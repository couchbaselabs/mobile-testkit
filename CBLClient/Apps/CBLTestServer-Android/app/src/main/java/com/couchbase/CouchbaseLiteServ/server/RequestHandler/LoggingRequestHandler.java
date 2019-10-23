package com.couchbase.CouchbaseLiteServ.server.RequestHandler;

import android.content.Context;
import android.util.Log;

import java.io.File;

import com.couchbase.CouchbaseLiteServ.CouchbaseLiteServ;
import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.Database;
import com.couchbase.lite.LogFileConfiguration;
import com.couchbase.lite.LogLevel;
import com.couchbase.CouchbaseLiteServ.server.RawData;
import com.couchbase.CouchbaseLiteServ.server.util.ZipUtils;


public class LoggingRequestHandler {
    private static final String TAG = "LOGREQHANDLER";
    /* ----------- */
    /* - Logging - */
    /* ----------- */

    public LogFileConfiguration configure(Args args) {
        String log_level = args.get("log_level");
        String directory = args.get("directory");
        int maxRotateCount = args.get("max_rotate_count");
        long maxSize = args.get("max_size");
        boolean plainText = args.get("plain_text");

        if (directory.isEmpty()) {
            Context context = CouchbaseLiteServ.getAppContext();
            long ts = System.currentTimeMillis() / 1000;
            directory = context.getFilesDir().getAbsolutePath() + "/logs_" + ts;

            Log.i(TAG, "File logging configured at: " + directory);
        }
        LogFileConfiguration config = new LogFileConfiguration(directory);
        if (maxRotateCount > 1) {
            config.setMaxRotateCount(maxRotateCount);
        }
        if (maxSize > 512000) {
            config.setMaxSize(maxSize);
        }
        config.setUsePlaintext(plainText);
        Database.log.getFile().setConfig(config);
        switch (log_level) {
            case "debug":
                Database.log.getFile().setLevel(LogLevel.DEBUG);
                break;
            case "verbose":
                Database.log.getFile().setLevel(LogLevel.VERBOSE);
                break;
            case "info":
                Database.log.getFile().setLevel(LogLevel.INFO);
                break;
            case "error":
                Database.log.getFile().setLevel(LogLevel.ERROR);
                break;
            case "warning":
                Database.log.getFile().setLevel(LogLevel.WARNING);
                break;
            default:
                Database.log.getFile().setLevel(LogLevel.NONE);
                break;
        }
        return config;
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

    public int getLogLevel(Args args) {
        return Database.log.getFile().getLevel().getValue();
    }

    public LogFileConfiguration getConfig(Args args) {
        return Database.log.getFile().getConfig();
    }

    public LogFileConfiguration setPlainTextStatus(Args args) {
        LogFileConfiguration config = args.get("config");
        Boolean plain_text = args.get("plain_text");
        config.setUsePlaintext(plain_text);
        return config;
    }

    public LogFileConfiguration setMaxRotateCount(Args args) {
        LogFileConfiguration config = args.get("config");
        int max_rotate_count = args.get("max_rotate_count");
        config.setMaxRotateCount(max_rotate_count);
        return config;
    }

    public LogFileConfiguration setMaxSize(Args args) {
        LogFileConfiguration config = args.get("config");
        long max_size = args.get("max_size");
        config.setMaxSize(max_size);
        return config;
    }

    public LogFileConfiguration setConfig(Args args) {
        String directory = args.get("directory");
        if (directory.isEmpty()) {
            Context context = CouchbaseLiteServ.getAppContext();
            long ts = System.currentTimeMillis() / 1000;
            directory = context.getFilesDir().getAbsolutePath() + "/logs_" + ts;

            Log.i(TAG, "File logging configured at: " + directory);
        }
        LogFileConfiguration config = new LogFileConfiguration(directory);
        Database.log.getFile().setConfig(config);
        return config;
    }

    public LogFileConfiguration setLogLevel(Args args) {
        LogFileConfiguration config = args.get("config");
        String log_level = args.get("log_level");
        switch (log_level) {
            case "debug":
                Database.log.getFile().setLevel(LogLevel.DEBUG);
                break;
            case "verbose":
                Database.log.getFile().setLevel(LogLevel.VERBOSE);
                break;
            case "info":
                Database.log.getFile().setLevel(LogLevel.INFO);
                break;
            case "error":
                Database.log.getFile().setLevel(LogLevel.ERROR);
                break;
            case "warning":
                Database.log.getFile().setLevel(LogLevel.WARNING);
                break;
            default:
                Database.log.getFile().setLevel(LogLevel.NONE);
                break;
        }
        return config;
    }

    public RawData getLogsInZip(Args args) {
        LogFileConfiguration fileLoggerConfig = Database.log.getFile().getConfig();
        if (fileLoggerConfig == null) { return null; }

        ZipUtils zipper = new ZipUtils();

        File zipDir = CouchbaseLiteServ.getAppContext().getExternalFilesDir("zip");
        try {
            File zipFile = new File(zipDir, "archive.zip");
            if (zipFile.exists()) { zipper.deleteRecursive(zipFile); }

            zipper.zipDirectory(fileLoggerConfig.getDirectory(), zipFile);

            return new RawData("application/zip", zipper.readFile(zipFile));
        }
        finally {
            zipper.deleteRecursive(zipDir);
        }
    }

}
