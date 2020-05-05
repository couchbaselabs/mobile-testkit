package com.couchbase.javaws;

import com.couchbase.mobiletestkit.javacommon.Context;

import javax.servlet.ServletRequest;
import java.io.File;
import java.io.InputStream;
import java.util.Base64;

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
        return "java-ws";
    }

    @Override
    public File getFilesDir() {
        /*
        this function to provide temp directory location
        where CouchbaseLite database files and log files will be stored
        in Tomcat structure, this points to %CATALINE_HOME%/temp/
         */
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
    public File getExternalFilesDir(String filetype) {
        /*
        this function to provide a location
        that zipped log archive file will temporarily be stored
        in Tomcat structure, this points to %CATALINE_HOME%/temp/TestServerTemp/
        and a subdirectory with the value of filetype will be created under
         */
        File externalFilesDir = new File(getFilesDir().getAbsoluteFile(), filetype);
        if(!externalFilesDir.exists()){
            try {
                externalFilesDir.mkdir();
            }catch(SecurityException se){
                throw se;
            }
        }
        return externalFilesDir;
    }

    @Override
    public String getLocalIpAddress() {
        return servletRequest.getServerName();
    }

    @Override
    public String encodeBase64(byte[] hashBytes){
        // load java.util.Base64 in java webservice app
        return Base64.getEncoder().encodeToString(hashBytes);
    }
}
