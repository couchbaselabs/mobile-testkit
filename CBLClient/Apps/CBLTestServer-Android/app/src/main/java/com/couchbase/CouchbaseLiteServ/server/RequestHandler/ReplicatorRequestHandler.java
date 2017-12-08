package com.couchbase.CouchbaseLiteServ.server.RequestHandler;

import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.Database;
import com.couchbase.lite.Replicator;
import com.couchbase.lite.ReplicatorChange;
import com.couchbase.lite.ReplicatorChangeListener;
import com.couchbase.lite.ReplicatorConfiguration;

import java.net.URI;
import java.util.List;

public class ReplicatorRequestHandler {
    /* -------------- */
    /* - Replicator - */
    /* -------------- */

    public Replicator create(Args args) {
        ReplicatorConfiguration config;
        Database sourceDB = args.get("sourceDB");
        Database destinationDB = args.get("destinationDB");
        URI targetURI = args.get("targerURI");
        if (targetURI != null){
            config = new ReplicatorConfiguration(sourceDB, targetURI);
        } else if (destinationDB != null) {
            config  = new ReplicatorConfiguration(sourceDB, destinationDB);
        }
        else {
            throw new IllegalArgumentException();
        }
        return new Replicator(config);
    }

    public ReplicatorConfiguration getConfig(Args args){
        Replicator replicator = args.get("replicator");
        return replicator.getConfig();
    }

    public Replicator.Status getStatus(Args args){
        Replicator replicator = args.get("replicator");
        return replicator.getStatus();
    }

    public void addChangeListener(Args args){
        Replicator replicator = args.get("replicator");
        MyReplicatorListener changeListerner = new MyReplicatorListener();
        replicator.addChangeListener(changeListerner);
    }

    public void removeChangeListener(Args args){
        Replicator replicator = args.get("replicator");
        MyReplicatorListener changeListerner = args.get("changeListener");
        replicator.addChangeListener(changeListerner);
    }

    public String toString(Args args){
        Replicator replicator = args.get("replicator");
        return replicator.toString();
    }

    public void networkReachable(Args args){
        Replicator replicator = args.get("replicator");
        replicator.networkReachable();
    }

    public void networkUnreachable(Args args){
        Replicator replicator = args.get("replicator");
        replicator.networkUnreachable();
    }

    public void start(Args args){
        Replicator replicator = args.get("replicator");
        replicator.start();
    }

    public void stop(Args args){
        Replicator replicator = args.get("replicator");
        replicator.stop();
    }
}

class MyReplicatorListener implements ReplicatorChangeListener{
    private List<ReplicatorChange> changes;

    public List<ReplicatorChange> getChanges(){
        return changes;
    }
    @Override
    public void changed(ReplicatorChange change) {
        changes.add(change);
    }
}
