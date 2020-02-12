package com.couchbase.mobiletestkit.javatestserver;

import org.apache.commons.daemon.Daemon;
import org.apache.commons.daemon.DaemonContext;
import org.apache.commons.daemon.DaemonInitException;

import com.couchbase.mobiletestkit.javacommon.Context;
import com.couchbase.mobiletestkit.javalistener.Server;
import com.couchbase.mobiletestkit.javacommon.util.Log;
import com.couchbase.lite.CouchbaseLite;
import org.nanohttpd.protocols.http.NanoHTTPD;

import java.io.File;
import java.io.IOException;


public class TestServerMain implements Daemon {
    private static final int PORT = 8080;
    private static final String TMP_DIR = System.getProperty("java.io.tmpdir");
    private static final String TAG = "TestServer-Java";
    private static Context context;
    private static boolean stopped = false;
    private static TestServerMain testserverLauncherInstance = null;

    /**
     * Main method runs as non-service mode for debugging use
     * @param args
     * @throws IOException
     */
    public static void main(String[] args) throws IOException {
        if(testserverLauncherInstance == null){
            testserverLauncherInstance = new TestServerMain();
        }

        testserverLauncherInstance.initCouchbaseLite();
        Log.i(TAG, "Main");
        testserverLauncherInstance.startServer(stopped);
    }

    /**
     * Static methods called by prunsrv to start/stop
     * the Windows service.  Pass the argument "start"
     * to start the service, and pass "stop" to
     * stop the service.
     *
     * @param args Arguments from prunsrv command line
     **/
    public static void windowsService(String args[]) {
        final String cmd = (args.length <= 0) ? "start" : args[0];
        if ("start".equals(cmd)) {
            if(testserverLauncherInstance == null){
                testserverLauncherInstance = new TestServerMain();
            }

            testserverLauncherInstance.initCouchbaseLite();
            testserverLauncherInstance.startServer(true);
        }
        else {
            try{
                testserverLauncherInstance.stop();
            }
            catch (Exception e){
                e.printStackTrace();
            }
        }
    }

    public void startServer(boolean asService) {
        NanoHTTPD server = null;
        try {
            File tempDir = new File(TMP_DIR, "TestServerTemp");
            context = new TestServerContext(tempDir);
            Server.setContext(context);

            String ip = context.getLocalIpAddress();  //here the context hands out an ip address of 0.0.0.0
            Server.memory.setIpAddress(ip);

            server = new Server(context, PORT);
            server.start(5000, false);

            Log.i(TAG, "A HTTP server launched at " + ip + ", port = " + PORT);
        } catch (IOException var3) {
            Log.e(TAG, "Couldn't start server:\n" + var3);
            System.exit(-1);
        }

        if (asService) {
            waitForStopService();
        } else {
            waitForEnter();
        }

        if (server != null) {
            server.stop();
            Log.i(TAG, "The HTTP Server stopped.\n");
        }
    }

    private void waitForEnter() {
        System.out.println("Server started, Hit Enter to stop.\n");

        try {
            System.in.read();
        } catch (IOException ioe) {
            System.err.println("waiting for entry key, but failed to get:\n" + ioe.toString());
        }
    }

    private synchronized void waitForStopService() {
        if(stopped){
            stopped = false;
            return;
        }
        try {
            // service will be running until stop() method gets called
            // which will notify this wait function and set server to stop
            wait();
        } catch (InterruptedException e) {
            System.err.println("service got interrupted while waiting for notify call.");
        }
        stopped = false;
    }

    private synchronized void notifyStopped() {
        stopped = true;
        notifyAll();
    }

    private void initCouchbaseLite(){
        Log.init(new TestServerLogger());
        CouchbaseLite.init();
        Log.i(TAG, "CouchbaseLite is initialized.");
    }

    @Override
    public void init(DaemonContext dc) throws DaemonInitException, Exception {
        // Log object is not initialized yet, call System.out here
        System.out.println("system.out TestServer service init is called.");
        initCouchbaseLite();
    }

    @Override
    public void start() throws Exception {
        Log.i(TAG, "Starting TestServer application as a service.");
        startServer(true);
    }

    @Override
    public void stop() throws Exception {
        Log.i(TAG, "Stopping TestServer service.");
        notifyStopped();
    }

    @Override
    public void destroy() {
        Log.i(TAG, "TestServer service is destroyed.");
    }
}
