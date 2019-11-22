package com.couchbase.mobiletestkit.javatestserver;

import com.couchbase.mobiletestkit.javacommon.Context;
import com.couchbase.mobiletestkit.javacommon.util.Log;

import java.io.File;
import java.io.InputStream;
import java.net.*;
import java.util.Collections;
import java.util.Enumeration;
import java.util.Base64;

public class TestServerContext implements Context {
    private final String TAG = "JavaContext";
    private File directory;

    public TestServerContext(File directory) {
        this.directory = directory;
    }

    @Override
    public File getFilesDir() {
        return this.directory;
    }


    @Override
    public InputStream getAsset(String name) {
        return TestServerMain.class.getResourceAsStream("/" + name);
    }

    @Override
    public String getPlatform() {
        return "java";
    }

    @Override
    public String getLocalIpAddress() {
        // bind 0.0.0.0 for java standalone application
        return "0.0.0.0";
    }

    @Override
    public String encodeBase64(byte[] hashBytes){
        // load java.util.Base64 in java standalone app
        return Base64.getEncoder().encodeToString(hashBytes);
    }
}