package com.couchbase.CouchbaseLiteServ.server.RequestHandler;

/**
 * Created by sridevi.saragadam on 7/9/18.
 */
import java.io.IOException;
import java.net.URI;
import java.util.ArrayList;
import java.util.List;
import android.util.Log;

import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.Database;
import com.couchbase.lite.DocumentReplication;
import com.couchbase.lite.DocumentReplicationListener;
import com.couchbase.lite.ListenerToken;
import com.couchbase.lite.MessageEndpoint;
import com.couchbase.lite.MessageEndpointConnection;
import com.couchbase.lite.MessageEndpointDelegate;
import com.couchbase.lite.MessageEndpointListener;
import com.couchbase.lite.MessageEndpointListenerConfiguration;
import com.couchbase.lite.ProtocolType;
import com.couchbase.lite.ReplicatedDocument;
import com.couchbase.lite.Replicator;
import com.couchbase.lite.ReplicatorChange;
import com.couchbase.lite.ReplicatorChangeListener;
import com.couchbase.lite.ReplicatorConfiguration;
import com.couchbase.lite.URLEndpoint;

public class PeerToPeerRequestHandler implements MessageEndpointDelegate{
    ReplicatorRequestHandler obj = new ReplicatorRequestHandler();

    public Replicator configure(Args args) throws Exception {
        String ipaddress = args.get("host");
        int port = args.get("port");
        Database sourceDb = args.get("database");
        String serverDBName = args.get("serverDBName");
        String replicationType = args.get("replicationType");
        Boolean continuous = args.get("continuous");
        String endPointType = args.get("endPointType");
        List<String> documentIds = args.get("documentIDs");
        ReplicatorConfiguration config;
        Replicator replicator;

        if (replicationType == null) {
            replicationType = "push_pull";
        }
        replicationType = replicationType.toLowerCase();
        ReplicatorConfiguration.ReplicatorType replType;
        if (replicationType.equals("push")) {
            replType = ReplicatorConfiguration.ReplicatorType.PUSH;
        } else if (replicationType.equals("pull")) {
            replType = ReplicatorConfiguration.ReplicatorType.PULL;
        } else {
            replType = ReplicatorConfiguration.ReplicatorType.PUSH_AND_PULL;
        }
        Log.i("DB name", "serverDBName is " + serverDBName);
        URI uri = new URI("ws://" + ipaddress + ":" + port + "/" + serverDBName);
        if (endPointType.toLowerCase() == "urlendpoint") {

            URLEndpoint urlEndPoint = new URLEndpoint(uri);
            config = new ReplicatorConfiguration(sourceDb, urlEndPoint);
        } else {
            MessageEndpoint messageEndPoint = new MessageEndpoint("p2p", uri, ProtocolType.BYTE_STREAM, this);
            config = new ReplicatorConfiguration(sourceDb, messageEndPoint);
        }
        config.setReplicatorType(replType);
        if (continuous != null) {
            config.setContinuous(continuous);
        } else {
            config.setContinuous(false);
        }
        if (documentIds != null) {
            config.setDocumentIDs(documentIds);
        }
        replicator = new Replicator(config);
        return replicator;
    }


    public void clientStart(Args args) throws Exception{
        Replicator replicator = args.get("replicator");
        replicator.start();
        Log.i("Replication status", "Replication started .... ");
    }

    class MyReplicatorListener implements ReplicatorChangeListener {
        private List<ReplicatorChange> changes = new ArrayList<>();
        public List<ReplicatorChange> getChanges(){
          return changes;
        }
        @Override
        public void changed(ReplicatorChange change) {
          changes.add(change);
        }
    }

    public MyDocumentReplicatorListener addReplicatorEventChangeListener(Args args){
//        Replicator replicator = args.get("replicator");
//        P2PMyDocumentReplicatorListener changeListener = new P2PMyDocumentReplicatorListener();
//        ListenerToken token = replicator.addDocumentReplicationListener(changeListener);
//        changeListener.setToken(token);
        return obj.addReplicatorEventChangeListener(args);
//        return changeListener;


    }

    public void removeReplicatorEventListener(Args args){
//        Replicator replicator = args.get("replicator");
//        P2PMyDocumentReplicatorListener changeListener = args.get("changeListener");
//        replicator.removeChangeListener(changeListener.getToken());
        obj.removeReplicatorEventListener(args);
    }

    public int changeListenerChangesCount(Args args) {
//        P2PMyDocumentReplicatorListener changeListener = args.get("changeListener");
//        return changeListener.getChanges().size();
        return obj.changeListenerChangesCount(args);
    }

    public List<String> replicatorEventGetChanges(Args args){
//        P2PMyDocumentReplicatorListener changeListener = args.get("changeListener");
////        List<DocumentReplication> changes = changeListener.getChanges();
////        List <String> event_list = new ArrayList<>();
////
////        for (DocumentReplication change: changes) {
////            for (ReplicatedDocument document: change.getDocuments()){
////                String event = document.toString();
////                String doc_id = "doc_id: " + document.getID();
////                String error = ", error_code: ";
////                String error_domain = "0";
////                int error_code = 0;
////
////                if (document.getError() != null){
////                    error_code = document.getError().getCode();
////                    error_domain = document.getError().getDomain();
////                }
////                error = error + error_code + ", error_domain: " + error_domain;
////                String flags = ", flags: " + document.flags().toString();
////                String push = ", push: " + Boolean.toString(change.isPush());
////                event_list.add(doc_id + error + push + flags);
////            }
////        }
////        return event_list;
        return obj.replicatorEventGetChanges(args);
    }

    public ReplicatorTcpListener serverStart(Args args) throws IOException {
        Database sourceDb = args.get("database");
        int port = args.get("port");
        MessageEndpointListener messageEndpointListener = new MessageEndpointListener(new MessageEndpointListenerConfiguration(sourceDb, ProtocolType.BYTE_STREAM));
        ReplicatorTcpListener p2ptcpListener = new ReplicatorTcpListener(sourceDb, port);
        p2ptcpListener.start();
        return p2ptcpListener;
    }

    public void serverStop(Args args){
        ReplicatorTcpListener p2ptcpListener = args.get("replicatorTcpListener");
        p2ptcpListener.stop();
    }

    public MessageEndpointConnection createConnection(MessageEndpoint endpoint){
        URI url = (URI)endpoint.getTarget();
        return new ReplicatorTcpClientConnection(url);
    }
}

//class P2PMyDocumentReplicatorListener implements DocumentReplicationListener{
//    private List<DocumentReplication> changes = new ArrayList<>();
//    private ListenerToken token;
//
//    public List<DocumentReplication> getChanges(){
//        return changes;
//    }
//
//    public void setToken(ListenerToken token){
//        this.token = token;
//    }
//
//    public ListenerToken getToken() {
//        return token;
//    }
//
//    @Override
//    public void replication(DocumentReplication replication) {
//        changes.add(replication);
//    }
//}


