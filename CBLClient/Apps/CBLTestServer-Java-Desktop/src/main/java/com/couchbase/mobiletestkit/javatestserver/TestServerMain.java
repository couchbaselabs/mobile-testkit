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
    private static Context context;

    public static void main(String[] args) throws IOException {
        Log.init(new TestServerLogger());
        CouchbaseLite.init();

        String curPath = new File(".").getCanonicalPath();
        context = new TestServerContext(new File(curPath));
        Server.setContext(context);

        String ip = context.getLocalIpAddress();
        Server.memory.setIpAddress(ip);
        Log.i("JavaDesktop", "Starting the server at " + ip + ", port = " + PORT);

        NanoHTTPD server = new Server(context, PORT);

        ServerRunner.executeInstance(server);
    }
}
