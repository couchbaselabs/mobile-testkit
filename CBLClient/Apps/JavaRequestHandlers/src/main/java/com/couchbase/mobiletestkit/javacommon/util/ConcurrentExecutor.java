package com.couchbase.mobiletestkit.javacommon.util;

import java.util.concurrent.Executor;
import java.util.concurrent.Executors;


public class ConcurrentExecutor {
    public static final Executor EXECUTOR = Executors.newSingleThreadExecutor();
}
