package com.couchbase.CouchbaseLiteServ;


import android.support.v7.app.AppCompatActivity;
import android.os.Bundle;
import android.content.Context;
import android.util.Log;
import android.widget.TextView;

import com.couchbase.CouchbaseLiteServ.server.Server;

import java.io.IOException;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.net.SocketException;
import java.util.Enumeration;


public class MainActivity extends AppCompatActivity {

    private Server server;
    private final static int PORT = 8080;
    private static Context context;
    public static String ip = getLocalIpAddress();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        TextView textView = findViewById(R.id.textView);
        textView.setText("Running http server @" + MainActivity.ip + ":" + PORT);
        try{
            server = new Server(MainActivity.ip, PORT);
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

    public static String getLocalIpAddress() {

        try {
            for (Enumeration<NetworkInterface> en = NetworkInterface.getNetworkInterfaces(); en.hasMoreElements();) {
                NetworkInterface intf = en.nextElement();
                System.out.println(intf.getName());
                for (Enumeration<InetAddress> enumIpAddr = intf.getInetAddresses(); enumIpAddr.hasMoreElements();) {
                    InetAddress inetAddress = enumIpAddr.nextElement();
                    String name = intf.getName();
                    if (!inetAddress.isLoopbackAddress() && (intf.getName().equals("eth1") || intf.getName().equals("wlan0")) && (inetAddress instanceof Inet4Address)) {
                        return inetAddress.getHostAddress();
                    }
                }
            }
        } catch (SocketException ex) {
            Log.e("CBL", ex.toString());
        }
        return null;
    }
}
