package com.couchbase.CouchbaseLiteServ.server.RequestHandler;
//
// ReplicatorTcpServerConnection.java
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

import java.io.IOException;
import java.net.Socket;
import java.nio.charset.StandardCharsets;


// Websocket based server connection
public final class ReplicatorTcpServerConnection extends ReplicatorTcpConnection {
    protected static final int RECEIVE_BUFFER_SIZE = 8192;

    private final Socket client;

    public ReplicatorTcpServerConnection(Socket client) {
        this.client = client;
    }

    @Override
    boolean openConnection() throws Exception {
        return performWebSocketHandshake();
    }

    private boolean performWebSocketHandshake() throws IOException {
        setSocket(this.client);

        byte[] buffer = new byte[RECEIVE_BUFFER_SIZE];
        inputStream.read(buffer);
        String data = new String(buffer, StandardCharsets.UTF_8);
        if (data.startsWith("GET ")) {
            String key = getHTTPHeader(data, "Sec-WebSocket-Key");
            if (key == null) {
                return false;
            }

            String protocol = getHTTPHeader(data, "Sec-WebSocket-Protocol");
            if (protocol == null) {
                return false;
            }

            String version = getHTTPHeader(data, "Sec-WebSocket-Version");
            if (version == null) {
                return false;
            }

            String accept = getWebSocketAcceptKey(key);
            if (accept == null) {
                return false;
            }

            byte[] response = new StringBuilder()
                .append("HTTP/1.1 101 Switching Protocols").append("\r\n")
                .append("Connection: Upgrade").append("\r\n")
                .append("Upgrade: Websocket").append("\r\n")
                .append("Sec-WebSocket-Version: ").append(version.trim()).append("\r\n")
                .append("Sec-WebSocket-Protocol: ").append(protocol.trim()).append("\r\n")
                .append("Sec-WebSocket-Accept: ").append(accept).append("\r\n")
                .append("\r\n")
                .toString().getBytes(StandardCharsets.UTF_8);
            outputStream.write(response);
            outputStream.flush();
            return true;
        }

        return false;
    }
}