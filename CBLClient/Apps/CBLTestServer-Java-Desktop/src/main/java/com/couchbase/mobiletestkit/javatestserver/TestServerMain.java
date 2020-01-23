package com.couchbase.mobiletestkit.javatestserver;

import com.couchbase.mobiletestkit.javacommon.Context;
import com.couchbase.mobiletestkit.javalistener.Server;
import com.couchbase.mobiletestkit.javacommon.util.Log;
import com.couchbase.lite.CouchbaseLite;
import org.nanohttpd.protocols.http.NanoHTTPD;
import org.nanohttpd.util.ServerRunner;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;

public class TestServerMain {
    private static final int PORT = 8080;
    private static final String TMP_DIR = System.getProperty("java.io.tmpdir");
    private static Context context;

    public static void main(String[] args) throws IOException {
        Log.init(new TestServerLogger());
        CouchbaseLite.init();

        File tempDir = new File(TMP_DIR, "TestServerTemp");
        context = new TestServerContext(tempDir);
        Server.setContext(context);

        String ip = context.getLocalIpAddress();  //here the context hands out an ip address of 0.0.0.0
        Server.memory.setIpAddress(ip);
        Log.i("JavaDesktop", "Starting the server at " + ip + ", port = " + PORT);

        NanoHTTPD server = new Server(context, PORT);

        ServerRunner.executeInstance(server);
    }
}
