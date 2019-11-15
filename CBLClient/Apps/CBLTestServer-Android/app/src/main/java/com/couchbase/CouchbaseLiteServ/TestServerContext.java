package com.couchbase.CouchbaseLiteServ;

import com.couchbase.mobiletestkit.javacommon.Context;
import com.couchbase.mobiletestkit.javacommon.util.Log;

import java.io.File;
import java.io.InputStream;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.NetworkInterface;

import java.util.Enumeration;

public class TestServerContext implements Context {
    private static final String TAG = "TestServerContext";

    @Override
    public InputStream getAsset(String name) {
        return getClass().getResourceAsStream("/" + name);
    }

    @Override
    public String getPlatform() {
        return "android";
    }

    @Override
    public File getFilesDir() {
        return CouchbaseLiteServ.getAppContext().getFilesDir();
    }

    @Override
    public String getLocalIpAddress() {
        String ip = "";
        try {
            for (Enumeration<NetworkInterface> en = NetworkInterface.getNetworkInterfaces(); en.hasMoreElements(); ) {
                NetworkInterface intf = en.nextElement();
                String intf_name = intf.getName();
                Log.d(TAG, "intf_name: " + intf_name);
                for (Enumeration<InetAddress> enumIpAddr = intf.getInetAddresses(); enumIpAddr.hasMoreElements(); ) {
                    InetAddress inetAddress = enumIpAddr.nextElement();
                    if (!inetAddress.isLoopbackAddress() && (intf_name.equals("eth1") || intf_name
                            .equals("wlan0")) && (inetAddress instanceof Inet4Address)) {
                        ip =  inetAddress.getHostAddress();
                        break;
                    }
                }
                if(!ip.isEmpty()) {
                    break;
                }
            }
        }
        catch (java.net.SocketException socketEx) {
            Log.e(TAG, "Socket exception: ", socketEx);
        }
        return ip;
    }

}
