package com.couchbase.mobiletestkit.javacommon.RequestHandler;

import java.io.IOException;
import java.io.InputStream;
import java.net.URL;
import java.util.Map;

import com.couchbase.mobiletestkit.javacommon.Args;
import com.couchbase.mobiletestkit.javacommon.RequestHandlerDispatcher;
import com.couchbase.lite.Blob;


public class BlobRequestHandler {

    public Blob create(Args args) throws IOException {
        String contentType = args.get("contentType");

        byte[] content = args.get("content");
        if (content != null) { return new Blob(contentType, content); }

        InputStream stream = args.get("stream");
        if (stream != null) { return new Blob(contentType, stream); }

        URL fileURL = args.get("fileURL");
        if (fileURL != null) { return new Blob(contentType, fileURL); }

        throw new IOException("Incorrect parameters provided");
    }

    public InputStream createImageContent(Args args) throws IOException {
        String filePath = args.get("image");
        if (filePath == null || filePath.isEmpty()) {
            throw new IOException("Image content file path cannot be null");
        }

        String[] imgFilePath = filePath.split("/");
        return RequestHandlerDispatcher.context.getAsset(imgFilePath[imgFilePath.length - 1]);
    }

    public String digest(Args args) {
        return ((Blob) args.get("blob")).digest();
    }

    public void encodeTo(Args args) {
        ((Blob) args.get("blob")).encodeTo(args.get("encoder"));
    }

    public Boolean equals(Args args) {
        return args.get("blob").equals(args.get("obj"));
    }

    public int hashCode(Args args) {
        return ((Blob) args.get("blob")).hashCode();
    }

    public byte[] getContent(Args args) {
        return ((Blob) args.get("blob")).getContent();
    }

    public Map<String, Object> getProperties(Args args) {
        return ((Blob) args.get("blob")).getProperties();
    }

    public InputStream getContentStream(Args args) {
        return ((Blob) args.get("blob")).getContentStream();
    }

    public String getContentType(Args args) {
        return ((Blob) args.get("blob")).getContentType();
    }

    public long length(Args args) {
        return ((Blob) args.get("blob")).length();
    }

    public String toString(Args args) {
        return args.get("blob").toString();
    }
}
