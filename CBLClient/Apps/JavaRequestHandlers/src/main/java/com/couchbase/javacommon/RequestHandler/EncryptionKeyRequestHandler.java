package com.couchbase.javacommon.RequestHandler;


import com.couchbase.javacommon.Args;
import com.couchbase.lite.EncryptionKey;


public class EncryptionKeyRequestHandler {

    public EncryptionKey create(Args args) {
        byte[] key = args.get("key");
        String password = args.get("password");

        if (password != null) {
            return new EncryptionKey(password);
        }
        else if (key != null) {
            return new EncryptionKey(key);
        }
        else {
            throw new IllegalArgumentException("an Encryption parameter is null");
        }
    }
}
