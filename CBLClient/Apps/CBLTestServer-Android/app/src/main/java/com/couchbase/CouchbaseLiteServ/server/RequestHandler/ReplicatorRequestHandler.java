package com.couchbase.CouchbaseLiteServ.server.RequestHandler;

import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.CouchbaseLiteException;
import com.couchbase.lite.DocumentReplication;
import com.couchbase.lite.DocumentReplicationListener;
import com.couchbase.lite.ListenerToken;
import com.couchbase.lite.Replicator;
import com.couchbase.lite.ReplicatorChange;
import com.couchbase.lite.ReplicatorChangeListener;
import com.couchbase.lite.ReplicatorConfiguration;

import java.util.ArrayList;
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

    public ReplicatorChangeListener addChangeListener(Args args){
        Replicator replicator = args.get("replicator");
        MyReplicatorListener changeListener = new MyReplicatorListener();
        replicator.addChangeListener(changeListener);
        return changeListener;
    }

    public void removeChangeListener(Args args){
        Replicator replicator = args.get("replicator");
        MyReplicatorListener changeListener = args.get("changeListener");
        replicator.addChangeListener(changeListener);
    }

    public DocumentReplicationListener addReplicatorEventChangeListener(Args args){
        Replicator replicator = args.get("replicator");
        MyDocumentReplicatorListener changeListener = new MyDocumentReplicatorListener();
        replicator.addDocumentReplicationListener(changeListener);
        return changeListener;
    }

    public void removeReplicatorEventListener(Args args){
        Replicator replicator = args.get("replicator");
        ListenerToken changeListener = args.get("changeListener");
        replicator.removeChangeListener(changeListener);
    }

    public int changeListenerChangesCount(Args args) {
        MyDocumentReplicatorListener changeListener = args.get("changeListener");
        return changeListener.getChanges().size();
    }

    public String replicatorEventGetChanges(Args args){
        MyDocumentReplicatorListener changeListener = args.get("changeListener");
        return changeListener.getChanges().toString();
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

    public Replicator changeGetReplicator(Args args){
        ReplicatorChange change = args.get("change");
        return change.getReplicator();
    }

    public Replicator.Status changeGetStatus(Args args){
        ReplicatorChange change = args.get("change");
        return change.getStatus();
    }

    public int replicatorEventChangesCount(Args args) {
        MyDocumentReplicatorListener changeListener = args.get("changeListener");
        return changeListener.getChanges().size();
    }

    public List<ReplicatorChange> changeListenerGetChanges(Args args) {
        MyReplicatorListener changeListener = args.get("changeListener");
        return changeListener.getChanges();
    }

    public CouchbaseLiteException replicatorGetError(Args args) {
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

    public void resetCheckpoint(Args args) {
        Replicator replicator = args.get("replicator");
        replicator.resetCheckpoint();
    }

}

class MyReplicatorListener implements ReplicatorChangeListener{
    private List<ReplicatorChange> changes = new ArrayList<>();
    public List<ReplicatorChange> getChanges(){
        return changes;
    }
    @Override
    public void changed(ReplicatorChange change) {
        changes.add(change);
    }
}

class MyDocumentReplicatorListener implements DocumentReplicationListener{
    private List<DocumentReplication> changes = new ArrayList<>();

    public List<DocumentReplication> getChanges(){
        return changes;
    }

    @Override
    public void replicated(DocumentReplication update) {
        changes.add(update);
    }
}


