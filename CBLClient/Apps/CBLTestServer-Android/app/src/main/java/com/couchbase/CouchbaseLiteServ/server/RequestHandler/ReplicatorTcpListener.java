package com.couchbase.CouchbaseLiteServ.server.RequestHandler;
//
// ReplicatorTcpListener.java
//
// Copyright (c) 2018 Couchbase, Inc.  All rights reserved.
//
// Licensed under the Couchbase License Agreement (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
// https://info.couchbase.com/rs/302-GJY-034/images/2017-10-30_License_Agreement.pdf
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//

import com.couchbase.lite.Database;
import com.couchbase.lite.MessageEndpointListener;
import com.couchbase.lite.MessageEndpointListenerConfiguration;
import com.couchbase.lite.ProtocolType;

import java.io.IOException;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.SocketException;
import java.util.Collections;
import java.util.List;

// WebSocket based listener
public final class ReplicatorTcpListener {
  private int PORT = 5000;
  private ServerSocket server;
  private MessageEndpointListener endpointListener;
  private Thread loopThread;
  private Database database;

  public ReplicatorTcpListener(Database database, int port) {
    this.database = database;
    MessageEndpointListenerConfiguration config =
        new MessageEndpointListenerConfiguration(database, ProtocolType.BYTE_STREAM);
    this.endpointListener = new MessageEndpointListener(config);
    this.PORT = port;
  }

  public synchronized void start() throws IOException {
    if (server != null)
      return;

    server = new ServerSocket(PORT);
    loopThread = new Thread(new Runnable() {
      @Override
      public void run() {
        acceptLoop();
      }
    });
    loopThread.start();
  }

  public synchronized void stop() {
    if (server == null)
      return;

    try {
      endpointListener.closeAll();
      server.close();
      server = null;
    } catch (IOException e) {
      e.printStackTrace();
    }
  }

  public String getURL() {
    try {
      List<NetworkInterface> interfaces = Collections.list(NetworkInterface.getNetworkInterfaces());
      for (NetworkInterface i : interfaces) {
        List<InetAddress> addresses = Collections.list(i.getInetAddresses());
        for (InetAddress a : addresses) {
          if (!a.isLoopbackAddress() && a instanceof Inet4Address) {
            return "ws://" + a.getHostAddress().toUpperCase() +
                ":" + PORT + "/" + this.database.getName();
          }
        }
      }
    } catch (SocketException e) {
      e.printStackTrace();
    }
    return null;
  }

  private void acceptLoop() {
    while(true) {
      if (server == null)
        break;

      Socket socket = null;
      try {
        socket = server.accept();
        ReplicatorTcpServerConnection connection =
            new ReplicatorTcpServerConnection(socket);
        endpointListener.accept(connection);
      } catch (IOException e) {
        e.printStackTrace();
      }
    }
  }
}