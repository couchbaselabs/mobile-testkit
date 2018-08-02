package com.couchbase.CouchbaseLiteServ.server.RequestHandler;

/**
 * Created by sridevi.saragadam on 7/9/18.
 */
import java.io.IOException;
import java.net.URI;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

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

public class PeerToPeerRequestHandler{


  public Replicator clientStart(Args args) throws Exception{
    String ipaddress = args.get("host");
    // String dbName = args.get("dbName");
    // Database sourceDb = new Database(dbName, null);
    Database sourceDb = args.get("database");
    String serverDBName = args.get("serverDBName");
    String replicationType = args.get("replicationType");
    Boolean continuous = args.get("continuous");
    String endPointType = "URLEndPoint";
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
    System.out.println("serverDBName is "+ serverDBName);
    URI uri = new URI("ws://" + ipaddress + ":5000/" + serverDBName);
    URLEndpoint urlEndPoint= new URLEndpoint(uri);
    config = new ReplicatorConfiguration(sourceDb, urlEndPoint);
    /* if (endPointType.toLowerCase() == "URLEndPoint"){

      URLEndpoint urlEndPoint= new URLEndpoint(uri);
      config = new ReplicatorConfiguration(sourceDb, urlEndPoint);
    }
    else{
      //MessageEndpoint messageEndPoint = new MessageEndpoint("p2p", uri, ProtocolType.BYTE_STREAM, this);
      // config = new ReplicatorConfiguration(sourceDb, messageEndPoint);
    }*/
    config.setReplicatorType(replType);
    if (continuous != null) {
      config.setContinuous(continuous);
    }
    else {
      config.setContinuous(false);
    }


    replicator = new Replicator(config);
    replicator.start();
    System.out.println("Replication started .... ");
    /*MyReplicatorListener changeListener = new MyReplicatorListener();
    replicator.addChangeListener(changeListener);
    changeListener.getChanges().size();
    TimeUnit.SECONDS.sleep(180);
    long completed = replicator.getStatus().getProgress().getCompleted();
    long total = replicator.getStatus().getProgress().getCompleted();
    System.out.println("completed and total is "+ completed + " and total is " + total);*/
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
    // MessageEndpointListener messageEndpointListener = new MessageEndpointListener(new MessageEndpointListenerConfiguration(sourceDb, ProtocolType.BYTE_STREAM));
    ReplicatorTcpListener p2ptcpListener = new ReplicatorTcpListener(sourceDb);
    p2ptcpListener.start();
    return p2ptcpListener;
  }

  public void serverStop(Args args){
    ReplicatorTcpListener p2ptcpListener = args.get("replicatorTcpListener");
    p2ptcpListener.stop();
  }
 /*
  public MessageEndpointConnection createConnection(MessageEndpoint endpoint){
    URI url = (URI)endpoint.getTarget();
    // return new ReplicatorTcpClientConnection(url);
    return new MessageEndpointConnection(url);
  }
*/
}


