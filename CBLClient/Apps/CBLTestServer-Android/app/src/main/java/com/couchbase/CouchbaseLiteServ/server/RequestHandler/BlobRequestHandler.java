package com.couchbase.CouchbaseLiteServ.server.RequestHandler;


import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.Blob;
import com.couchbase.lite.Database;
import com.couchbase.litecore.fleece.FLEncoder;

import java.io.IOException;
import java.io.InputStream;
import java.net.URL;
import java.util.Base64;
import java.util.Map;

public class BlobRequestHandler {

    public Blob create(Args args) throws IOException {
        String contentType = args.get("contentType");
        byte[] content = args.get("content");
        InputStream stream = args.get("stream");
        URL fileURL = args.get("fileURL");
        if (!contentType.isEmpty()){
            return new Blob(contentType, content);
        } else if (stream != null){
            return new Blob(contentType, stream);
        } else if (fileURL != null){
            return new Blob(contentType, fileURL);
        }else {
            throw new IOException("Incorrect parameters provided");
        }
    }

    public String digest(Args args){
        Blob obj = args.get("obj");
        return obj.digest();
    }

    public void fleeceEncode(Args args){
        Blob obj = args.get("obj");
        FLEncoder encoder = args.get("encoder");
        Database database = args.get("database");
        obj.fleeceEncode(encoder, database);
    }

    public byte[] getContent(Args args){
        Blob obj = args.get("obj");
        return obj.getContent();
    }

    public Map<String, Object> getProperties(Args args){
        Blob obj = args.get("obj");
        return obj.getProperties();
    }

    public InputStream getContentStream(Args args){
        Blob obj = args.get("obj");
        return obj.getContentStream();
    }

    public String getContentType(Args args){
        Blob obj = args.get("obj");
        return obj.getContentType();
    }

    public long length(Args args){
        Blob obj = args.get("obj");
        return obj.length();
    }

    public String toString(Args args){
        Blob obj = args.get("obj");
        return obj.toString();
    }
}
