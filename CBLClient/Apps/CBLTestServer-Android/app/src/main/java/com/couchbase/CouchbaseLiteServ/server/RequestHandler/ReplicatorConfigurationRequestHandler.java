package com.couchbase.CouchbaseLiteServ.server.RequestHandler;


import android.content.Context;
import android.content.res.AssetManager;
import android.util.Log;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.EnumSet;
import java.util.List;
import java.util.Map;

import com.couchbase.CouchbaseLiteServ.CouchbaseLiteServ;
import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.Authenticator;
import com.couchbase.lite.Conflict;
import com.couchbase.lite.ConflictResolver;
import com.couchbase.lite.Database;
import com.couchbase.lite.DatabaseEndpoint;
import com.couchbase.lite.Document;
import com.couchbase.lite.DocumentFlag;
import com.couchbase.lite.ReplicationFilter;
import com.couchbase.lite.ReplicatorConfiguration;
import com.couchbase.lite.URLEndpoint;


public class ReplicatorConfigurationRequestHandler {
    private static final String TAG = "REPLCONFIGHANDLER";

    public ReplicatorConfiguration builderCreate(Args args) throws URISyntaxException {
        Database sourceDb = args.get("sourceDb");
        Database targetDb = args.get("targetDb");
        URI targetURI = null;
        if (args.get("targetURI") != null) {
            targetURI = new URI((String) args.get("targetURI"));
        }
        if (targetDb != null) {
            DatabaseEndpoint target = new DatabaseEndpoint(targetDb);
            return new ReplicatorConfiguration(sourceDb, target);
        }
        else if (targetURI != null) {
            URLEndpoint target = new URLEndpoint(targetURI);
            return new ReplicatorConfiguration(sourceDb, target);
        }
        else {
            throw new IllegalArgumentException("Incorrect configuration parameter provided");
        }
    }

    public ReplicatorConfiguration configure(Args args) throws Exception {
        Database sourceDb = args.get("source_db");
        URI targetURL = null;
        if (args.get("target_url") != null) {
            targetURL = new URI((String) args.get("target_url"));
        }
        Database targetDb = args.get("target_db");
        String replicatorType = args.get("replication_type");
        Boolean continuous = args.get("continuous");
        List<String> channels = args.get("channels");
        List<String> documentIds = args.get("documentIDs");
        String pinnedservercert = args.get("pinnedservercert");
        Authenticator authenticator = args.get("authenticator");
        Boolean push_filter = args.get("push_filter");
        Boolean pull_filter = args.get("pull_filter");
        String filter_callback_func = args.get("filter_callback_func");
        String conflict_resolver = args.get("conflict_resolver");
        // ConflictResolver conflictResolver = args.get("conflictResolver");
        Map<String, String> headers = args.get("headers");

        if (replicatorType == null) {
            replicatorType = "push_pull";
        }
        replicatorType = replicatorType.toLowerCase();
        ReplicatorConfiguration.ReplicatorType replType;
        if (replicatorType.equals("push")) {
            replType = ReplicatorConfiguration.ReplicatorType.PUSH;
        }
        else if (replicatorType.equals("pull")) {
            replType = ReplicatorConfiguration.ReplicatorType.PULL;
        }
        else {
            replType = ReplicatorConfiguration.ReplicatorType.PUSH_AND_PULL;
        }
        ReplicatorConfiguration config;
        if (sourceDb != null && targetURL != null) {
            URLEndpoint target = new URLEndpoint(targetURL);
            config = new ReplicatorConfiguration(sourceDb, target);
        }
        else if (sourceDb != null && targetDb != null) {
            DatabaseEndpoint target = new DatabaseEndpoint(targetDb);
            config = new ReplicatorConfiguration(sourceDb, target);
        }
        else {
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

        Log.d(TAG, "Args: " + args);
        if (pinnedservercert != null) {
            Context context = CouchbaseLiteServ.getAppContext();
            byte[] ServerCert = this.getPinnedCertFile(context);
            // Set pinned certificate.
            config.setPinnedServerCertificate(ServerCert);
        }
        if (push_filter) {
            switch (filter_callback_func) {
                case "boolean":
                    config.setPushFilter(new ReplicatorBooleanFilterCallback());
                    break;
                case "deleted":
                    config.setPushFilter(new ReplicatorDeletedFilterCallback());
                    break;
                case "access_revoked":
                    config.setPushFilter(new ReplicatorAccessRevokedFilterCallback());
                    break;
                default:
                    config.setPushFilter(new DefaultReplicatorFilterCallback());
                    break;
            }
        }
        if (pull_filter) {
            switch (filter_callback_func) {
                case "boolean":
                    config.setPullFilter(new ReplicatorBooleanFilterCallback());
                    break;
                case "deleted":
                    config.setPullFilter(new ReplicatorDeletedFilterCallback());
                    break;
                case "access_revoked":
                    config.setPullFilter(new ReplicatorAccessRevokedFilterCallback());
                    break;
                default:
                    config.setPullFilter(new DefaultReplicatorFilterCallback());
                    break;
            }
        }
        switch (conflict_resolver) {
            case "local_wins":
                config.setConflictResolver(new LocalWinsCustomConflictResolver());
                break;
            case "remote_wins":
                config.setConflictResolver(new RemoteWinsCustomConflictResolver());
            default:
                ConflictResolver cr = config.getConflictResolver();
                break;
        }
        return config;
    }

    public ReplicatorConfiguration create(Args args) {
        return args.get("configuration");
    }

    public Authenticator getAuthenticator(Args args) {
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        return replicatorConfiguration.getAuthenticator();
    }

    public List<String> getChannels(Args args) {
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        return replicatorConfiguration.getChannels();
    }

    /*public ConflictResolver getConflictResolver(Args args){
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        return replicatorConfiguration.getConflictResolver();
    }*/

    public Database getDatabase(Args args) {
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        return replicatorConfiguration.getDatabase();
    }

    public List<String> getDocumentIDs(Args args) {
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        return replicatorConfiguration.getDocumentIDs();
    }

    public byte[] getPinnedServerCertificate(Args args) {
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        return replicatorConfiguration.getPinnedServerCertificate();
    }

    public String getReplicatorType(Args args) {
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        return replicatorConfiguration.getReplicatorType().toString();
    }

    public String getTarget(Args args) {
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        return replicatorConfiguration.getTarget().toString();
    }

    public Boolean isContinuous(Args args) {
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        return replicatorConfiguration.isContinuous();
    }

    public void setAuthenticator(Args args) {
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        Authenticator authenticator = args.get("authenticator");
        replicatorConfiguration.setAuthenticator(authenticator);
    }

    public void setChannels(Args args) {
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        List<String> channels = args.get("channels");
        replicatorConfiguration.setChannels(channels);
    }

    /*public void setConflictResolver(Args args){
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        ConflictResolver conflictResolver = args.get("conflictResolver");
        replicatorConfiguration.setConflictResolver(conflictResolver);
    }*/

    public void setContinuous(Args args) {
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        Boolean continuous = args.get("continuous");
        replicatorConfiguration.setContinuous(continuous);
    }

    public void setDocumentIDs(Args args) {
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        List<String> documentIds = args.get("documentIds");
        replicatorConfiguration.setDocumentIDs(documentIds);
    }

    public void setPinnedServerCertificate(Args args) {
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        byte[] cert = args.get("cert");
        replicatorConfiguration.setPinnedServerCertificate(cert);
    }

    public void setReplicatorType(Args args) {
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

    private byte[] getPinnedCertFile(Context context) {
        AssetManager assetManager = context.getAssets();
        InputStream is;
        byte[] bytes = new byte[0];
        try {
            is = assetManager.open("sg_cert.cer");
            return (toByteArray(is));
        }
        catch (IOException e) {
            Log.e(TAG, "Failed to retrieve cert", e);
        }
        return null;

    }

    public static byte[] toByteArray(InputStream is) {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        byte[] b = new byte[1024];

        try {
            int bytesRead = is.read(b);
            while (bytesRead != -1) {
                bos.write(b, 0, bytesRead);
                bytesRead = is.read(b);
            }
        }
        catch (IOException io) {
            Log.w(TAG, "Got exception " + io.getMessage() + ", Ignoring...");
        }

        return bos.toByteArray();
    }
}

class ReplicatorBooleanFilterCallback implements ReplicationFilter {
    @Override
    public boolean filtered(Document document, EnumSet<DocumentFlag> flags) {
        String key = "new_field_1";
        if (document.contains(key)) {
            return document.getBoolean(key);
        }
        return true;
    }

}

class DefaultReplicatorFilterCallback implements ReplicationFilter {
    @Override
    public boolean filtered(Document document, EnumSet<DocumentFlag> flags) {
        return true;
    }

}

class ReplicatorDeletedFilterCallback implements ReplicationFilter {
    @Override
    public boolean filtered(Document document, EnumSet<DocumentFlag> flags) {
        return !(flags.contains(DocumentFlag.DocumentFlagsDeleted));
    }
}

class ReplicatorAccessRevokedFilterCallback implements ReplicationFilter {
    @Override
    public boolean filtered(Document document, EnumSet<DocumentFlag> flags) {
        return !(flags.contains(DocumentFlag.DocumentFlagsAccessRemoved));
    }
}

class LocalWinsCustomConflictResolver implements ConflictResolver {
    @Override
    public Document resolve(Conflict conflict) {
        Document localDoc = conflict.getLocalDocument();
        Document remoteDoc = conflict.getRemoteDocument();
        String docId = conflict.getDocumentId();
        System.out.println("Local copy of doc with doc id - " + docId);
        System.out.println(localDoc.toString());
        System.out.println("Remote copy of doc with doc id - " + docId);
        System.out.println(remoteDoc.toString());
        return localDoc;
    }
}

class RemoteWinsCustomConflictResolver implements ConflictResolver {
    @Override
    public Document resolve(Conflict conflict) {
        Document localDoc = conflict.getLocalDocument();
        Document remoteDoc = conflict.getRemoteDocument();
        String docId = conflict.getDocumentId();
        System.out.println("Local copy of doc with doc id - " + docId);
        System.out.println(localDoc.toString());
        System.out.println("Remote copy of doc with doc id - " + docId);
        System.out.println(remoteDoc.toString());
        return localDoc;
    }
}




