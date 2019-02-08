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
import com.couchbase.lite.MessageEndpoint;
import com.couchbase.lite.MessageEndpointConnection;
import com.couchbase.lite.MessageEndpointDelegate;
import com.couchbase.lite.MessageEndpointListener;
import com.couchbase.lite.MessageEndpointListenerConfiguration;
import com.couchbase.lite.ProtocolType;
import com.couchbase.lite.Replicator;
import com.couchbase.lite.ReplicatorChange;
import com.couchbase.lite.ReplicatorChangeListener;
import com.couchbase.lite.ReplicatorConfiguration;
import com.couchbase.lite.URLEndpoint;

public class PeerToPeerRequestHandler implements MessageEndpointDelegate{

    ReplicatorRequestHandler replicatorRequestHandlerObj = new ReplicatorRequestHandler();

    public void clientStart(Args args) throws Exception{
        Replicator replicator = args.get("replicator");
        replicator.start();
        Log.i("Replication status", "Replication started .... ");
    }

    public Replicator configure(Args args) throws Exception{
        String ipaddress = args.get("host");
        int port = args.get("port");
        Database sourceDb = args.get("database");
        String serverDBName = args.get("serverDBName");
        String replicationType = args.get("replicationType");
        Boolean continuous = args.get("continuous");
        String endPointType = args.get("endPointType");
        List<String> documentIds = args.get("documentIDs");
        Boolean push_filter = args.get("push_filter");
        Boolean pull_filter = args.get("pull_filter");
        String filter_callback_func = args.get("filter_callback_func");
        ReplicatorConfiguration config;
        Replicator replicator;

        if (replicationType == null)
        {
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
        Log.i("DB name", "serverDBName is "+ serverDBName);
        URI uri = new URI("ws://" + ipaddress + ":"+port+"/" + serverDBName);
        if (endPointType.equals("URLEndPoint")){
            URLEndpoint urlEndPoint= new URLEndpoint(uri);
            config = new ReplicatorConfiguration(sourceDb, urlEndPoint);
        }
        else if (endPointType.equals("MessageEndPoint")){
            MessageEndpoint messageEndPoint = new MessageEndpoint("p2p", uri, ProtocolType.BYTE_STREAM, this);
            config = new ReplicatorConfiguration(sourceDb, messageEndPoint);
        } else {
            throw new IllegalArgumentException("Incorrect EndPoint type");
        }
        config.setReplicatorType(replType);
        if (continuous != null) {
            config.setContinuous(continuous);
        }
        else {
            config.setContinuous(false);
        }
        if (documentIds != null) {
            config.setDocumentIDs(documentIds);
        }if (push_filter){
            if (filter_callback_func.equals("boolean")){
                config.setPushFilter(new ReplicatorBooleanFiltlerCallback());
            } else if (filter_callback_func.equals("deleted")){
                config.setPushFilter(new ReplicatorDeletedFilterCallback());
            } else if (filter_callback_func.equals("access_revoked")){
                config.setPushFilter(new ReplicatorAccessRevokedFilterCallback());
            } else {
                config.setPushFilter(new DefaultReplicatorFilterCallback());
            }
        }
        if (pull_filter){
            if (filter_callback_func.equals("boolean")){
                config.setPullFilter(new ReplicatorBooleanFiltlerCallback());
            } else if (filter_callback_func.equals("deleted")){
                config.setPullFilter(new ReplicatorDeletedFilterCallback());
            } else if (filter_callback_func.equals("access_revoked")){
                config.setPullFilter(new ReplicatorAccessRevokedFilterCallback());
            } else {
                config.setPullFilter(new DefaultReplicatorFilterCallback());
            }
        }

        replicator = new Replicator(config);
        return replicator;
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

    public ReplicatorTcpListener serverStart(Args args) throws IOException{
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
public MyDocumentReplicatorListener addReplicatorEventChangeListener(Args args){
        return replicatorRequestHandlerObj.addReplicatorEventChangeListener(args);
    }

    public void removeReplicatorEventListener(Args args) {
        replicatorRequestHandlerObj.removeReplicatorEventListener(args);
    }

    public int changeListenerChangesCount(Args args) {
        return replicatorRequestHandlerObj.changeListenerChangesCount(args);
    }

    public List<String> replicatorEventGetChanges(Args args){
        return replicatorRequestHandlerObj.replicatorEventGetChanges(args);
    }
}
