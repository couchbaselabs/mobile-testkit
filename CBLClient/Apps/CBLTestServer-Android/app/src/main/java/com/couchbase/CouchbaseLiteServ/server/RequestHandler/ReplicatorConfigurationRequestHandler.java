package com.couchbase.CouchbaseLiteServ.server.RequestHandler;


import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.Authenticator;
import com.couchbase.lite.ConflictResolver;
import com.couchbase.lite.Database;
import com.couchbase.lite.DatabaseEndpoint;
import com.couchbase.lite.ReplicatorConfiguration;
import com.couchbase.lite.ReplicatorConfiguration.Builder;
import com.couchbase.lite.URLEndpoint;

import java.net.MalformedURLException;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.Dictionary;
import java.util.List;
import java.util.Map;

public class ReplicatorConfigurationRequestHandler {

    public Builder builderCreate(Args args) throws MalformedURLException, URISyntaxException {
        Database sourceDb = args.get("sourceDb");
        Database targetDb = args.get("targetDb");
        URI targetURI = null;
        if (args.get("targetURI") != null) {
            targetURI = new URI((String) args.get("targetURI"));
        }
        if (targetDb != null){
            DatabaseEndpoint target = new DatabaseEndpoint(targetDb);
            return new Builder(sourceDb, target);
        } else if (targetURI != null){
            URLEndpoint target = new URLEndpoint(targetURI);
            return new Builder(sourceDb, target);
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
        Authenticator authenticator = args.get("authenticator");
        ConflictResolver conflictResolver = args.get("conflictResolver");
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
        Builder builder;
        if (sourceDb != null && targetURL != null) {
            URLEndpoint target = new URLEndpoint(targetURL);
            builder = new Builder(sourceDb, target);
        } else if (sourceDb != null && targetDb != null) {
            DatabaseEndpoint target = new DatabaseEndpoint(targetDb);
            builder = new Builder(sourceDb, target);
        } else {
            throw new Exception("\"No source db provided or target url provided\"");
        }
        if (continuous != null) {
            builder.setContinuous(true);
        }
        if (headers != null) {
            builder.setHeaders(headers);
        }
        builder.setAuthenticator(authenticator);
        builder.setReplicatorType(replType);
        if (conflictResolver != null) {
            builder.setConflictResolver(conflictResolver);
        }
        if (channels != null) {
            builder.setChannels(channels);
        }
        if (documentIds != null) {
            builder.setDocumentIDs(documentIds);
        }
        return builder.build();
    }

    public ReplicatorConfiguration create(Args args) {
        Builder builder = args.get("replicatorBuilder");
        return builder.build();
    }

    public Authenticator getAuthenticator(Args args){
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        return replicatorConfiguration.getAuthenticator();
    }

    public List<String>  getChannels(Args args){
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        return replicatorConfiguration.getChannels();
    }

    public ConflictResolver getConflictResolver(Args args){
        ReplicatorConfiguration replicatorConfiguration = args.get("configuration");
        return replicatorConfiguration.getConflictResolver();
    }

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
        Builder builder = args.get("replicatorBuilder");
        Authenticator authenticator = args.get("authenticator");
        builder.setAuthenticator(authenticator);
    }

    public void setChannels(Args args){
        Builder builder = args.get("replicatorBuilder");
        List<String> channels = args.get("channels");
        builder.setChannels(channels);
    }

    public void setConflictResolver(Args args){
        Builder builder = args.get("replicatorBuilder");
        ConflictResolver conflictResolver = args.get("conflictResolver");
        builder.setConflictResolver(conflictResolver);
    }

    public void setContinuous(Args args){
        Builder builder = args.get("replicatorBuilder");
        Boolean continuous = args.get("continuous");
        builder.setContinuous(continuous);
    }

    public void setDocumentIDs(Args args){
        Builder builder = args.get("replicatorBuilder");
        List<String> documentIds = args.get("documentIds");
        builder.setDocumentIDs(documentIds);
    }

    public void setPinnedServerCertificate(Args args){
        Builder builder = args.get("replicatorBuilder");
        byte[] cert = args.get("cert");
        builder.setPinnedServerCertificate(cert);
    }

    public void setReplicatorType(Args args){
        Builder builder = args.get("replicatorBuilder");
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
        builder.setReplicatorType(replicatorType);
    }

}
