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
    private static boolean stopped = false;

    public static void main(String[] args) throws IOException {
        //ServerRunner.executeInstance(server);
        new TestServerMain().startServer(false);
    }

    public void startServer(boolean asService) {
        NanoHTTPD server = null;
        try {
            String ip = context.getLocalIpAddress();  //here the context hands out an ip address of 0.0.0.0
            Server.memory.setIpAddress(ip);

            server = new Server(context, PORT);
            server.start(5000, false);

            Log.i("JavaDesktop", "Launching a HTTP server at " + ip + ", port = " + PORT);
        } catch (IOException var3) {
            System.err.println("Couldn't start server:\n" + var3);
            System.exit(-1);
        }

        if (asService) {
            waitForStopService();
        } else {
            waitForEnter();
        }

        if (server != null) {
            server.stop();
            System.out.println("Server stopped.\n");
        }
    }

    private void waitForEnter() {
        System.out.println("Server started, Hit Enter to stop.\n");
        try {
            System.in.read();
        } catch (Throwable th) { }
    }

    private synchronized void waitForStopService() {
        try {
            wait();
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        stopped = false;
    }

    private synchronized void notifyStopped() {
        stopped = true;
        notifyAll();
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
        startServer(true);
    }

    @Override
    public void stop() throws Exception {
        Log.i("JavaDesktop", "Stopping TestServer daemon service.");
        notifyStopped();
    }

    @Override
    public void destroy() {
        Log.i("JavaDesktop", "TestServer daemon service is destroyed.");
    }
}
