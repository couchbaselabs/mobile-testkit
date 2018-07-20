package com.couchbase.CouchbaseLiteServ.server.RequestHandler;

/**
 * Created by sridevi.saragadam on 7/9/18.
 */

import android.util.Base64;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;
import java.util.regex.Pattern;

import com.couchbase.lite.MessageEndpointConnection;
import com.couchbase.lite.ReplicatorConnection;
import com.couchbase.lite.Message;
import com.couchbase.lite.MessagingCompletion;

import com.couchbase.lite.MessagingError;

public final class Peer2PeerTcpConnection implements MessageEndpointConnection{
  private final int RECEIVE_BUFFER_SIZE = 8192;
  public static final int port = 8085;

  private boolean connected;
  private ReplicatorConnection replicatorConnection;
  private Socket client;
  private InputStream inputStream;
  private OutputStream outputStream;
  private Thread receiveThread;

  public Peer2PeerTcpConnection(Socket client) {
    this.client = client;
    //this.port = port;
  }

  private boolean performWebSocketHandshake() throws IOException {
    byte[] buffer = new byte[RECEIVE_BUFFER_SIZE];
    inputStream.read(buffer);
    String data = new String(buffer, StandardCharsets.UTF_8);
    if(data.matches("^GET")) {
      StringBuilder sb = new StringBuilder();
      final String eol = "\r\n";
      String key = Pattern.compile("Sec-WebSocket-Key: (.*)").matcher(data).group(1);
      if(key == null) {
        return false;
      }

      String protocol = Pattern.compile("Sec-WebSocket-Protocol: (.*)").matcher(data).group(1);
      if(protocol == null) {
        return false;
      }

      String version = Pattern.compile("Sec-WebSocket-Version: (.*)").matcher(data).group(1);
      if(version == null) {
        return false;
      }

      String accept = acceptKey(key);
      if(accept == null) {
        return false;
      }

      byte[] response = sb.append("HTTP/1.1 101 Switching Protocols").append(eol)
          .append("Connection: Upgrade").append(eol)
          .append("Upgrade: websocket").append(eol)
          .append("Sec-WebSocket-Version: ").append(version).append(eol)
          .append("Sec-WebSocket-Protocol: ").append(protocol).append(eol)
          .append("Sec-WebSocket-Accept: ").append(accept).append(eol)
          .append(eol)
          .toString().getBytes(StandardCharsets.UTF_8);
      outputStream.write(response);
      return true;
    }

    return false;
  }

  private String acceptKey(String key) {
    String longKey = key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";
    MessageDigest md;
    try {
      md = MessageDigest.getInstance("SHA-1");
    } catch(NoSuchAlgorithmException e) {
      return null;
    }

    byte[] hashBytes = md.digest(key.getBytes(StandardCharsets.US_ASCII));
    return Base64.encodeToString(hashBytes, 0);
  }

  private void receiveLoop() {
    byte[] buffer = new byte[RECEIVE_BUFFER_SIZE];
    try {
      int length;
      while((length = inputStream.read(buffer)) != 0) {
        replicatorConnection.receive(Message.fromData(Arrays.copyOfRange(buffer, 0, length)));
      }
    } catch(Exception e) {
      // Custom error handling
    }
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
  public void close(Exception error, MessagingCompletion completion) {
    if(!connected) {
      return;
    }

    connected = false;
    try {
      client.close();
      client = null;
      completion.complete(true, null);
    } catch (IOException e) {
      completion.complete(false, new MessagingError(e, false));
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
