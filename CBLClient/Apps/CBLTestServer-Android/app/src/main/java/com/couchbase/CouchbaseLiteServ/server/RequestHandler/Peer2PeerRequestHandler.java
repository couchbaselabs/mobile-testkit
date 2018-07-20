package com.couchbase.CouchbaseLiteServ.server.RequestHandler;

/**
 * Created by sridevi.saragadam on 7/9/18.
 */
import java.net.URI;
import java.net.URISyntaxException;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.BasicAuthenticator;
import com.couchbase.lite.Database;
import com.couchbase.lite.MessageEndpointListener;
import com.couchbase.lite.MessageEndpointListenerConfiguration;
import com.couchbase.lite.ProtocolType;
import com.couchbase.lite.Replicator;
import com.couchbase.lite.ReplicatorChange;
import com.couchbase.lite.ReplicatorChangeListener;
import com.couchbase.lite.ReplicatorConfiguration;
import com.couchbase.lite.URLEndpoint;

public class Peer2PeerRequestHandler {

  public Peer2PeerTcpListener initialize(Args args){
    Peer2PeerTcpListener p2pListener;

    Database database = args.get("database");
    String host = args.get("host");
    int port = args.get("port");
    boolean continuous = args.get("continuous");
    MessageEndpointListenerConfiguration mListenerConfig = new MessageEndpointListenerConfiguration(database, ProtocolType.BYTE_STREAM);
    MessageEndpointListener listener = new MessageEndpointListener(mListenerConfig);
    p2pListener = new Peer2PeerTcpListener(listener);
    return p2pListener;
  }

  public void clientStart(Args args) throws Exception{
    String ipaddress = args.get("host");
    int port = args.get("port");
    // String dbName = args.get("dbName");
    // Database sourceDb = new Database(dbName, null);
    Database sourceDb = args.get("database");
    String serverDBName = args.get("serverDbName");
    Replicator replicator;
    URI uri = new URI("ws://" + ipaddress + ":" + port + "/" + serverDBName);
    BasicAuthenticator authenticator = new BasicAuthenticator("p2pTest", "password");

    URLEndpoint urlEndPoint= new URLEndpoint(uri);
    ReplicatorConfiguration config = new ReplicatorConfiguration(sourceDb, urlEndPoint);
    config.setReplicatorType(ReplicatorConfiguration.ReplicatorType.PUSH_AND_PULL);
    config.setContinuous(true);
    config.setAuthenticator(authenticator);
    replicator = new Replicator(config);
    replicator.start();
    System.out.println("Replication started .... ");
    MyReplicatorListener changeListener = new MyReplicatorListener();
    replicator.addChangeListener(changeListener);
    changeListener.getChanges().size();
    TimeUnit.SECONDS.sleep(180);
    long completed = replicator.getStatus().getProgress().getCompleted();
    long total = replicator.getStatus().getProgress().getCompleted();
    System.out.println("completed and total is "+ completed + " and total is " + total);
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

  public void serverStart(Args args){
    Database sourceDb = args.get("database");
    MessageEndpointListener messageEndpointListener = new MessageEndpointListener(new MessageEndpointListenerConfiguration(sourceDb, ProtocolType.BYTE_STREAM));
    Peer2PeerTcpListener p2ptcpListener = new Peer2PeerTcpListener(messageEndpointListener);
    p2ptcpListener.start();
    System.out.println("server is getting started");
  }

}


