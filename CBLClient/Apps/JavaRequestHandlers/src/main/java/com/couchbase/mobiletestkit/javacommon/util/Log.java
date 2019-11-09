package com.couchbase.mobiletestkit.javacommon.util;

public class Log {
    private static Logger LOGGER;

    public static void init(Logger logger) {
        if(LOGGER == null) {
            LOGGER = logger;
        }
    }

    public static void i(String tag, String msg) {
        LOGGER.i(tag, msg);
    }

    public static void d(String tag, String msg) {
        LOGGER.d(tag, msg);
    }

    public static void e(String tag, String msg) {
        LOGGER.e(tag, msg);
    }

    public static void e(String tag, String msg, Throwable throwable) {
        LOGGER.e(tag, msg, throwable);
    }

    public static void w(String tag, String msg) {
        LOGGER.w(tag, msg);
    }

    public static void w(String tag, String msg, Throwable throwable) {
        LOGGER.w(tag, msg, throwable);
    }
}
