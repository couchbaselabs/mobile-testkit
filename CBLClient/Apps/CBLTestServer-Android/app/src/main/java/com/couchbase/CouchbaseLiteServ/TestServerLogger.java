package com.couchbase.CouchbaseLiteServ;
import com.couchbase.mobiletestkit.javacommon.log.Logger;
import android.util.*;

public class TestServerLogger implements Logger {
    @Override
    public void i(String tag, String msg) {
        Log.i(tag, msg);
    }

    @Override
    public void d(String tag, String msg) {
        Log.d(tag, msg);
    }

    @Override
    public void e(String tag, String msg) {
        Log.e(tag, msg);
    }

    @Override
    public void e(String tag, String msg, Throwable throwable) {
        Log.e(tag, msg, throwable);
    }

    @Override
    public void w(String tag, String msg) {
        Log.w(tag, msg);
    }

    @Override
    public void w(String tag, String msg, Throwable throwable) {
        Log.w(tag, msg, throwable);
    }
}
