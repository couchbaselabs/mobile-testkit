package com.couchbase.CouchbaseLiteServ.server.RequestHandler;

/**
 * Created by sridevi.saragadam on 6/6/18.
 */
// A Java program for a Server
import com.couchbase.CouchbaseLiteServ.server.Args;

import java.net.*;
import java.io.*;

import com.couchbase.lite.MessageEndpointDelegate;
import com.couchbase.lite.MessageEndpoint;
import com.couchbase.lite.MessageEndpointConnection;


public class Peer2PeerRequestHandler{

  //initialize socket and input stream
  // private Socket          socket   = null;
  // private ServerSocket    server   = null;
  // private DataInputStream in       =  null;

  // constructor with port
  public ServerSocket socketConnection(Args args)
  {
    ServerSocket    server   = null;
    int port = args.get("port");
    // int port = 5000;
    // starts server and waits for a connection
    System.out.println("Server started with some port "+port);
    try {
      server = new ServerSocket(port);
      System.out.println("Server started");
    }catch(IOException i)
      {
        System.out.println(i);
      }
      return server;
    }
    /*try
    {
      server = new ServerSocket(port);
      System.out.println("Server started");

      System.out.println("Waiting for a client ...");

      socket = server.accept();
      System.out.println("Client accepted");

      // takes input from the client socket
      in = new DataInputStream(
          new BufferedInputStream(socket.getInputStream()));

      String line = "";

      // reads message from client until "Over" is sent
      while (!line.equals("Over"))
      {
        try
        {
          line = in.readUTF();
          System.out.println(line);

        }
        catch(IOException i)
        {
          System.out.println(i);
        }
      }
      System.out.println("Closing connection");

      // close connection
      socket.close();
      in.close();
    }
    catch(IOException i)
    {
      System.out.println(i);
    }
  }
  /*
  public void serverConnection(){
    socketConnection(5000);
  } */

  public Socket acceptClient(Args args){
    Socket          socket   = null;
    ServerSocket server = args.get("server");
    System.out.println("Waiting for a client ...");
    try {
      socket = server.accept();
      System.out.println("Client accepted");
    }
    catch(IOException i)
    {
      System.out.println(i);
    }
    return socket;
  }

  @Override
  public MessageEndpointConnection createConnection(MessageEndpoint endpoint) {
    MockServerConnection server = (MockServerConnection) endpoint.getTarget();
    return new MockClientConnection(server);
  }

  public void readDataFromClient(Args args){
    DataInputStream in       =  null;
    Socket socket = args.get("socket");
    // takes input from the client socket
    try {
    in = new DataInputStream(new BufferedInputStream(socket.getInputStream()));
    }
    catch(IOException i)
    {
      System.out.println("Exception in Data input stream "+i);
    }
    String line = "";

    // reads message from client until "Over" is sent
    while (!line.equals("Over"))
    {
      try
      {
        line = in.readUTF();
        System.out.println(line);

      }
      catch(IOException i)
      {
        System.out.println(i);
      }
    }
  }

}

public class PeerToPeerImplementation implements MessageEndpointDelegate{
  
}