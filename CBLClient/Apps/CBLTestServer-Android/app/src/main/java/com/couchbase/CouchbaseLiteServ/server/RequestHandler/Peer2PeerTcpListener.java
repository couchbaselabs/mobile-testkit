package com.couchbase.CouchbaseLiteServ.server.RequestHandler;

/**
 * Created by sridevi.saragadam on 7/9/18.
 */

import java.io.IOException;
import java.net.ServerSocket;
import java.net.Socket;

import com.couchbase.lite.MessageEndpoint;
import com.couchbase.lite.MessageEndpointListener;
import com.couchbase.lite.ProtocolType;

public final class Peer2PeerTcpListener {
  private Socket connectedTcpClient;
  private ServerSocket listener;
  private MessageEndpointListener endpointListener;
  private boolean opened;
  private Thread loopThread;

  public Peer2PeerTcpListener(MessageEndpointListener endpointListener){
    this.endpointListener = endpointListener;
    // this.connectedTcpClient = new Socket(ipAddress, port);
  }

  public void start() {
    if(listener == null) {
      try {
        listener = new ServerSocket(Peer2PeerTcpConnection.port);
        opened = true;
        loopThread = new Thread(new Runnable() {
          @Override
          public void run() {
            acceptLoop();
          }
        });
      } catch(Exception e) {
        // Placeholder for customized logging or error handling
      }
    }
  }

  private void acceptLoop() {
    while(opened) {
      try {
        connectedTcpClient = listener.accept();
        Peer2PeerTcpConnection socketConnection = new Peer2PeerTcpConnection(connectedTcpClient);
        endpointListener.accept(socketConnection);
      } catch (IOException e) {
        // Placeholder for customized logging or error handling
      }

    }
  }
  /*
  public MessageEndpoint getMessageEndPoint(Object uri){
    MessageEndpoint endPoint = new MessageEndpoint("UID:123", uri, ProtocolType.BYTE_STREAM, this);
    return endPoint;
  }*/


}

