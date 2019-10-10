package com.couchbase.javacommon.RequestHandler;


import com.couchbase.javacommon.Args;
import com.couchbase.lite.SessionAuthenticator;


public class SessionAuthenticatorRequestHandler {
    /* ------------------------ */
    /* - SessionAuthenticator - */
    /* ------------------------ */

    public SessionAuthenticator create(Args args) {
        String sessionId = args.get("sessionId");
        String cookieName = args.get("cookieName");
        if (cookieName == null) {
            return new SessionAuthenticator(sessionId);
        }
        return new SessionAuthenticator(sessionId, cookieName);
    }

    public String getSessionId(Args args) {
        SessionAuthenticator session = args.get("session");
        return session.getSessionID();
    }

    public String getCookieName(Args args) {
        SessionAuthenticator session = args.get("session");
        return session.getCookieName();
    }
}
