package com.couchbase.mobiletestkit.javatestserver;

import com.couchbase.mobiletestkit.javacommon.util.Logger;

public class TestServerLogger implements Logger {
    @Override
    public void i(String tag, String msg) {
        System.out.println("INFO " + tag + ": " + msg);
    }

    @Override
    public void d(String tag, String msg) {
        System.out.println("DEBUG " + tag + ": " + msg);
    }

    @Override
    public void e(String tag, String msg) {
        System.out.println("ERROR " + tag + ": " + msg);
    }

    @Override
    public void e(String tag, String msg, Throwable throwable) {
        System.out.println("ERROR " + tag + ": " + msg + " - " + throwable);
        throwable.printStackTrace();
    }

    @Override
    public void w(String tag, String msg) {
        System.out.println("WARNING " + tag + ": " + msg);
    }

    @Override
    public void w(String tag, String msg, Throwable throwable) {
        System.out.println("WARNING " + tag + ": " + msg + " - " + throwable);
        throwable.printStackTrace();
    }
}
