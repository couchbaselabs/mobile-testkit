package com.couchbase.javacommon;

import com.couchbase.javacommon.RequestHandler.*;
import com.couchbase.javacommon.log.Log;

import java.lang.reflect.Method;


public class RequestHandlerDispatcher {
    public static final String TAG = "REQUEST-DISPATCHER";
    public static Context context = null;
    public static Memory memory = null;

    public static void setDispatcherProperties(Context requestContext, Memory memoryObject){
        context = requestContext;
        memory = memoryObject;
    }

    public static String handle(String handlerType, String method, Args args) throws Exception {
        String body = null;

        try{
            Object result;
            if ("release".equals(method)) {
                memory.remove(args.get("releaseObject"));
            }
            else if ("flushMemory".equals(method)) {
                memory.flushMemory();
            } else if ("copy_files".equals(method)){
                result = memory.copyFiles(args);
                body = ValueSerializer.serialize(result, memory);
            } else {
                Method target;
                Object requestHandler;
                switch (handlerType) {
                    case "databaseConfiguration":
                        target = DatabaseConfigurationRequestHandler.class.getMethod(method, Args.class);
                        requestHandler = new DatabaseConfigurationRequestHandler();
                        break;
                    case "database":
                        target = DatabaseRequestHandler.class.getMethod(method, Args.class);
                        requestHandler = new DatabaseRequestHandler();
                        break;
                    case "document":
                        target = DocumentRequestHandler.class.getMethod(method, Args.class);
                        requestHandler = new DocumentRequestHandler();
                        break;
                    case "dictionary":
                        target = DictionaryRequestHandler.class.getMethod(method, Args.class);
                        requestHandler = new DictionaryRequestHandler();
                        break;
                    case "datatype":
                        target = DataTypesInitiatorHandler.class.getMethod(method, Args.class);
                        requestHandler = new DataTypesInitiatorHandler();
                        break;
                    case "replicator":
                        target = ReplicatorRequestHandler.class.getMethod(method, Args.class);
                        requestHandler = new ReplicatorRequestHandler();
                        break;
                    case "replicatorConfiguration":
                        target = ReplicatorConfigurationRequestHandler.class.getMethod(method, Args.class);
                        requestHandler = new ReplicatorConfigurationRequestHandler();
                        break;
                    case "query":
                        target = QueryRequestHandler.class.getMethod(method, Args.class);
                        requestHandler = new QueryRequestHandler();
                        break;
                    case "expression":
                        target = ExpressionRequestHandler.class.getMethod(method, Args.class);
                        requestHandler = new ExpressionRequestHandler();
                        break;
                    case "function":
                        target = FunctionRequestHandler.class.getMethod(method, Args.class);
                        requestHandler = new FunctionRequestHandler();
                        break;
                    case "dataSource":
                        target = DataSourceRequestHandler.class.getMethod(method, Args.class);
                        requestHandler = new DataSourceRequestHandler();
                        break;
                    case "selectResult":
                        target = SelectResultRequestHandler.class.getMethod(method, Args.class);
                        requestHandler = new SelectResultRequestHandler();
                        break;
                    case "collation":
                        target = CollatorRequestHandler.class.getMethod(method, Args.class);
                        requestHandler = new CollatorRequestHandler();
                        break;
                    case "result":
                        target = ResultRequestHandler.class.getMethod(method, Args.class);
                        requestHandler = new ResultRequestHandler();
                        break;
                    case "basicAuthenticator":
                        target = BasicAuthenticatorRequestHandler.class.getMethod(method, Args.class);
                        requestHandler = new BasicAuthenticatorRequestHandler();
                        break;
                    case "sessionAuthenticator":
                        target = SessionAuthenticatorRequestHandler.class.getMethod(method, Args.class);
                        requestHandler = new SessionAuthenticatorRequestHandler();
                        break;
                    case "array":
                        target = ArrayRequestHandler.class.getMethod(method, Args.class);
                        requestHandler = new ArrayRequestHandler();
                        break;
                    case "peerToPeer":
                        target = PeerToPeerRequestHandler.class.getMethod(method, Args.class);
                        requestHandler = new PeerToPeerRequestHandler();
                        break;
                    case "predictiveQuery":
                        target = PredictiveQueriesRequestHandler.class.getMethod(method, Args.class);
                        requestHandler = new PredictiveQueriesRequestHandler();
                        break;
                    case "logging":
                        target = LoggingRequestHandler.class.getMethod(method, Args.class);
                        requestHandler = new LoggingRequestHandler();
                        break;
                    case "blob":
                        target = BlobRequestHandler.class.getMethod(method, Args.class);
                        requestHandler = new BlobRequestHandler();
                        break;
                    default:
                        throw new IllegalArgumentException("Handler not implemented for this call");
                }
                if (target.getReturnType().equals(Void.TYPE)) {
                    target.invoke(requestHandler, args);
                }
                else {
                    result = target.invoke(requestHandler, args);
                    body = ValueSerializer.serialize(result, memory);
                }
            }


        } catch (Exception e){
            Log.e(TAG, e.getMessage());
            throw e;
        }

        return body;
    }
   
}