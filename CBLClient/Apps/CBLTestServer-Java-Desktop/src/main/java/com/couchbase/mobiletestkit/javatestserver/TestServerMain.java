package com.couchbase.mobiletestkit.javatestserver;

import org.apache.commons.daemon.Daemon;
import org.apache.commons.daemon.DaemonContext;
import org.apache.commons.daemon.DaemonInitException;

import com.couchbase.mobiletestkit.javacommon.Context;
import com.couchbase.mobiletestkit.javalistener.Server;
import com.couchbase.mobiletestkit.javacommon.util.Log;
import com.couchbase.lite.CouchbaseLite;
import org.nanohttpd.protocols.http.NanoHTTPD;
import org.nanohttpd.util.ServerRunner;

import java.io.File;
import java.io.IOException;


public class TestServerMain implements Daemon {
    private static final int PORT = 8080;
    private static final String TMP_DIR = System.getProperty("java.io.tmpdir");
    private static Context context;

    public static void main(String[] args) throws IOException {
        String ip = context.getLocalIpAddress();  //here the context hands out an ip address of 0.0.0.0
        Server.memory.setIpAddress(ip);
        Log.i("JavaDesktop", "Launching a HTTP server at " + ip + ", port = " + PORT);

        NanoHTTPD server = new Server(context, PORT);
        ServerRunner.executeInstance(server);
    }

    @Override
    public void init(DaemonContext dc) throws DaemonInitException, Exception {
        Log.init(new TestServerLogger());
        CouchbaseLite.init();

        File tempDir = new File(TMP_DIR, "TestServerTemp");
        context = new TestServerContext(tempDir);
        Server.setContext(context);
    }

    @Override
    public void start() throws Exception {
        Log.i("JavaDesktop", "Starting TestServer application as a daemon service.");
        main(null);
    }

    @Override
    public void stop() throws Exception {
        Log.i("JavaDesktop", "Stopping TestServer daemon service.");
    }

    @Override
    public void destroy() {
        Log.i("JavaDesktop", "TestServer daemon service is destroyed.");
    }
}
