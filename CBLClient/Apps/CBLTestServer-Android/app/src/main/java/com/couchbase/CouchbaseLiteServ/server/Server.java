package com.couchbase.CouchbaseLiteServ.server;


import android.content.Context;

import com.couchbase.CouchbaseLiteServ.MainActivity;
import com.couchbase.CouchbaseLiteServ.server.RequestHandler.ArrayRequestHandler;
import com.couchbase.CouchbaseLiteServ.server.RequestHandler.BasicAuthenticatorRequestHandler;
import com.couchbase.CouchbaseLiteServ.server.RequestHandler.CollatorRequestHandler;
import com.couchbase.CouchbaseLiteServ.server.RequestHandler.DataSourceRequestHandler;
import com.couchbase.CouchbaseLiteServ.server.RequestHandler.DataTypesInitiatorHandler;
import com.couchbase.CouchbaseLiteServ.server.RequestHandler.DatabaseConfigurationRequestHandler;
import com.couchbase.CouchbaseLiteServ.server.RequestHandler.DatabaseRequestHandler;
import com.couchbase.CouchbaseLiteServ.server.RequestHandler.DictionaryRequestHandler;
import com.couchbase.CouchbaseLiteServ.server.RequestHandler.DocumentRequestHandler;
import com.couchbase.CouchbaseLiteServ.server.RequestHandler.ExpressionRequestHandler;
import com.couchbase.CouchbaseLiteServ.server.RequestHandler.FunctionRequestHandler;
import com.couchbase.CouchbaseLiteServ.server.RequestHandler.PredictiveQueriesRequestHandler;
import com.couchbase.CouchbaseLiteServ.server.RequestHandler.LoggingRequestHandler;
import com.couchbase.CouchbaseLiteServ.server.RequestHandler.QueryRequestHandler;
import com.couchbase.CouchbaseLiteServ.server.RequestHandler.ReplicatorConfigurationRequestHandler;
import com.couchbase.CouchbaseLiteServ.server.RequestHandler.ReplicatorRequestHandler;
import com.couchbase.CouchbaseLiteServ.server.RequestHandler.ResultRequestHandler;
import com.couchbase.CouchbaseLiteServ.server.RequestHandler.SelectResultRequestHandler;
import com.couchbase.CouchbaseLiteServ.server.RequestHandler.SessionAuthenticatorRequestHandler;
import com.couchbase.CouchbaseLiteServ.server.RequestHandler.PeerToPeerRequestHandler;
import com.couchbase.lite.Database;

import com.couchbase.lite.LogDomain;
import com.couchbase.lite.LogLevel;
import com.google.gson.Gson;

import org.nanohttpd.protocols.http.IHTTPSession;
import org.nanohttpd.protocols.http.NanoHTTPD;
import org.nanohttpd.protocols.http.response.IStatus;
import org.nanohttpd.protocols.http.response.Response;
import org.nanohttpd.protocols.http.response.Status;

import java.io.IOException;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.lang.reflect.Method;
import java.util.EnumSet;
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

    public static final Memory memory = new Memory();

    public Server(String ip, int port) throws IOException {
        super(port);
        System.out.print("Running! Point your Mobile browser to http://" + ip + ":" + port + "/\n");
    }

    @Override
    public Response handle(IHTTPSession session) {
        String path = session.getUri();
        String method = (path.startsWith("/") ? path.substring(1) : path);
        Database.log.getConsole().setLevel(LogLevel.DEBUG);
        Database.log.getConsole().setDomains(EnumSet.of(LogDomain.ALL));
        // Get args from query string.
        Map<String, String> rawArgs = new HashMap<>();

        Args args = new Args();
        try {
            session.parseBody(rawArgs);
        } catch (IOException e) {
            e.printStackTrace();
        } catch (ResponseException e) {
            e.printStackTrace();
        }
        Map<String, Object> query = new Gson().fromJson(rawArgs.get("postData"), Map.class);
        if (query !=null){
            for (String key : query.keySet()){
                String value = (String) query.get(key);
                args.put(key, ValueSerializer.deserialize(value, memory));
            }
        }

        try {
            // Find and invoke the method on the RequestHandler.
            String body = null;
            Object result;
            if ("release".equals(method)) {
                memory.remove(rawArgs.get("object"));
            } else if ("flushMemory".equals(method)){
                memory.flushMemory();
            } else if ("copy_files".equals(method)){
                result = memory.copyFiles(args);
                body = ValueSerializer.serialize(result, memory);
            } else {
                Object requestHandler = null;
                String handlerType = method.split("_")[0];
                String method_to_call = method.split("_")[1];
                Method target;
                switch (handlerType){

                    case "databaseConfiguration":
                        target = DatabaseConfigurationRequestHandler.class.getMethod(method_to_call, Args.class);
                        requestHandler = new DatabaseConfigurationRequestHandler();
                        break;
                    case "database":
                        target = DatabaseRequestHandler.class.getMethod(method_to_call, Args.class);
                        requestHandler = new DatabaseRequestHandler();
                        break;
                    case "document":
                        target = DocumentRequestHandler.class.getMethod(method_to_call, Args.class);
                        requestHandler = new DocumentRequestHandler();
                        break;
                    case "dictionary":
                        target = DictionaryRequestHandler.class.getMethod(method_to_call, Args.class);
                        requestHandler = new DictionaryRequestHandler();
                        break;
                    case "datatype":
                        target = DataTypesInitiatorHandler.class.getMethod(method_to_call, Args.class);
                        requestHandler = new DataTypesInitiatorHandler();
                        break;
                    case "replicator":
                        target = ReplicatorRequestHandler.class.getMethod(method_to_call, Args.class);
                        requestHandler = new ReplicatorRequestHandler();
                        break;
                    case "replicatorConfiguration":
                        target = ReplicatorConfigurationRequestHandler.class.getMethod(method_to_call, Args.class);
                        requestHandler = new ReplicatorConfigurationRequestHandler();
                        break;
                    case "query":
                        target = QueryRequestHandler.class.getMethod(method_to_call, Args.class);
                        requestHandler = new QueryRequestHandler();
                        break;
                    case "expression":
                        target = ExpressionRequestHandler.class.getMethod(method_to_call, Args.class);
                        requestHandler = new ExpressionRequestHandler();
                        break;
                    case "function":
                        target = FunctionRequestHandler.class.getMethod(method_to_call, Args.class);
                        requestHandler = new FunctionRequestHandler();
                        break;
                    case "dataSource":
                        target = DataSourceRequestHandler.class.getMethod(method_to_call, Args.class);
                        requestHandler = new DataSourceRequestHandler();
                        break;
                    case "selectResult":
                        target = SelectResultRequestHandler.class.getMethod(method_to_call, Args.class);
                        requestHandler = new SelectResultRequestHandler();
                        break;
                    case "collation":
                        target = CollatorRequestHandler.class.getMethod(method_to_call, Args.class);
                        requestHandler = new CollatorRequestHandler();
                        break;
                    case "result":
                        target = ResultRequestHandler.class.getMethod(method_to_call, Args.class);
                        requestHandler = new ResultRequestHandler();
                        break;
                    case "basicAuthenticator":
                        target = BasicAuthenticatorRequestHandler.class.getMethod(method_to_call, Args.class);
                        requestHandler = new BasicAuthenticatorRequestHandler();
                        break;
                    case "sessionAuthenticator":
                        target = SessionAuthenticatorRequestHandler.class.getMethod(method_to_call, Args.class);
                        requestHandler = new SessionAuthenticatorRequestHandler();
                        break;
                    case "array":
                        target = ArrayRequestHandler.class.getMethod(method_to_call, Args.class);
                        requestHandler = new ArrayRequestHandler();
                        break;
                    case "peerToPeer":
                        target = PeerToPeerRequestHandler.class.getMethod(method_to_call, Args.class);
                        requestHandler = new PeerToPeerRequestHandler();
                        break;
                    case "predictiveQuery":
                        target = PredictiveQueriesRequestHandler.class.getMethod(method_to_call, Args.class);
                        requestHandler = new PredictiveQueriesRequestHandler();
                        break;
                    case "logging":
                        target = LoggingRequestHandler.class.getMethod(method_to_call, Args.class);
                        requestHandler = new LoggingRequestHandler();
                        break;
                    default:
                        throw new IllegalArgumentException("Handler not implemented for this call");
                }
                if (target.getReturnType().equals(Void.TYPE)) {
                    target.invoke(requestHandler, args);
                } else {
                    result = target.invoke(requestHandler, args);
                    body = ValueSerializer.serialize(result, memory);
                }
            }
            session.getHeaders();
            if (body != null) {
                IStatus status = Status.OK;
                return Response.newFixedLengthResponse(status, "text/plain", body.getBytes());
            } else {
                return Response.newFixedLengthResponse(Status.OK, "text/plain", "I-1");
            }
        } catch (Exception e) {
            // TODO: How should we handle exceptions?
            e.printStackTrace(System.out);
            StringWriter sw = new StringWriter();
            PrintWriter pw = new PrintWriter(sw);
            e.printStackTrace(pw);
            String sStackTrace = sw.toString();
            return Response.newFixedLengthResponse(Status.BAD_REQUEST, "text/plain", sStackTrace);
        }
    }
}

