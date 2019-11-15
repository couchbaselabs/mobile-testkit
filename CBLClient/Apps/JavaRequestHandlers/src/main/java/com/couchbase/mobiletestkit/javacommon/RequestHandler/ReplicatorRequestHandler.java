package com.couchbase.mobiletestkit.javacommon.RequestHandler;

import java.util.ArrayList;
import java.util.List;

import com.couchbase.mobiletestkit.javacommon.Args;
import com.couchbase.lite.CouchbaseLiteException;
import com.couchbase.lite.DocumentReplication;
import com.couchbase.lite.DocumentReplicationListener;
import com.couchbase.lite.ListenerToken;
import com.couchbase.lite.ReplicatedDocument;
import com.couchbase.lite.Replicator;
import com.couchbase.lite.ReplicatorChange;
import com.couchbase.lite.ReplicatorChangeListener;
import com.couchbase.lite.ReplicatorConfiguration;


public class ReplicatorRequestHandler {
    /* -------------- */
    /* - Replicator - */
    /* -------------- */

    public Replicator create(Args args) {
        ReplicatorConfiguration config = args.get("config");
        return new Replicator(config);
    }

    public ReplicatorConfiguration getConfig(Args args) {
        Replicator replicator = args.get("replicator");
        return replicator.getConfig();
    }

    public String status(Args args) {
        Replicator replicator = args.get("replicator");
        return replicator.getStatus().toString();
    }

    public String getActivityLevel(Args args) {
        Replicator replicator = args.get("replicator");
        return replicator.getStatus().getActivityLevel().toString().toLowerCase();
    }

    public ReplicatorChangeListener addChangeListener(Args args) {
        Replicator replicator = args.get("replicator");
        MyReplicatorListener changeListener = new MyReplicatorListener();
        replicator.addChangeListener(changeListener);
        return changeListener;
    }

    public void removeChangeListener(Args args) {
        Replicator replicator = args.get("replicator");
        MyReplicatorListener changeListener = args.get("changeListener");
        replicator.addChangeListener(changeListener);
    }

    public MyDocumentReplicatorListener addReplicatorEventChangeListener(Args args) {
        Replicator replicator = args.get("replicator");
        MyDocumentReplicatorListener changeListener = new MyDocumentReplicatorListener();
        ListenerToken token = replicator.addDocumentReplicationListener(changeListener);
        changeListener.setToken(token);
        return changeListener;
    }

    public void removeReplicatorEventListener(Args args) {
        Replicator replicator = args.get("replicator");
        MyDocumentReplicatorListener changeListener = args.get("changeListener");
        replicator.removeChangeListener(changeListener.getToken());
    }

    public int changeListenerChangesCount(Args args) {
        MyReplicatorListener changeListener = args.get("changeListener");
        return changeListener.getChanges().size();
    }

    public List<String> replicatorEventGetChanges(Args args) {
        MyDocumentReplicatorListener changeListener = args.get("changeListener");
        List<DocumentReplication> changes = changeListener.getChanges();
        List<String> event_list = new ArrayList<>();

        for (DocumentReplication change : changes) {
            for (ReplicatedDocument document : change.getDocuments()) {
                String event = document.toString();
                String doc_id = "doc_id: " + document.getID();
                String error = ", error_code: ";
                String error_domain = "0";
                int error_code = 0;

                if (document.getError() != null) {
                    error_code = document.getError().getCode();
                    error_domain = document.getError().getDomain();
                }
                error = error + error_code + ", error_domain: " + error_domain;
                String flags = ", flags: " + document.flags();
                String push = ", push: " + change.isPush();
                event_list.add(doc_id + error + push + flags);
            }
        }
        return event_list;
    }

    public String toString(Args args) {
        Replicator replicator = args.get("replicator");
        return replicator.toString();
    }

    public void start(Args args) {
        Replicator replicator = args.get("replicator");
        replicator.start();
    }

    public void stop(Args args) {
        Replicator replicator = args.get("replicator");
        replicator.stop();
    }

    public Replicator changeGetReplicator(Args args) {
        ReplicatorChange change = args.get("change");
        return change.getReplicator();
    }

    public Replicator.Status changeGetStatus(Args args) {
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

    public Boolean isContinuous(Args args) {
        ReplicatorConfiguration config = args.get("config");
        return config.isContinuous();
    }

    public void resetCheckpoint(Args args) {
        Replicator replicator = args.get("replicator");
        replicator.resetCheckpoint();
    }

}

class MyReplicatorListener implements ReplicatorChangeListener {
    private final List<ReplicatorChange> changes = new ArrayList<>();

    public List<ReplicatorChange> getChanges() {
        return changes;
    }

    @Override
    public void changed(ReplicatorChange change) {
        changes.add(change);
    }
}

class MyDocumentReplicatorListener implements DocumentReplicationListener {
    private final List<DocumentReplication> changes = new ArrayList<>();
    private ListenerToken token;

    public List<DocumentReplication> getChanges() {
        return changes;
    }

    public void setToken(ListenerToken token) {
        this.token = token;
    }

    public ListenerToken getToken() {
        return token;
    }

    @Override
    public void replication(DocumentReplication replication) {
        changes.add(replication);
    }
}


