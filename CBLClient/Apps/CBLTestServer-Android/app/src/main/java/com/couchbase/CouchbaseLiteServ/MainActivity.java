package com.couchbase.CouchbaseLiteServ;


import android.support.v7.app.AppCompatActivity;
import android.os.Bundle;
import android.content.Context;

import com.couchbase.CouchbaseLiteServ.server.Server;

import java.io.IOException;


public class MainActivity extends AppCompatActivity {

    private Server server;
    private final static int PORT = 8080;
    private static Context context;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        try{
            server = new Server(PORT);
            server.start();
        } catch (IOException e) {
            e.printStackTrace();
        }
        MainActivity.context = getApplicationContext();

    }

    @Override
    protected void onStop() {
        super.onStop();
        if (server != null)
            server.stop();
    }

    public static Context getAppContext() {
        return MainActivity.context;
    }

}
