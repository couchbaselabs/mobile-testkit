package com.couchbase.CouchbaseLiteServ;


import android.os.Bundle;
import android.support.v7.app.AppCompatActivity;
import android.widget.TextView;

import java.io.IOException;

import com.couchbase.mobiletestkit.javacommon.Context;
import com.couchbase.mobiletestkit.javalistener.Server;
import com.couchbase.mobiletestkit.javacommon.log.Log;



public class MainActivity extends AppCompatActivity{
    private static final String TAG = "MAIN";
    private Server server;
    private final static int PORT = 8080;
    private static Context context;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        context = CouchbaseLiteServ.getTestServerContext();
        String ip = context.getLocalIpAddress();

        setContentView(R.layout.activity_main);
        TextView textView = findViewById(R.id.textView);
        textView.setText(getString(R.string.server_running, ip, PORT));
        Log.init(new TestServerLogger());

        try {
            Server.setContext(context);
            Server.memory.setIpAddress(ip);
            Log.i(TAG,"Starting the server at " + ip + ", port = " + PORT);

            server = new Server(context, PORT);
            server.start();
        }
        catch (IOException e) {
            Log.e(TAG, "Failed starting server", e);
        }
    }

    @Override
    protected void onStop() {
        super.onStop();
        if (server != null) { server.stop(); }
    }
}
