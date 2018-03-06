package com.couchbase.CouchbaseLiteServ.server.RequestHandler;


import android.util.Log;

import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.CouchbaseLiteServ.server.Server;
import com.couchbase.lite.Authenticator;
// import com.couchbase.lite.ConflictResolver;
import com.couchbase.lite.Database;
import com.couchbase.lite.DatabaseEndpoint;
import com.couchbase.lite.ReplicatorConfiguration;
import com.couchbase.lite.URLEndpoint;
import com.couchbase.litecore.C4Socket;

import java.net.MalformedURLException;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.Dictionary;
import java.util.List;
import java.util.Map;
import java.io.InputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import javax.net.ssl.X509TrustManager;
import javax.net.ssl.TrustManager;
import java.security.cert.X509Certificate;
import javax.net.ssl.SSLContext;
import javax.net.ssl.HttpsURLConnection;
import java.security.GeneralSecurityException;
import android.content.res.AssetManager;
import android.content.Context;


public class ReplicatorConfigurationRequestHandler {

    public ReplicatorConfiguration builderCreate(Args args) throws MalformedURLException, URISyntaxException {
        Database sourceDb = args.get("sourceDb");
        Database targetDb = args.get("targetDb");
        URI targetURI = null;
        if (args.get("targetURI") != null) {
            targetURI = new URI((String) args.get("targetURI"));
        }
        if (targetDb != null){
            DatabaseEndpoint target = new DatabaseEndpoint(targetDb);
            return new ReplicatorConfiguration(sourceDb, target);
        } else if (targetURI != null){
            URLEndpoint target = new URLEndpoint(targetURI);
            return new ReplicatorConfiguration(sourceDb, target);
        } else {
            throw new IllegalArgumentException("Incorrect configuration parameter provided");
        }
    }

    public ReplicatorConfiguration configure(Args args) throws Exception {
        Database sourceDb = args.get("source_db");
        URI targetURL = null;
        if (args.get("target_url") != null){
            targetURL = new URI((String) args.get("target_url"));
        }
        Database targetDb = args.get("target_db");
        String replicatorType = args.get("replication_type");
        Boolean continuous = args.get("continuous");
        List<String> channels = args.get("channels");
        List<String> documentIds = args.get("documentIDs");
        String pinnedservercert = args.get("pinnedservercert");
        Authenticator authenticator = args.get("authenticator");
        // ConflictResolver conflictResolver = args.get("conflictResolver");
        Map<String, String> headers = args.get("headers");

        replicatorType = replicatorType.toLowerCase();
        ReplicatorConfiguration.ReplicatorType replType;
        if (replicatorType.equals("push")) {
            replType = ReplicatorConfiguration.ReplicatorType.PUSH;
        } else if (replicatorType.equals("pull")) {
            replType = ReplicatorConfiguration.ReplicatorType.PULL;
        } else {
            replType = ReplicatorConfiguration.ReplicatorType.PUSH_AND_PULL;
        }
        ReplicatorConfiguration config;
        if (sourceDb != null && targetURL != null) {
            URLEndpoint target = new URLEndpoint(targetURL);
            config = new ReplicatorConfiguration(sourceDb, target);
        } else if (sourceDb != null && targetDb != null) {
            DatabaseEndpoint target = new DatabaseEndpoint(targetDb);
            config = new ReplicatorConfiguration(sourceDb, target);
        } else {
            throw new Exception("\"No source db provided or target url provided\"");
        }
        if (continuous != null) {
            config.setContinuous(continuous);
        }
        else {
            config.setContinuous(false);
        }
        if (headers != null) {
            config.setHeaders(headers);
        }
        config.setAuthenticator(authenticator);
        config.setReplicatorType(replType);
        /*if (conflictResolver != null) {
            config.setConflictResolver(conflictResolver);
        }*/
        if (channels != null) {
            config.setChannels(channels);
        }
        if (documentIds != null) {
            config.setDocumentIDs(documentIds);
        }
        System.out.println(args);
        if (pinnedservercert != null){
            Context context = com.couchbase.CouchbaseLiteServ.MainActivity.getAppContext();
            byte[] ServerCert = this.getPinnedCertFile(context);
            // Set pinned certificate.
            // config.setPinnedServerCertificate(ServerCert);

            // Create a trust manager that does not validate certificate chains
            TrustManager[] trustAllCerts = new TrustManager[] {
                    new X509TrustManager() {
                        public java.security.cert.X509Certificate[] getAcceptedIssuers() {
                            return new X509Certificate[0];
                        }
                        public void checkClientTrusted(
                                java.security.cert.X509Certificate[] certs, String authType) {
                        }
                        public void checkServerTrusted(
                                java.security.cert.X509Certificate[] certs, String authType) {
                        }
                    }
            };

            // Install the all-trusting trust manager
            try {
                SSLContext sc = SSLContext.getInstance("SSL");
                sc.init(null, trustAllCerts, new java.security.SecureRandom());
                HttpsURLConnection.setDefaultSSLSocketFactory(sc.getSocketFactory());

            } catch (GeneralSecurityException e) {
            }

            config.setPinnedServerCertificate(ServerCert);
        }
        return config;
    }

    public ReplicatorConfiguration create(Args args) {
        ReplicatorConfiguration config = args.get("configuration");
        return config;
    }

    public Authenticator getAuthenticator(Args args){
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        return replicatorConfiguration.getAuthenticator();
    }

    public List<String>  getChannels(Args args){
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        return replicatorConfiguration.getChannels();
    }

    /*public ConflictResolver getConflictResolver(Args args){
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        return replicatorConfiguration.getConflictResolver();
    }*/

    public Database getDatabase(Args args){
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        return replicatorConfiguration.getDatabase();
    }

    public List<String> getDocumentIDs(Args args){
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        return replicatorConfiguration.getDocumentIDs();
    }

    public byte[] getPinnedServerCertificate(Args args){
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        return replicatorConfiguration.getPinnedServerCertificate();
    }

    public String getReplicatorType(Args args){
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        return replicatorConfiguration.getReplicatorType().toString();
    }

    public String getTarget(Args args){
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        return replicatorConfiguration.getTarget().toString();
    }

    public Boolean isContinuous(Args args){
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        return replicatorConfiguration.isContinuous();
    }

    public void setAuthenticator(Args args){
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        Authenticator authenticator = args.get("authenticator");
        replicatorConfiguration.setAuthenticator(authenticator);
    }

    public void setChannels(Args args){
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        List<String> channels = args.get("channels");
        replicatorConfiguration.setChannels(channels);
    }

    /*public void setConflictResolver(Args args){
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        ConflictResolver conflictResolver = args.get("conflictResolver");
        replicatorConfiguration.setConflictResolver(conflictResolver);
    }*/

    public void setContinuous(Args args){
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        Boolean continuous = args.get("continuous");
        replicatorConfiguration.setContinuous(continuous);
    }

    public void setDocumentIDs(Args args){
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        List<String> documentIds = args.get("documentIds");
        replicatorConfiguration.setDocumentIDs(documentIds);
    }

    public void setPinnedServerCertificate(Args args){
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        byte[] cert = args.get("cert");
        replicatorConfiguration.setPinnedServerCertificate(cert);
    }

    public void setReplicatorType(Args args){
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        String type = args.get("replType");
        ReplicatorConfiguration.ReplicatorType replicatorType;
        switch (type) {
            case "PUSH":
                replicatorType = ReplicatorConfiguration.ReplicatorType.PUSH;
                break;
            case "PULL":
                replicatorType = ReplicatorConfiguration.ReplicatorType.PULL;
                break;
            default:
                replicatorType = ReplicatorConfiguration.ReplicatorType.PUSH_AND_PULL;
        }
        replicatorConfiguration.setReplicatorType(replicatorType);
    }

//    public static byte[] toByteArray(InputStream input) throws IOException {
//        ByteArrayOutputStream output = new ByteArrayOutputStream();
//        copy(input, output);
//        return output.toByteArray();
//    }

//    public static int copy(InputStream input, OutputStream output) throws IOException {
//        long count = copyLarge(input, output);
//        if (count > Integer.MAX_VALUE) {
//            return -1;
//        }
//        return (int) count;
//    }
//
//    public static long copyLarge(InputStream input, OutputStream output)
//            throws IOException {
//        final int DEFAULT_BUFFER_SIZE = 1024 * 4;
//        byte[] buffer = new byte[DEFAULT_BUFFER_SIZE];
//        long count = 0;
//        int n = 0;
//        while (-1 != (n = input.read(buffer))) {
//            output.write(buffer, 0, n);
//            count += n;
//        }
//        return count;
//    }


    private byte[] getPinnedCertFile(Context context) {
        AssetManager assetManager = context.getAssets();
        InputStream is = null;
        byte[] bytes = new byte[0];
        try {
            is = assetManager.open("sg_cert.cer");
            return (toByteArray(is));
        } catch (IOException e) {
            e.printStackTrace();
        }
        return null;

    }

    public static byte[] toByteArray(InputStream is){
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        byte[] b = new byte[1024];

        try {
            int bytesRead = is.read(b);
            while (bytesRead != -1) {
                bos.write(b, 0, bytesRead);
                bytesRead = is.read(b);
            }
        } catch(IOException io) {
            System.out.println("Got exception " + io.getMessage() + ", Ignoring...");
        }

        byte[] bytes = bos.toByteArray();
        return bytes;
    }

}
