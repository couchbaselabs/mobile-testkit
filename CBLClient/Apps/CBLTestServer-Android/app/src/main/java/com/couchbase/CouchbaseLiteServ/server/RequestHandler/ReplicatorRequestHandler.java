package com.couchbase.CouchbaseLiteServ.server.RequestHandler;

import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.CouchbaseLiteException;
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

    public String status(Args args){
        Replicator replicator = args.get("replicator");
        return replicator.getStatus().toString();
    }

    public String getActivityLevel(Args args) {
        Replicator replicator = args.get("replicator");
        return replicator.getStatus().getActivityLevel().toString().toLowerCase();
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

    public CouchbaseLiteException replicator_getError(Args args) {
        Replicator replicator = args.get("replicator");
        return replicator.getStatus().getError();
    }

    public ReplicatorConfiguration config(Args args) {
        Replicator replicator = args.get("replicator");
        return replicator.getConfig();
    }

    public long getCompleted(Args args) {
        Replicator replicator = args.get("replicator");
        return replicator.getStatus().getProgress().getCompleted();
    }

    public long getTotal(Args args) {
        Replicator replicator = args.get("replicator");
        return replicator.getStatus().getProgress().getTotal();
    }

    public String getError(Args args) {
        Replicator replicator = args.get("replicator");
        CouchbaseLiteException error = replicator.getStatus().getError();
        if (error != null) {
            return error.toString();
        }
        return null;
    }

    public Boolean isContinous(Args args) {
        ReplicatorConfiguration config = args.get("config");
        return config.isContinuous();
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
