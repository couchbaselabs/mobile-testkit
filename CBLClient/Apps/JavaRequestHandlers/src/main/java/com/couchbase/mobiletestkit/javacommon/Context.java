package com.couchbase.mobiletestkit.javacommon;

import java.io.File;
import java.io.InputStream;

public interface Context {
    File getFilesDir();
    InputStream getAsset(String name);
    String getPlatform();
    String getLocalIpAddress();

    /*
     * the customEncode method allows custom Base64 package
     * is loaded by platform specific:
     * java.util.Base64 in java standalone and web application
     * android.util.Base64 in android apps
     */
    String encodeBase64(byte[] hashBytes);
}
