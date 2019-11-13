package com.couchbase.mobiletestkit.javacommon.RequestHandler;
//
// ReplicatorTcpClientConnection.java
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


import com.couchbase.mobiletestkit.javacommon.RequestHandlerDispatcher;

import java.io.IOException;
import java.net.Socket;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.Random;


// Websocket based client connection
public final class ReplicatorTcpClientConnection extends ReplicatorTcpConnection {
    private URI uri;

    public ReplicatorTcpClientConnection(URI uri) {
        super();
        if (uri == null) { throw new IllegalArgumentException("uri cannot be null"); }
        this.uri = uri;
    }

    @Override
    protected boolean openConnection() throws Exception {
        return sendWebSocketRequest();
    }

    private boolean sendWebSocketRequest() throws IOException {
        String host = uri.getHost();
        int port = uri.getPort();
        setSocket(new Socket(host, port));

        if (port != 80) {
            host = host + ":" + port;
        }

        String key = generateWebSocketKey();
        String path = uri.getPath() + "/_blipsync";

        byte[] request = new StringBuilder().append("GET ").append(path).append(" HTTP/1.1").append("\r\n")
            .append("Sec-WebSocket-Version: 13").append("\r\n")
            .append("Sec-WebSocket-Protocol: BLIP_3+CBMobile_2").append("\r\n")
            .append("Sec-WebSocket-Key: ").append(key).append("\r\n")
            .append("Upgrade: websocket").append("\r\n")
            .append("Connection: Upgrade").append("\r\n")
            .append("Host: ").append(host).append("\r\n")
            .append("\r\n")
            .toString().getBytes(StandardCharsets.UTF_8);

        outputStream.write(request);
        outputStream.flush();

        byte[] buffer = new byte[RECEIVE_BUFFER_SIZE];
        inputStream.read(buffer);
        String data = new String(buffer, StandardCharsets.UTF_8);

        if (!data.startsWith("HTTP/1.1 101 ")) {
            return false;
        }

        String connection = getHTTPHeader(data, "Connection");
        if (!"Upgrade".equalsIgnoreCase(connection)) {
            return false;
        }

        String upgrade = getHTTPHeader(data, "Upgrade");
        if (!"Websocket".equalsIgnoreCase(upgrade)) {
            return false;
        }

        String accept = getHTTPHeader(data, "Sec-WebSocket-Accept");
        return getWebSocketAcceptKey(key).equals(accept);
    }

    private String generateWebSocketKey() {
        byte[] keyBytes = new byte[16];
        Random random = new Random();
        random.nextBytes(keyBytes);

        return RequestHandlerDispatcher.context.customEncode(keyBytes);
    }

}