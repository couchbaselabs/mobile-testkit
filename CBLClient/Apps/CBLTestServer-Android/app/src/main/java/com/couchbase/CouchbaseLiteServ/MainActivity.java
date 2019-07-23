package com.couchbase.CouchbaseLiteServ;


import android.os.Bundle;
import android.support.v7.app.AppCompatActivity;
import android.util.Log;
import android.widget.TextView;

import java.io.IOException;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.net.SocketException;
import java.util.Enumeration;

import com.couchbase.CouchbaseLiteServ.server.Server;


public class MainActivity extends AppCompatActivity {
    public static final String ip = getLocalIpAddress();
    private static final String TAG = "MAIN";

    private Server server;
    private final static int PORT = 8080;


    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        TextView textView = findViewById(R.id.textView);
        textView.setText(getString(R.string.server_running, MainActivity.ip, PORT));
        try {
            server = new Server(MainActivity.ip, PORT);
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

    public static String getLocalIpAddress() {

        try {
            for (Enumeration<NetworkInterface> en = NetworkInterface.getNetworkInterfaces(); en.hasMoreElements(); ) {
                NetworkInterface intf = en.nextElement();
                String intf_name = intf.getName();
                Log.d(TAG, "intf_name: " + intf_name);
                for (Enumeration<InetAddress> enumIpAddr = intf.getInetAddresses(); enumIpAddr.hasMoreElements(); ) {
                    InetAddress inetAddress = enumIpAddr.nextElement();
                    if (!inetAddress.isLoopbackAddress() && (intf_name.equals("eth1") || intf_name
                        .equals("wlan0")) && (inetAddress instanceof Inet4Address)) {
                        return inetAddress.getHostAddress();
                    }
                }
            }
        }
        catch (SocketException ex) {
            Log.e(TAG, "Socket exception: ", ex);
        }
        return null;
    }
}
