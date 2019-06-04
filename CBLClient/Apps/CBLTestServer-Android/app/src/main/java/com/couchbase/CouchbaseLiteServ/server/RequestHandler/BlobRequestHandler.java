package com.couchbase.CouchbaseLiteServ.server.RequestHandler;

import android.content.Context;

import com.couchbase.CouchbaseLiteServ.server.Args;
import com.couchbase.lite.Blob;
import com.couchbase.litecore.fleece.FLEncoder;

import java.io.IOException;
import java.io.InputStream;
import java.net.URL;
import java.util.Map;

public class BlobRequestHandler {

    public Blob create(Args args) throws IOException {
        String contentType = args.get("contentType");
        byte[] content = args.get("content");
        InputStream stream = args.get("stream");
        URL fileURL = args.get("fileURL");
        if (content != null){
            return new Blob(contentType, content);
        } else if (stream != null){
            return new Blob(contentType, stream);
        } else if (fileURL != null){
            return new Blob(contentType, fileURL);
        }else {
            throw new IOException("Incorrect parameters provided");
        }
    }

    public InputStream createImageContent(Args args) throws IOException {
        String image = args.get("image");
        InputStream is = getAsset(image);
        return is;
    }

    private InputStream getAsset(String name) {
        return this.getClass().getResourceAsStream(name);
    }

    public String digest(Args args){
        Blob blob = args.get("blob");
        return blob.digest();
    }

    public void encodeTo(Args args){
        Blob blob = args.get("blob");
        FLEncoder encoder = args.get("encoder");
        blob.encodeTo(encoder);
    }

    public Boolean equals(Args args){
        Blob blob = args.get("blob");
        Object obj = args.get("obj");
        return blob.equals(obj);
    }

    public int hashCode(Args args){
        Blob blob = args.get("blob");
        return blob.hashCode();
    }

    public byte[] getContent(Args args){
        Blob blob = args.get("blob");
        return blob.getContent();
    }

    public Map<String, Object> getProperties(Args args){
        Blob blob = args.get("blob");
        return blob.getProperties();
    }

    public InputStream getContentStream(Args args){
        Blob blob = args.get("blob");
        return blob.getContentStream();
    }

    public String getContentType(Args args){
        Blob blob = args.get("blob");
        return blob.getContentType();
    }

    public long length(Args args){
        Blob blob = args.get("blob");
        return blob.length();
    }

    public String toString(Args args){
        Blob blob = args.get("blob");
        return blob.toString();
    }
}
