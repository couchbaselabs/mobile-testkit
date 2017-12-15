package com.couchbase.CouchbaseLiteServ.server.RequestHandler;


import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.Conflict;
import com.couchbase.lite.ReadOnlyDocument;

public class ConflictRequestHandler {

    public ReadOnlyDocument getBase(Args args){
        Conflict conflict = args.get("conflict");
        return conflict.getBase();
    }

    public ReadOnlyDocument getMine(Args args){
        Conflict conflict = args.get("conflict");
        return conflict.getMine();
    }

    public ReadOnlyDocument getTheirs(Args args){
        Conflict conflict = args.get("conflict");
        return conflict.getTheirs();
    }
}
