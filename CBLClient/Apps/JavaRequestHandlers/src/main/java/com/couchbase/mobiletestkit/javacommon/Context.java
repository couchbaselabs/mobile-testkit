package com.couchbase.mobiletestkit.javacommon;

import java.io.File;
import java.io.InputStream;

public interface Context {
    File getFilesDir();
    InputStream getAsset(String name);
    String getPlatform();
    String getLocalIpAddress();
}
