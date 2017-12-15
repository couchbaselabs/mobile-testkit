package com.couchbase.CouchbaseLiteServ.server.RequestHandler;


import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.SessionAuthenticator;

import java.util.Date;

public class SessionAuthenticatorRequestHandler {
    /* ------------------------ */
    /* - SessionAuthenticator - */
    /* ------------------------ */

    public SessionAuthenticator create(Args args){
        String sessionId = args.get("sessionId");
        String cookieName = args.get("cookieName");
        Object expires  = args.get("expires");
        return new SessionAuthenticator(sessionId, expires, cookieName);
    }

    public String getSessionId(Args args){
        SessionAuthenticator session = args.get("session");
        return session.getSessionID();
    }

    public String getCookieName(Args args){
        SessionAuthenticator session = args.get("session");
        return session.getCookieName();
    }

    public Date getExpires(Args args){
        SessionAuthenticator session = args.get("session");
        return session.getExpires();
    }
}
