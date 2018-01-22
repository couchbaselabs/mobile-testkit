package com.couchbase.CouchbaseLiteServ.server.RequestHandler;

import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.Replicator;
import com.couchbase.lite.ReplicatorChange;
import com.couchbase.lite.ReplicatorChangeListener;
import com.couchbase.lite.ReplicatorConfiguration;

import java.util.List;

public class ReplicatorRequestHandler {
    /* -------------- */
    /* - Replicator - */
    /* -------------- */

    public Replicator create(Args args) {
        ReplicatorConfiguration config = args.get("config");
        return new Replicator(config);
    }

    public ReplicatorConfiguration getConfig(Args args){
        Replicator replicator = args.get("replicator");
        return replicator.getConfig();
    }

    public Replicator.ActivityLevel getStatus(Args args){
        Replicator replicator = args.get("replicator");
        return replicator.getStatus().getActivityLevel();
    }

    public void addChangeListener(Args args){
        Replicator replicator = args.get("replicator");
        MyReplicatorListener changeListener = new MyReplicatorListener();
        replicator.addChangeListener(changeListener);
    }

    public void removeChangeListener(Args args){
        Replicator replicator = args.get("replicator");
        MyReplicatorListener changeListener = args.get("changeListener");
        replicator.addChangeListener(changeListener);
    }

    public String toString(Args args){
        Replicator replicator = args.get("replicator");
        return replicator.toString();
    }

    public void start(Args args){
        Replicator replicator = args.get("replicator");
        replicator.start();
    }

    public void stop(Args args){
        Replicator replicator = args.get("replicator");
        replicator.stop();
    }

    public Replicator replicatorChangeGetReplicator(Args args){
        ReplicatorChange change = args.get("change");
        return change.getReplicator();
    }

    public Replicator.Status replicatorChangeGetStatus(Args args){
        ReplicatorChange change = args.get("change");
        return change.getStatus();
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
