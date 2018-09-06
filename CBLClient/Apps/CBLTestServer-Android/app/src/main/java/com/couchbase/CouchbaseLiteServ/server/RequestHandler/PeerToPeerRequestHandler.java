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


  public Replicator clientStart(Args args) throws Exception{
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
    if (endPointType.toLowerCase() == "urlendpoint"){

      URLEndpoint urlEndPoint= new URLEndpoint(uri);
      config = new ReplicatorConfiguration(sourceDb, urlEndPoint);
    }
    else{
      MessageEndpoint messageEndPoint = new MessageEndpoint("p2p", uri, ProtocolType.BYTE_STREAM, this);
      config = new ReplicatorConfiguration(sourceDb, messageEndPoint);
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
    }

    replicator = new Replicator(config);
    replicator.start();
    Log.i("Replication status", "Replication started .... ");
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

}


