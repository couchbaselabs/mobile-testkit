package com.couchbase.mobiletestkit.javalistener;

import java.io.ByteArrayOutputStream;
import java.io.ObjectOutputStream;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.lang.reflect.Method;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.List;
import java.util.Map;


import com.couchbase.mobiletestkit.javacommon.*;

import com.couchbase.mobiletestkit.javacommon.util.Log;
import com.google.gson.Gson;
import org.nanohttpd.protocols.http.IHTTPSession;
import org.nanohttpd.protocols.http.NanoHTTPD;
import org.nanohttpd.protocols.http.response.IStatus;
import org.nanohttpd.protocols.http.response.Response;
import org.nanohttpd.protocols.http.response.Status;

import com.couchbase.lite.Database;
import com.couchbase.lite.LogDomain;
import com.couchbase.lite.LogLevel;



public class Server extends NanoHTTPD {
    public static final String TAG = "SERVER";

    public String uri;

    public Method method;

    public Map<String, String> header;

    public Map<String, String> params;

    public Map<String, List<String>> parameters;

    public Map<String, String> files;

    public Map<String, List<String>> decodedParameters;

    public Map<String, List<String>> decodedParametersFromParameter;

    public String queryParameterString;

    public static final Memory memory = new Memory();

    private static Context context = null;

    public Server(Context context, int port) {
        super(port);
    }

    public static Context getContext() {
        return context;
    }

    public static void setContext(Context ctxt) {
        context = ctxt;
    }

    @Override
    public Response handle(IHTTPSession session) {
        String path = session.getUri();
        Log.i(TAG, "Request URI: " + path);

        String method = (path.startsWith("/") ? path.substring(1) : path);

        Database.log.getConsole().setLevel(LogLevel.DEBUG);
        Database.log.getConsole().setDomains(EnumSet.of(LogDomain.ALL));
        // Get args from query string.
        Map<String, String> rawArgs = new HashMap<>();

        Args args = new Args();
        try {
            session.parseBody(rawArgs);
        }
        catch (Exception e) {
            Log.e(TAG, "Failed parsing args", e);
        }
        Map<String, Object> query = new Gson().fromJson(rawArgs.get("postData"), Map.class);
        if (query != null) {
            for (String key : query.keySet()) {
                /*
                while receiving a release method in request
                no deserialization is needed,
                the original object memory address is required
                */
                if("release".equals(method)){
                    args.put(key, query.get(key));
                }
                else {
                    String value = (String) query.get(key);
                    args.put(key, ValueSerializer.deserialize(value, memory));
                }
            }
        }

        try {
            // Find and invoke the method on the RequestHandler.
            Object body = null;

            /*
            deal with request handler type and request method:
            in general, if url format is /database_create
            then DatabaseReqestHandler will be instantiated, and create() method will get invoked,
            if url format is /flushMemory
            they no Reqest Handler is involved, it deals with the Memory object or other objects.
             */
            String handlerType = "";
            String method_to_call = "";

            if(method.equalsIgnoreCase("copy_files")){
                method_to_call = method;
            }
            else {
                final String[] methodArgs = method.split("_");
                handlerType = methodArgs.length > 1 ? methodArgs[0] : "nohandler";
                method_to_call = methodArgs.length > 1 ? methodArgs[1] : methodArgs[0];
            }

            RequestHandlerDispatcher.setDispatcherProperties(context, memory);
            body = RequestHandlerDispatcher.handle(handlerType, method_to_call, args);

            session.getHeaders();
            if (body == null) {
				return Response.newFixedLengthResponse(Status.OK, "text/plain", "I-1");
			}                
            else {
				if (body instanceof String) {
                    return Response.newFixedLengthResponse(Status.OK, "text/plain", ((String) body).getBytes());
                }
				else if (body instanceof RawData) {
                    RawData dataObj = (RawData) body;
                    return Response.newFixedLengthResponse(Status.OK, dataObj.contentType, dataObj.data);
                }
				else {
                    throw new IllegalArgumentException("unrecognized body type: " + body.getClass());
                }
            }
        }
        catch (Exception e) {
            Log.w(TAG, "Request failed", e);

            StringWriter sw = new StringWriter();
            PrintWriter pw = new PrintWriter(sw);
            e.printStackTrace(pw);
            return Response.newFixedLengthResponse(Status.BAD_REQUEST, "text/plain", sw.toString());
        }
    }
}

