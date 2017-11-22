package com.couchbase.CouchbaseLiteServ.server;

import org.nanohttpd.protocols.http.IHTTPSession;
import org.nanohttpd.protocols.http.NanoHTTPD;
import org.nanohttpd.protocols.http.response.IStatus;
import org.nanohttpd.protocols.http.response.Response;
import org.nanohttpd.protocols.http.response.Status;

import java.io.IOException;
import java.io.UnsupportedEncodingException;
import java.lang.reflect.Method;
import java.net.URLDecoder;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class Server extends NanoHTTPD {

    private static final String TAG = "com.example.hemant.coucbaselitesampleapp.serve";
    public String uri;

    public Method method;

    public Map<String, String> header;

    public Map<String, String> parms;

    public Map<String, List<String>> parameters;

    public Map<String, String> files;

    public Map<String, List<String>> decodedParamters;

    public Map<String, List<String>> decodedParamtersFromParameter;

    public String queryParameterString;

    private Memory memory = new Memory();

    public Server(int port) throws IOException {
        super(port);
        System.out.print("Running! Point your Mobile browser to http://localhost:" + port + "/\n");
    }

    @Override
    public Response handle(IHTTPSession session) {
        String path = session.getUri();
        String method = (path.startsWith("/") ? path.substring(1) : path);
        // Get args from query string.
        Map<String, String> rawArgs = new HashMap<>();
        Args args = new Args();
        String query = session.getQueryParameterString();
        if (query != null) {
            for (String param : query.split("&")) {
                String pair[] = param.split("=", 2);
                String name = null;
                try {
                    name = URLDecoder.decode(pair[0], "UTF8");
                } catch (UnsupportedEncodingException e) {
                    e.printStackTrace();
                }
                String value = null;
                try {
                    value = URLDecoder.decode(pair.length > 1 ? pair[1] : null, "UTF8");
                } catch (UnsupportedEncodingException e) {
                    e.printStackTrace();
                }

                if (value != null) {
                    rawArgs.put(name, value);
                }

                args.put(name, ValueSerializer.deserialize(value, memory));
            }
        }

        String handlerType = method.split("_")[0];
        try {
            // Find and invoke the method on the RequestHandler.
            String body = null;
            if ("release".equals(method)) {
                memory.remove(rawArgs.get("object"));
            } else {
                Object requestHandler = null;
                Method target;
                if (handlerType.equals("database")){
                    target = DatabaseRequestHandler.class.getMethod(method, Args.class);
                    requestHandler = new DatabaseRequestHandler();
                } else if (handlerType.equals("document")){
                    target = DocumentRequestHandler.class.getMethod(method, Args.class);
                    requestHandler = new DocumentRequestHandler();
                } else if (handlerType.equals("dictionary")){
                    target = DictionaryRequestHandler.class.getMethod(method, Args.class);
                    requestHandler = new DictionaryRequestHandler();
                } else {
                    throw new IllegalArgumentException("Handler not implemented for this call");
                }
                if (target.getReturnType().equals(Void.TYPE)) {
                    target.invoke(requestHandler, args);
                } else {
                    Object result = target.invoke(requestHandler, args);
                    body = ValueSerializer.serialize(result, memory);
                }
            }
            session.getHeaders();
            if (body != null) {
                IStatus status = Status.OK;
                return Response.newFixedLengthResponse(status, "text/plain", body.getBytes());
            } else {
                return Response.newFixedLengthResponse(Status.OK, "text/plain", "-1");
            }
        } catch (Exception e) {
            // TODO: How should we handle exceptions?
            e.printStackTrace(System.out);
             return Response.newFixedLengthResponse(Status.BAD_REQUEST, "text/plain", "0");
        }
    }
}