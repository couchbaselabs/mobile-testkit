package com.couchbase.CouchbaseLiteServ.server.RequestHandler;

import java.net.Socket;
import java.net.SocketAddress;
import java.io.IOException;
import java.net.URI;

import com.couchbase.lite.MessageEndpoint;
import com.couchbase.lite.MessageEndpointConnection;
import com.couchbase.lite.MessageEndpointDelegate;

/**
 * Created by sridevi.saragadam on 7/9/18.
 */

public final class ReplicatorTcpClientConnection  {

  public ReplicatorTcpClientConnection(URI url){
    System.out.println("this is constructor");
  }

}
