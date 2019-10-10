package com.couchbase.javacommon.RequestHandler;

import com.couchbase.javacommon.Args;
import com.couchbase.lite.Collation;


public class CollatorRequestHandler {

    public Collation.ASCII ascii(Args args) {
        Boolean ignoreCase = args.get("ignoreCase");
        return Collation.ascii().ignoreCase(ignoreCase);
    }

    public Collation.Unicode unicode(Args args) {
        Boolean ignoreCase = args.get("ignoreCase");
        Boolean ignoreAccents = args.get("ignoreAccents");
        return Collation.unicode().ignoreCase(ignoreCase).ignoreAccents(ignoreAccents);
    }

}
