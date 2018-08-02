//
// ReplicatorTcpConnection.java
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

package com.couchbase.CouchbaseLiteServ.server.RequestHandler;

import android.util.Base64;

import com.couchbase.lite.Message;
import com.couchbase.lite.MessageEndpointConnection;
import com.couchbase.lite.MessagingCloseCompletion;
import com.couchbase.lite.MessagingCompletion;
import com.couchbase.lite.MessagingError;
import com.couchbase.lite.ReplicatorConnection;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class ReplicatorTcpServerConnection implements MessageEndpointConnection {
  private final int RECEIVE_BUFFER_SIZE = 8192;

  private boolean connected;
  private ReplicatorConnection replicatorConnection;
  private Socket client;
  private InputStream inputStream;
  private OutputStream outputStream;
  private Thread receiveThread;

  public ReplicatorTcpServerConnection(Socket client) {
    this.client = client;
  }

  private boolean performWebSocketHandshake() throws IOException {
    byte[] buffer = new byte[RECEIVE_BUFFER_SIZE];
    inputStream.read(buffer);
    String data = new String(buffer, StandardCharsets.UTF_8);
    if(data.startsWith("GET ")) {
      String key = getHeader(data, "Sec-WebSocket-Key");
      if(key == null) {
        return false;
      }

      String protocol = getHeader(data, "Sec-WebSocket-Protocol");
      if(protocol == null) {
        return false;
      }

      String version = getHeader(data, "Sec-WebSocket-Version");
      if(version == null) {
        return false;
      }

      String accept = acceptKey(key);
      if(accept == null) {
        return false;
      }

      final String eol = "\r\n";
      StringBuilder sb = new StringBuilder();
      byte[] response = sb.append("HTTP/1.1 101 Switching Protocols").append(eol)
          .append("Connection: Upgrade").append(eol)
          .append("Upgrade: websocket").append(eol)
          .append("Sec-WebSocket-Version: ").append(version.trim()).append(eol)
          .append("Sec-WebSocket-Protocol: ").append(protocol.trim()).append(eol)
          .append("Sec-WebSocket-Accept: ").append(accept).append(eol)
          .append(eol)
          .toString().getBytes(StandardCharsets.UTF_8);
      outputStream.write(response);
      return true;
    }

    return false;
  }

  private String getHeader(String httpRequest, String key) {
    Matcher m = Pattern.compile(key + ": (.*)").matcher(httpRequest);
    if (m.find())
      return m.group(1);
    else
      return null;
  }

  private String acceptKey(String key) {
    String longKey = key.trim() + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";
    MessageDigest md;
    try {
      md = MessageDigest.getInstance("SHA-1");
    } catch(NoSuchAlgorithmException e) {
      return null;
    }

    byte[] hashBytes = md.digest(longKey.getBytes(StandardCharsets.US_ASCII));
    return Base64.encodeToString(hashBytes, Base64.NO_WRAP);
  }

  private void receiveLoop() {
    Exception error = null;
    byte[] buffer = new byte[RECEIVE_BUFFER_SIZE];
    try {
      int length;
      while((length = inputStream.read(buffer)) != 0) {
        replicatorConnection.receive(Message.fromData(Arrays.copyOfRange(buffer, 0, length)));
      }
    } catch(Exception e) {
      if (!(e instanceof InterruptedException)) {
        error = e;
      }
    }
    replicatorConnection.close(error != null ? new MessagingError(error, false) : null);
  }

  @Override
  public void open(ReplicatorConnection connection, MessagingCompletion completion) {
    if(connected) {
      return;
    }

    try {
      inputStream = client.getInputStream();
      outputStream = client.getOutputStream();
      if(!performWebSocketHandshake()) {
        completion.complete(false,
            new MessagingError(new RuntimeException("Failed websocket handshake"), false));
      }
    } catch (IOException e) {
      completion.complete(false, new MessagingError(e, false));
      return;
    }

    connected = true;
    replicatorConnection = connection;
    receiveThread = new Thread(new Runnable() {
      @Override
      public void run() {
        receiveLoop();
      }
    });
    receiveThread.start();
  }

  @Override
  public void close(Exception error, MessagingCloseCompletion completion) {
    if(!connected) {
      return;
    }
    connected = false;
    try {
      client.close();
      client = null;
    } catch (IOException e) {
      e.printStackTrace();
    } finally {
      completion.complete();
      receiveThread.interrupt();
    }
  }

  @Override
  public void send(Message message, MessagingCompletion completion) {
    byte[] bytes = message.toData();
    try {
      outputStream.write(bytes);
      completion.complete(true, null);
    } catch(IOException e) {
      completion.complete(false, new MessagingError(e, false));
    }
  }
}