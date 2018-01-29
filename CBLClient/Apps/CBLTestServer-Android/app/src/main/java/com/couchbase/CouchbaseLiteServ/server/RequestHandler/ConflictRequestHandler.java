package com.couchbase.CouchbaseLiteServ.server.RequestHandler;


import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.Conflict;
import com.couchbase.lite.ConflictResolver;
import com.couchbase.lite.Document;

public class ConflictRequestHandler {

    public ConflictResolver resolver(Args args) {
        String conflictType = args.get("conflict_type");
        if (conflictType.equals("mine")) {
            return new ReplicationMine();
        } else if (conflictType.equals("theirs")) {
            return new ReplicationTheirs();
        } else if (conflictType.equals("base")) {
            return new ReplicationBase();
        } else {
            return null;
        }
    }

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

class ReplicationMine implements ConflictResolver {
    @Override
    public Document resolve(Conflict conflict) {
        return conflict.getMine();
    }
}

class ReplicationTheirs implements ConflictResolver {
    @Override
    public Document resolve(Conflict conflict) {
        return conflict.getTheirs();
    }
}

class ReplicationBase implements ConflictResolver {
    @Override
    public Document resolve(Conflict conflict) {
        return conflict.getBase();
    }
}

class GiveUp implements ConflictResolver {
    @Override
    public Document resolve(Conflict conflict) {
        return null;
    }
}