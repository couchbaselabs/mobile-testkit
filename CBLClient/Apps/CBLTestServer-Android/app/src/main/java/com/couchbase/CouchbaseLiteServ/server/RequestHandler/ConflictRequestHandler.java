package com.couchbase.CouchbaseLiteServ.server.RequestHandler;


import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.Conflict;
import com.couchbase.lite.Document;

public class ConflictRequestHandler {

    public Document getBase(Args args){
        Conflict conflict = args.get("conflict");
        return conflict.getBase();
    }

    public Document getMine(Args args){
        Conflict conflict = args.get("conflict");
        return conflict.getMine();
    }

    public Document getTheirs(Args args){
        Conflict conflict = args.get("conflict");
        return conflict.getTheirs();
    }
}
