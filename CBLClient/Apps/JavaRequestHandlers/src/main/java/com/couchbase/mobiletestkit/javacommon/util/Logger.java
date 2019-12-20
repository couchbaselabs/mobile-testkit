package com.couchbase.mobiletestkit.javacommon.util;

public interface Logger {
    void i(String tag, String msg);
    void d(String tag, String msg);
    void e(String tag, String msg);
    void e(String tag, String msg, Throwable throwable);
    void w(String tag, String msg);
    void w(String tag, String msg, Throwable throwable);
}
