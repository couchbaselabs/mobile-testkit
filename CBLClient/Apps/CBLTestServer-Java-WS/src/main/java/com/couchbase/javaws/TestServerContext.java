package com.couchbase.javaws;

import com.couchbase.mobiletestkit.javacommon.Context;

import javax.servlet.ServletRequest;
import java.io.File;
import java.io.InputStream;

public class TestServerContext implements Context {
    private ServletRequest servletRequest;

    public static final String TMP_DIR = System.getProperty("java.io.tmpdir");

    public TestServerContext(ServletRequest request){
        this.servletRequest = request;
    }

    @Override
    public InputStream getAsset(String name) {
        return getClass().getResourceAsStream("/" + name);
    }

    @Override
    public String getPlatform() {
        return "android";
    }

    @Override
    public File getFilesDir() {
        //return new File(servletRequest.getServletContext().getRealPath("CouchbaseLiteTemp"));
        File temp_dir = new File(TMP_DIR, "TestServerTemp");
        if(!temp_dir.exists()){
            try {
                temp_dir.mkdir();
            }catch(SecurityException se){
                throw se;
            }
        }

        return temp_dir;
    }

    @Override
    public String getLocalIpAddress() {
        return servletRequest.getServerName();
    }
}
