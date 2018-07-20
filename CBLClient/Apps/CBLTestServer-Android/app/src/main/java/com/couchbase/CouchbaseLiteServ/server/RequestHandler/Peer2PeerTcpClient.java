package com.couchbase.CouchbaseLiteServ.server.RequestHandler;

import java.net.Socket;
import java.net.SocketAddress;
import java.io.IOException;

import com.couchbase.lite.MessageEndpoint;
import com.couchbase.lite.MessageEndpointConnection;
import com.couchbase.lite.MessageEndpointDelegate;

/**
 * Created by sridevi.saragadam on 7/9/18.
 */

public final class Peer2PeerTcpClient implements MessageEndpointDelegate  {
  @Override
  public MessageEndpointConnection createConnection(MessageEndpoint endpoint) {
    Socket socket = new Socket();
    try {
      socket.connect((SocketAddress) endpoint.getTarget());
    }
    catch(IOException ex){
      System.out.println("Exception while connecting to server by client " + ex.getMessage());
    }
    Peer2PeerTcpConnection server = new Peer2PeerTcpConnection(socket);
    return server;
  }

  public void start(){

  }
}
